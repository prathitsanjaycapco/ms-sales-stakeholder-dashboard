from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import insert, select, update

from .canonical_schema import business_units, divisions, opportunities, stakeholders
from .executive_store import (
    employee_capacity, employees, engagement_assignments, engagement_milestones,
    engagements, revenue_records,
)
from .repository import POD_STRUCTURE


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EngagementRow(ImportModel):
    id: str = Field(min_length=1, max_length=120)
    pod_id: str
    division_id: str
    business_unit_id: str
    division: str
    business_unit: str
    name: str
    health: str = Field(pattern="^(GREEN|AMBER|RED)$")
    status: str = Field(pattern="^(Active|Planned|Completed|Cancelled)$")
    commercial_value: Decimal = Field(ge=0)
    quarterly_revenue_target: Decimal = Field(ge=0)
    start_date: date
    end_date: date
    renewal_date: date | None = None
    executive_sponsor_id: str | None = None
    opportunity_id: str | None = None
    source_system: str = Field(min_length=1, max_length=80)
    source_record_id: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.end_date < self.start_date:
            raise ValueError("engagement end_date must be on or after start_date")
        return self


class MilestoneRow(ImportModel):
    id: str
    engagement_id: str
    title: str
    due_date: date
    status: str
    completed_date: date | None = None


class RevenueRow(ImportModel):
    id: str
    engagement_id: str
    recognized_on: date
    amount: Decimal = Field(ge=0)


class CapacityRow(ImportModel):
    id: str
    employee_id: str
    period_start: date
    period_end: date
    available_hours: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.period_end < self.period_start:
            raise ValueError("capacity period_end must be on or after period_start")
        return self


class AssignmentRow(ImportModel):
    id: str
    employee_id: str
    engagement_id: str
    allocation_percent: Decimal = Field(gt=0, le=100)
    assignment_role: str | None = None
    billable: bool
    status: str = Field(pattern="^(Active|Planned|Completed|Cancelled)$")
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.end_date < self.start_date:
            raise ValueError("assignment end_date must be on or after start_date")
        return self


class ExecutiveImportBatch(ImportModel):
    engagements: list[EngagementRow] = Field(default_factory=list)
    milestones: list[MilestoneRow] = Field(default_factory=list)
    revenue_records: list[RevenueRow] = Field(default_factory=list)
    capacity: list[CapacityRow] = Field(default_factory=list)
    assignments: list[AssignmentRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def ids_are_unique(self):
        for field in ("engagements", "milestones", "revenue_records", "capacity", "assignments"):
            ids = [item.id for item in getattr(self, field)]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate IDs in {field}")
        return self


def _ids(connection, table) -> set[str]:
    return set(connection.execute(select(table.c.id)).scalars())


def _upsert(connection, table, values: dict) -> None:
    record_id = values["id"]
    exists = connection.execute(select(table.c.id).where(table.c.id == record_id)).scalar_one_or_none()
    if exists:
        connection.execute(update(table).where(table.c.id == record_id).values(**{key: value for key, value in values.items() if key != "id"}))
    else:
        connection.execute(insert(table).values(**values))


def import_executive_batch(engine, batch: ExecutiveImportBatch, *, dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        known_divisions = _ids(connection, divisions)
        known_units = _ids(connection, business_units)
        known_stakeholders = _ids(connection, stakeholders)
        known_opportunities = _ids(connection, opportunities)
        known_employees = _ids(connection, employees)
        known_engagements = _ids(connection, engagements) | {item.id for item in batch.engagements}
        errors = []
        for item in batch.engagements:
            if item.pod_id not in POD_STRUCTURE: errors.append(f"{item.id}: unknown pod {item.pod_id}")
            if item.division_id not in known_divisions: errors.append(f"{item.id}: unknown division {item.division_id}")
            if item.business_unit_id not in known_units: errors.append(f"{item.id}: unknown business unit {item.business_unit_id}")
            if item.executive_sponsor_id and item.executive_sponsor_id not in known_stakeholders: errors.append(f"{item.id}: unknown sponsor {item.executive_sponsor_id}")
            if item.opportunity_id and item.opportunity_id not in known_opportunities: errors.append(f"{item.id}: unknown opportunity {item.opportunity_id}")
        for item in [*batch.milestones, *batch.revenue_records]:
            if item.engagement_id not in known_engagements: errors.append(f"{item.id}: unknown engagement {item.engagement_id}")
        for item in batch.capacity:
            if item.employee_id not in known_employees: errors.append(f"{item.id}: unknown employee {item.employee_id}")
        for item in batch.assignments:
            if item.employee_id not in known_employees: errors.append(f"{item.id}: unknown employee {item.employee_id}")
            if item.engagement_id not in known_engagements: errors.append(f"{item.id}: unknown engagement {item.engagement_id}")
        if errors:
            raise ValueError("; ".join(errors))
        counts = {field: len(getattr(batch, field)) for field in ("engagements", "milestones", "revenue_records", "capacity", "assignments")}
        if dry_run:
            return counts
        for item in batch.engagements:
            values = item.model_dump()
            values.update(updated_at=now, last_synced_at=now)
            if connection.execute(select(engagements.c.id).where(engagements.c.id == item.id)).scalar_one_or_none() is None:
                values["created_at"] = now
            _upsert(connection, engagements, values)
        for field, table in (("milestones", engagement_milestones), ("revenue_records", revenue_records), ("capacity", employee_capacity), ("assignments", engagement_assignments)):
            for item in getattr(batch, field):
                _upsert(connection, table, item.model_dump())
    return counts
