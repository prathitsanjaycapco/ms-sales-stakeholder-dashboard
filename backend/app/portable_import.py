from __future__ import annotations

import json
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import create_engine, event, insert, select, update

from .canonical_schema import (
    accounts, business_units, divisions, pods, stakeholder_assignments,
    stakeholder_employee_relationships, stakeholders,
)
from .executive_store import employee_skills, employees


class ImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountImport(ImportRow):
    name: str = Field(min_length=2, max_length=200)


class PodImport(ImportRow):
    name: str = Field(min_length=1, max_length=80)
    head_stakeholder_id: str


class DivisionImport(ImportRow):
    id: str = Field(min_length=1, max_length=160)
    pod: str
    name: str = Field(min_length=1, max_length=120)
    color: str = Field(default="#1675d1", pattern=r"^#[0-9A-Fa-f]{6}$")
    head_stakeholder_id: str | None = None


class BusinessUnitImport(ImportRow):
    id: str = Field(min_length=1, max_length=220)
    division_id: str
    name: str = Field(min_length=1, max_length=160)
    sort_order: int = Field(default=0, ge=0)


class EmployeeImport(ImportRow):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=2, max_length=180)
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    level: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=120)
    capability: str | None = None
    location: str = Field(min_length=1, max_length=120)
    active: bool = True
    manager_employee_id: str | None = None
    skills: list[str] = Field(default_factory=list)
    source_record_id: str | None = None


class StakeholderImport(ImportRow):
    id: str = Field(min_length=1, max_length=180)
    name: str = Field(min_length=2, max_length=160)
    title: str = Field(min_length=2, max_length=160)
    pod: str
    division_id: str | None = None
    business_unit_id: str | None = None
    team_type: str = Field(pattern="^(Business|Technology)$")
    organizational_role: str = Field(min_length=1, max_length=160)
    level: str = Field(default="Vice President", min_length=1, max_length=80)
    location: str = Field(default="Not recorded", min_length=1, max_length=160)
    country_code: str = Field(default="US", min_length=2, max_length=2)
    manager_stakeholder_id: str | None = None
    is_primary_technology: bool = False
    is_buyer: bool = False
    is_influencer: bool = True
    is_budget_holder: bool = False
    relationship_strength: str = Field(default="Developing", pattern="^(Strong|Medium|Developing|Unknown)$")
    capco_contingents: int = Field(default=0, ge=0)
    budget_amount: float | None = Field(default=None, ge=0)
    biography: str = ""
    tags: list[str] = Field(default_factory=list)
    source_record_id: str | None = None


class RelationshipImport(ImportRow):
    id: str = Field(min_length=1, max_length=180)
    stakeholder_id: str
    employee_id: str
    relationship_role: str = Field(default="Relationship owner", min_length=1, max_length=80)
    is_primary: bool = False
    effective_from: date
    effective_to: date | None = None
    is_current: bool = True

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return sorted({value for value in values if value in seen or seen.add(value)})


def _cycles(parent_by_id: dict[str, str | None]) -> list[str]:
    cyclic: set[str] = set()
    for record_id in parent_by_id:
        path: set[str] = set()
        cursor: str | None = record_id
        while cursor:
            if cursor in path:
                cyclic.add(record_id)
                break
            path.add(cursor)
            cursor = parent_by_id.get(cursor)
    return sorted(cyclic)


class PortableImportBatch(ImportRow):
    schema_version: int = Field(default=1, ge=1, le=1)
    account: AccountImport
    pods: list[PodImport] = Field(min_length=1)
    divisions: list[DivisionImport] = Field(min_length=1)
    business_units: list[BusinessUnitImport] = Field(default_factory=list)
    employees: list[EmployeeImport] = Field(default_factory=list)
    stakeholders: list[StakeholderImport] = Field(min_length=1)
    relationships: list[RelationshipImport] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_are_valid(self):
        errors: list[str] = []
        for label, values in (
            ("pods", [item.name for item in self.pods]),
            ("divisions", [item.id for item in self.divisions]),
            ("business_units", [item.id for item in self.business_units]),
            ("employees", [item.id for item in self.employees]),
            ("stakeholders", [item.id for item in self.stakeholders]),
            ("relationships", [item.id for item in self.relationships]),
        ):
            duplicates = _duplicates(values)
            if duplicates:
                errors.append(f"duplicate {label} IDs/names: {', '.join(duplicates)}")

        pod_names = {item.name for item in self.pods}
        divisions_by_id = {item.id: item for item in self.divisions}
        units_by_id = {item.id: item for item in self.business_units}
        employees_by_id = {item.id: item for item in self.employees}
        stakeholders_by_id = {item.id: item for item in self.stakeholders}

        for item in self.divisions:
            if item.pod not in pod_names:
                errors.append(f"division {item.id} references unknown pod {item.pod}")
        for item in self.business_units:
            if item.division_id not in divisions_by_id:
                errors.append(f"business unit {item.id} references unknown division {item.division_id}")
        for item in self.pods:
            head = stakeholders_by_id.get(item.head_stakeholder_id)
            if not head or head.pod != item.name or head.organizational_role != "Pod Head":
                errors.append(f"pod {item.name} requires a Pod Head stakeholder in the same pod")
        for item in self.stakeholders:
            if item.pod not in pod_names:
                errors.append(f"stakeholder {item.id} references unknown pod {item.pod}")
                continue
            if item.organizational_role == "Pod Head":
                if item.division_id or item.business_unit_id or item.manager_stakeholder_id:
                    errors.append(f"pod head {item.id} cannot have division, business unit, or manager")
            else:
                division = divisions_by_id.get(item.division_id or "")
                if not division or division.pod != item.pod:
                    errors.append(f"stakeholder {item.id} requires a division in pod {item.pod}")
                if not item.manager_stakeholder_id:
                    errors.append(f"stakeholder {item.id} requires manager_stakeholder_id")
            if item.business_unit_id:
                unit = units_by_id.get(item.business_unit_id)
                if not unit or unit.division_id != item.division_id:
                    errors.append(f"stakeholder {item.id} references a business unit outside its division")
            manager = stakeholders_by_id.get(item.manager_stakeholder_id or "")
            if item.manager_stakeholder_id and (not manager or manager.pod != item.pod):
                errors.append(f"stakeholder {item.id} references an unknown or cross-pod manager")
            if item.is_primary_technology and (item.team_type != "Technology" or not item.business_unit_id):
                errors.append(f"primary technology stakeholder {item.id} must be Technology and have a business unit")
        for item in self.divisions:
            if item.head_stakeholder_id:
                head = stakeholders_by_id.get(item.head_stakeholder_id)
                if not head or head.division_id != item.id:
                    errors.append(f"division {item.id} head must be assigned to that division")
        for item in self.employees:
            if item.manager_employee_id and item.manager_employee_id not in employees_by_id:
                errors.append(f"employee {item.id} references unknown manager {item.manager_employee_id}")
        for item in self.relationships:
            if item.stakeholder_id not in stakeholders_by_id:
                errors.append(f"relationship {item.id} references unknown stakeholder {item.stakeholder_id}")
            if item.employee_id not in employees_by_id:
                errors.append(f"relationship {item.id} references unknown employee {item.employee_id}")

        stakeholder_cycles = _cycles({item.id: item.manager_stakeholder_id for item in self.stakeholders})
        employee_cycles = _cycles({item.id: item.manager_employee_id for item in self.employees})
        if stakeholder_cycles:
            errors.append(f"stakeholder reporting cycles: {', '.join(stakeholder_cycles)}")
        if employee_cycles:
            errors.append(f"employee reporting cycles: {', '.join(employee_cycles)}")

        primary_units = [item.business_unit_id for item in self.stakeholders if item.is_primary_technology]
        duplicate_primary_units = _duplicates([value for value in primary_units if value])
        if duplicate_primary_units:
            errors.append(f"multiple primary technology stakeholders for: {', '.join(duplicate_primary_units)}")
        primary_relationships = [item.stakeholder_id for item in self.relationships if item.is_current and item.is_primary]
        duplicate_primary_relationships = _duplicates(primary_relationships)
        if duplicate_primary_relationships:
            errors.append(f"multiple current primary relationship owners for: {', '.join(duplicate_primary_relationships)}")
        if errors:
            raise ValueError("; ".join(errors))
        return self


def load_portable_import(source: Path) -> PortableImportBatch:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}") from error
    return PortableImportBatch.model_validate(payload)


def _migrate(database_path: Path, resource_root: Path) -> None:
    config = Config(str(resource_root / "alembic.ini"))
    config.set_main_option("script_location", str(resource_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")


def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def build_portable_database(batch: PortableImportBatch, database_path: Path, resource_root: Path) -> dict[str, int]:
    _migrate(database_path, resource_root)
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    event.listen(engine, "connect", _enable_foreign_keys)
    now = datetime.now(timezone.utc)
    try:
        with engine.begin() as connection:
            connection.execute(insert(accounts).values(id="morgan-stanley", name=batch.account.name))
            connection.execute(insert(pods), [
                {"id": item.name, "account_id": "morgan-stanley", "name": item.name, "head_stakeholder_id": None}
                for item in batch.pods
            ])
            connection.execute(insert(divisions), [
                {"id": item.id, "pod_id": item.pod, "name": item.name, "color": item.color, "head_stakeholder_id": None}
                for item in batch.divisions
            ])
            if batch.business_units:
                connection.execute(insert(business_units), [item.model_dump() for item in batch.business_units])
            if batch.employees:
                connection.execute(insert(employees), [{
                    **item.model_dump(exclude={"skills", "manager_employee_id"}),
                    "manager_employee_id": None,
                    "source_system": "portable_import",
                    "created_at": now,
                    "updated_at": now,
                    "last_synced_at": now,
                } for item in batch.employees])
            connection.execute(insert(stakeholders), [{
                "id": item.id,
                "name": item.name,
                "title": item.title,
                "level": item.level,
                "location": item.location,
                "country_code": item.country_code.upper(),
                "biography": item.biography,
                "created_at": now,
                "updated_at": now,
                "source_system": "portable_import",
                "source_record_id": item.source_record_id,
                "last_synced_at": now,
            } for item in batch.stakeholders])
            connection.execute(insert(stakeholder_assignments), [{
                "id": f"assignment-{item.id}",
                "stakeholder_id": item.id,
                "pod_id": item.pod,
                "division_id": item.division_id,
                "business_unit_id": item.business_unit_id,
                "team_type": item.team_type,
                "organizational_role": item.organizational_role,
                "manager_stakeholder_id": item.manager_stakeholder_id,
                "is_primary_technology": item.is_primary_technology,
                "is_buyer": item.is_buyer,
                "is_influencer": item.is_influencer,
                "is_budget_holder": item.is_budget_holder,
                "relationship_strength": item.relationship_strength,
                "capco_contingents": item.capco_contingents,
                "capco_owner": next((employee.name for employee in batch.employees if employee.id == next((relationship.employee_id for relationship in batch.relationships if relationship.stakeholder_id == item.id and relationship.is_primary and relationship.is_current), None)), None),
                "budget_amount": item.budget_amount,
                "tags": item.tags,
                "effective_from": date.today(),
                "effective_to": None,
                "is_current": True,
            } for item in batch.stakeholders])
            if batch.relationships:
                connection.execute(insert(stakeholder_employee_relationships), [{
                    **item.model_dump(), "created_at": now,
                } for item in batch.relationships])
            skill_rows = [
                {"id": f"skill-{uuid4().hex}", "employee_id": item.id, "capability": skill}
                for item in batch.employees for skill in dict.fromkeys(item.skills) if skill.strip()
            ]
            if skill_rows:
                connection.execute(insert(employee_skills), skill_rows)
            for item in batch.employees:
                if item.manager_employee_id:
                    connection.execute(update(employees).where(employees.c.id == item.id).values(manager_employee_id=item.manager_employee_id))
            for item in batch.divisions:
                if item.head_stakeholder_id:
                    connection.execute(update(divisions).where(divisions.c.id == item.id).values(head_stakeholder_id=item.head_stakeholder_id))
            for item in batch.pods:
                connection.execute(update(pods).where(pods.c.id == item.name).values(head_stakeholder_id=item.head_stakeholder_id))
        with engine.connect() as connection:
            foreign_key_errors = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            if foreign_key_errors:
                raise ValueError(f"Imported database failed foreign-key validation: {foreign_key_errors[:10]}")
    finally:
        engine.dispose()
    return {
        "pods": len(batch.pods),
        "divisions": len(batch.divisions),
        "business_units": len(batch.business_units),
        "employees": len(batch.employees),
        "stakeholders": len(batch.stakeholders),
        "relationships": len(batch.relationships),
    }


def replace_portable_database(source: Path, database_path: Path, resource_root: Path, *, validate_only: bool = False) -> dict[str, int]:
    batch = load_portable_import(source)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = database_path.with_name(f".{database_path.stem}-importing-{uuid4().hex}.db")
    try:
        counts = build_portable_database(batch, temporary, resource_root)
        if validate_only:
            return counts
        if database_path.exists():
            backups = database_path.parent / "backups"
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(database_path, backups / f"dashboard-{stamp}.db")
        os.replace(temporary, database_path)
        return counts
    finally:
        temporary.unlink(missing_ok=True)
