from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
import json
from threading import RLock
from uuid import uuid4

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, insert, select, text

from .canonical_schema import audit_events, idempotency_records
from .executive_store import employees


ROLE_ALIASES = {"Reader": "Viewer"}
READ_ROLES = frozenset({"Viewer", "Editor", "Account Manager", "Partner", "Account Admin"})
WRITE_ROLES = frozenset({"Editor", "Account Manager", "Partner", "Account Admin"})
ADMIN_ROLES = frozenset({"Account Admin"})
KNOWN_ROLES = READ_ROLES
DEFAULT_ACCOUNT_ID = "morgan-stanley"
_IDEMPOTENCY_LOCK = RLock()


def _parse_roles(value: str) -> tuple[frozenset[str], frozenset[str]]:
    supplied = {item.strip() for item in value.split(",") if item.strip()}
    normalized = {ROLE_ALIASES.get(item, item) for item in supplied}
    return frozenset(normalized & KNOWN_ROLES), frozenset(normalized - KNOWN_ROLES)


def _parse_scope(value: str | None) -> frozenset[str]:
    return frozenset(item.strip() for item in (value or "").split(",") if item.strip())


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    employee_id: str | None = None
    account_ids: frozenset[str] = field(default_factory=lambda: frozenset({DEFAULT_ACCOUNT_ID}))
    pod_ids: frozenset[str] = field(default_factory=frozenset)
    invalid_roles: frozenset[str] = field(default_factory=frozenset)

    @property
    def can_write(self) -> bool:
        return bool(self.roles & WRITE_ROLES)

    @property
    def is_admin(self) -> bool:
        return bool(self.roles & ADMIN_ROLES)

    def can_access_pod(self, pod_id: str | None) -> bool:
        return not pod_id or pod_id == "All" or not self.pod_ids or pod_id in self.pod_ids

    def as_dict(self) -> dict:
        return {
            "subject": self.subject,
            "roles": sorted(self.roles),
            "employee_id": self.employee_id,
            "account_ids": sorted(self.account_ids),
            "pod_ids": sorted(self.pod_ids),
            "permissions": {"read": bool(self.roles & READ_ROLES), "write": self.can_write, "admin": self.is_admin},
        }


def principal_from_request(request: Request, settings) -> Principal | None:
    if settings.auth_mode == "trusted_proxy":
        supplied_secret = request.headers.get("x-auth-proxy-secret", "")
        if not settings.trusted_proxy_secret or not compare_digest(supplied_secret, settings.trusted_proxy_secret):
            return None
        subject = request.headers.get("x-user-subject", "").strip()
        if not subject:
            return None
        roles, invalid_roles = _parse_roles(request.headers.get("x-user-roles", ""))
        account_ids = _parse_scope(request.headers.get("x-user-accounts"))
        if not account_ids:
            return None
        employee_id = request.headers.get("x-user-employee-id") or None
        return Principal(
            subject, roles, employee_id, account_ids,
            _parse_scope(request.headers.get("x-user-pods")), invalid_roles,
        )
    roles_header = request.headers.get("x-development-roles")
    # Development overrides are intentionally unavailable in production and
    # make permission behavior testable without a corporate identity provider.
    roles, invalid_roles = _parse_roles(roles_header or ",".join(settings.development_roles))
    return Principal(
        request.headers.get("x-development-subject", settings.development_actor).strip(),
        roles,
        request.headers.get("x-development-employee-id") or None,
        _parse_scope(request.headers.get("x-development-accounts")) or frozenset({DEFAULT_ACCOUNT_ID}),
        _parse_scope(request.headers.get("x-development-pods")),
        invalid_roles,
    )


def record_audit_event(engine, principal: Principal, request: Request, response_status: int) -> str:
    event_id = f"audit-{uuid4().hex}"
    employee_id = principal.employee_id
    with engine.begin() as connection:
        if employee_id and connection.execute(select(employees.c.id).where(employees.c.id == employee_id)).scalar_one_or_none() is None:
            employee_id = None
        path_parts = [value for value in request.url.path.split("/") if value and value != "api"]
        resource_names = {
            "stakeholders", "meetings", "notes", "documents", "opportunities", "pods", "tasks",
            "critical-items", "focus", "reporting-line", "business-units", "primary-tech-stakeholder",
            "resource-requirements", "candidates", "interviews", "offers", "offer", "onboarding", "steps",
        }
        resource_index = next(
            (index for index in range(len(path_parts) - 1, -1, -1) if path_parts[index] in resource_names),
            None,
        )
        resource = path_parts[resource_index] if resource_index is not None else (path_parts[0] if path_parts else "application")
        entity_type = resource[:-1] if resource.endswith("s") and resource not in {"business-units"} else resource
        entity_id = (
            path_parts[resource_index + 1]
            if resource_index is not None and resource_index + 1 < len(path_parts)
            else request.url.path
        )
        connection.execute(insert(audit_events).values(
            id=event_id,
            actor_subject=principal.subject,
            actor_employee_id=employee_id,
            action=request.method,
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"path": request.url.path, "status": response_status},
            request_id=getattr(request.state, "request_id", None),
        ))
    return event_id


def execute_idempotent(engine, principal: Principal, request: Request, payload, operation):
    """Execute a lifecycle command once for an actor-supplied idempotency key."""
    idempotency_key = request.headers.get("idempotency-key", "").strip()
    if not idempotency_key:
        return operation(), False
    if len(idempotency_key) > 180:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key is too long")

    encoded_payload = jsonable_encoder(payload)
    request_hash = sha256(json.dumps({
        "method": request.method, "path": request.url.path, "payload": encoded_payload,
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    lock_name = f"{principal.subject}:{idempotency_key}"

    def run_locked():
        with engine.connect() as lock_connection:
            postgres = lock_connection.dialect.name == "postgresql"
            if postgres:
                lock_connection.execute(text("SELECT pg_advisory_lock(hashtext(:key))"), {"key": lock_name})
            try:
                now = datetime.now(timezone.utc)
                existing = lock_connection.execute(select(idempotency_records).where(
                    idempotency_records.c.actor_subject == principal.subject,
                    idempotency_records.c.idempotency_key == idempotency_key,
                    idempotency_records.c.expires_at > now,
                )).mappings().one_or_none()
                if existing:
                    if existing["request_hash"] != request_hash or existing["path"] != request.url.path or existing["method"] != request.method:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency-Key was already used for a different request",
                        )
                    return existing["response_body"], True

                result = operation()
                body = jsonable_encoder(result)
                with engine.begin() as write_connection:
                    write_connection.execute(delete(idempotency_records).where(idempotency_records.c.expires_at <= now))
                    write_connection.execute(insert(idempotency_records).values(
                        id=f"idempotency-{uuid4().hex}", actor_subject=principal.subject,
                        idempotency_key=idempotency_key, method=request.method, path=request.url.path,
                        request_hash=request_hash, response_status=200, response_body=body,
                        expires_at=now + timedelta(hours=24),
                    ))
                return result, False
            finally:
                if postgres:
                    lock_connection.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": lock_name})

    if engine.dialect.name == "postgresql":
        return run_locked()
    with _IDEMPOTENCY_LOCK:
        return run_locked()
