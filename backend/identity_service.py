from __future__ import annotations

from sqlalchemy import and_, select

from .canonical_schema import (
    audit_events, meeting_employees, meeting_opportunities, meetings,
    opportunities, opportunity_employees, stakeholder_employee_relationships,
    stakeholders,
)
from .executive_store import (
    employee_capacity, employee_skills, employees, engagement_assignments,
    engagement_stakeholders, engagements,
)
from .models import EmployeeProfile, EmployeeSummary
from .repository import NotFoundError


class IdentityService:
    def __init__(self, engine) -> None:
        self.engine = engine

    def list_employees(self, active: bool | None = True, search: str | None = None) -> list[EmployeeSummary]:
        statement = select(employees)
        if active is not None:
            statement = statement.where(employees.c.active.is_(active))
        with self.engine.connect() as connection:
            rows = connection.execute(statement.order_by(employees.c.name)).mappings().all()
        if search:
            needle = search.casefold().strip()
            rows = [row for row in rows if needle in f"{row['name']} {row['role']} {row['location']} {row['level']}".casefold()]
        return [EmployeeSummary(**{key: row[key] for key in EmployeeSummary.model_fields}) for row in rows]

    def employee_profile(self, employee_id: str) -> EmployeeProfile:
        with self.engine.connect() as connection:
            employee = connection.execute(select(employees).where(employees.c.id == employee_id)).mappings().one_or_none()
            if employee is None:
                raise NotFoundError("Capco employee not found")
            skills = list(connection.execute(
                select(employee_skills.c.capability).where(employee_skills.c.employee_id == employee_id).order_by(employee_skills.c.capability)
            ).scalars())
            capacity = [dict(row) for row in connection.execute(
                select(employee_capacity).where(employee_capacity.c.employee_id == employee_id).order_by(employee_capacity.c.period_start.desc())
            ).mappings()]
            assignments = [dict(row) for row in connection.execute(
                select(
                    engagement_assignments.c.id, engagement_assignments.c.engagement_id,
                    engagements.c.name.label("engagement_name"), engagements.c.pod_id,
                    engagement_assignments.c.allocation_percent, engagement_assignments.c.billable,
                    engagement_assignments.c.start_date, engagement_assignments.c.end_date,
                ).join(engagements, engagements.c.id == engagement_assignments.c.engagement_id)
                .where(engagement_assignments.c.employee_id == employee_id)
                .order_by(engagement_assignments.c.end_date.desc())
            ).mappings()]
            relationships = [dict(row) for row in connection.execute(
                select(
                    stakeholder_employee_relationships.c.id,
                    stakeholder_employee_relationships.c.stakeholder_id,
                    stakeholders.c.name.label("stakeholder_name"),
                    stakeholder_employee_relationships.c.relationship_role,
                    stakeholder_employee_relationships.c.is_primary,
                    stakeholder_employee_relationships.c.effective_from,
                    stakeholder_employee_relationships.c.effective_to,
                    stakeholder_employee_relationships.c.is_current,
                ).join(stakeholders, stakeholders.c.id == stakeholder_employee_relationships.c.stakeholder_id)
                .where(stakeholder_employee_relationships.c.employee_id == employee_id)
                .order_by(stakeholder_employee_relationships.c.is_current.desc(), stakeholder_employee_relationships.c.effective_from.desc())
            ).mappings()]
            employee_meetings = [dict(row) for row in connection.execute(
                select(
                    meetings.c.id, meetings.c.subject, meetings.c.meeting_date,
                    meeting_employees.c.attendee_role, meeting_employees.c.is_organizer,
                ).join(meeting_employees, meeting_employees.c.meeting_id == meetings.c.id)
                .where(meeting_employees.c.employee_id == employee_id)
                .order_by(meetings.c.meeting_date.desc()).limit(50)
            ).mappings()]
            owned_opportunities = [dict(row) for row in connection.execute(
                select(
                    opportunities.c.id, opportunities.c.name, opportunities.c.stage,
                    opportunities.c.estimated_value, opportunities.c.probability,
                    opportunities.c.target_close_date, opportunity_employees.c.owner_role,
                    opportunity_employees.c.is_primary,
                ).join(opportunity_employees, opportunity_employees.c.opportunity_id == opportunities.c.id)
                .where(opportunity_employees.c.employee_id == employee_id)
                .order_by(opportunities.c.updated_at.desc())
            ).mappings()]
        return EmployeeProfile(
            **{key: employee[key] for key in EmployeeSummary.model_fields},
            skills=skills,
            capacity=capacity,
            assignments=assignments,
            stakeholder_relationships=relationships,
            meetings=employee_meetings,
            owned_opportunities=owned_opportunities,
        )

    def engagement_detail(self, engagement_id: str) -> dict:
        with self.engine.connect() as connection:
            engagement = connection.execute(select(engagements).where(engagements.c.id == engagement_id)).mappings().one_or_none()
            if engagement is None:
                raise NotFoundError("Engagement not found")
            team = [dict(row) for row in connection.execute(
                select(
                    employees.c.id, employees.c.name, employees.c.role, employees.c.level,
                    engagement_assignments.c.allocation_percent, engagement_assignments.c.billable,
                    engagement_assignments.c.start_date, engagement_assignments.c.end_date,
                ).join(engagement_assignments, engagement_assignments.c.employee_id == employees.c.id)
                .where(engagement_assignments.c.engagement_id == engagement_id)
                .order_by(employees.c.name)
            ).mappings()]
            sponsors = [dict(row) for row in connection.execute(
                select(
                    stakeholders.c.id, stakeholders.c.name, stakeholders.c.title,
                    engagement_stakeholders.c.relationship_role, engagement_stakeholders.c.is_primary,
                ).join(engagement_stakeholders, engagement_stakeholders.c.stakeholder_id == stakeholders.c.id)
                .where(engagement_stakeholders.c.engagement_id == engagement_id)
                .order_by(engagement_stakeholders.c.is_primary.desc(), stakeholders.c.name)
            ).mappings()]
            discussed_in = [dict(row) for row in connection.execute(
                select(meetings.c.id, meetings.c.subject, meetings.c.meeting_date)
                .join(meeting_opportunities, meeting_opportunities.c.meeting_id == meetings.c.id)
                .where(meeting_opportunities.c.opportunity_id == engagement["opportunity_id"])
                .order_by(meetings.c.meeting_date.desc())
            ).mappings()] if engagement["opportunity_id"] else []
        return {"engagement": dict(engagement), "team": team, "stakeholders": sponsors, "meetings": discussed_in}

    def list_audit_events(self, limit: int = 100, entity_type: str | None = None, entity_id: str | None = None) -> list[dict]:
        statement = select(audit_events)
        predicates = []
        if entity_type:
            predicates.append(audit_events.c.entity_type == entity_type)
        if entity_id:
            predicates.append(audit_events.c.entity_id == entity_id)
        if predicates:
            statement = statement.where(and_(*predicates))
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement.order_by(audit_events.c.occurred_at.desc()).limit(limit)).mappings()]
