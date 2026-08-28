from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from uuid import uuid4

from fastapi import Request
from sqlalchemy import insert, select

from .canonical_schema import audit_events
from .executive_store import employees


READ_ROLES = frozenset({"Reader", "Editor", "Account Manager", "Account Admin"})
WRITE_ROLES = frozenset({"Editor", "Account Manager", "Account Admin"})
ADMIN_ROLES = frozenset({"Account Admin"})


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    employee_id: str | None = None

    @property
    def can_write(self) -> bool:
        return bool(self.roles & WRITE_ROLES)

    @property
    def is_admin(self) -> bool:
        return bool(self.roles & ADMIN_ROLES)

    def as_dict(self) -> dict:
        return {
            "subject": self.subject,
            "roles": sorted(self.roles),
            "employee_id": self.employee_id,
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
        roles = frozenset(value.strip() for value in request.headers.get("x-user-roles", "Reader").split(",") if value.strip())
        employee_id = request.headers.get("x-user-employee-id") or None
        return Principal(subject, roles, employee_id)
    roles_header = request.headers.get("x-development-roles")
    # Development overrides are intentionally unavailable in production and
    # make permission behavior testable without a corporate identity provider.
    roles = frozenset(value.strip() for value in (roles_header or ",".join(settings.development_roles)).split(",") if value.strip())
    return Principal(
        request.headers.get("x-development-subject", settings.development_actor).strip(),
        roles,
        request.headers.get("x-development-employee-id") or None,
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
