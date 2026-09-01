from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, select

from .canonical_schema import (
    audit_events, meeting_employees, meeting_opportunities, meetings,
    opportunities, opportunity_employees, stakeholder_employee_relationships,
    stakeholders,
)
from .config import settings
from .executive_store import (
    employee_capacity, employee_skills, employees, engagement_assignments,
    engagement_milestones, engagement_stakeholders, engagements, revenue_records,
)
from .models import EmployeeProfile, EmployeeSummary
from .pod_store import pod_critical_items
from .repository import NotFoundError
from .resourcing_store import candidates, onboarding_records, resource_requirements


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
            resourcing = [dict(row) for row in connection.execute(
                select(
                    candidates.c.id.label("candidate_id"), candidates.c.first_name, candidates.c.last_name,
                    candidates.c.stage, candidates.c.expected_start_date, resource_requirements.c.id.label("requirement_id"),
                    resource_requirements.c.title.label("requirement_title"), resource_requirements.c.role,
                    resource_requirements.c.pod_id, resource_requirements.c.engagement_id,
                    onboarding_records.c.id.label("onboarding_id"), onboarding_records.c.overall_status,
                    onboarding_records.c.actual_start_date,
                ).join(resource_requirements, resource_requirements.c.id == candidates.c.resource_requirement_id)
                .outerjoin(onboarding_records, onboarding_records.c.candidate_id == candidates.c.id)
                .where((candidates.c.capco_employee_id == employee_id) | (candidates.c.capco_reviewer_id == employee_id))
                .order_by(candidates.c.updated_at.desc())
            ).mappings()]
        return EmployeeProfile(
            **{key: employee[key] for key in EmployeeSummary.model_fields},
            skills=skills,
            capacity=capacity,
            assignments=assignments,
            stakeholder_relationships=relationships,
            meetings=employee_meetings,
            owned_opportunities=owned_opportunities,
            resourcing=resourcing,
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
            demand = [dict(row) for row in connection.execute(
                select(resource_requirements).where(resource_requirements.c.engagement_id == engagement_id)
                .order_by(resource_requirements.c.target_start_date)
            ).mappings()]
            pipeline = [dict(row) for row in connection.execute(
                select(candidates.c.id, candidates.c.resource_requirement_id, candidates.c.first_name, candidates.c.last_name,
                       candidates.c.stage, candidates.c.expected_start_date)
                .join(resource_requirements, resource_requirements.c.id == candidates.c.resource_requirement_id)
                .where(resource_requirements.c.engagement_id == engagement_id)
            ).mappings()]
            onboarding = [dict(row) for row in connection.execute(
                select(onboarding_records.c.id, onboarding_records.c.candidate_id, onboarding_records.c.expected_start_date,
                       onboarding_records.c.actual_start_date, onboarding_records.c.overall_status)
                .join(candidates, candidates.c.id == onboarding_records.c.candidate_id)
                .join(resource_requirements, resource_requirements.c.id == candidates.c.resource_requirement_id)
                .where(resource_requirements.c.engagement_id == engagement_id)
                .order_by(onboarding_records.c.expected_start_date)
            ).mappings()]
            milestones = [dict(row) for row in connection.execute(
                select(engagement_milestones)
                .where(engagement_milestones.c.engagement_id == engagement_id)
                .order_by(engagement_milestones.c.due_date)
            ).mappings()]
            revenue = [dict(row) for row in connection.execute(
                select(revenue_records)
                .where(revenue_records.c.engagement_id == engagement_id)
                .order_by(revenue_records.c.recognized_on.desc())
            ).mappings()]
            risks = [dict(row) for row in connection.execute(
                select(pod_critical_items)
                .where(pod_critical_items.c.engagement_id == engagement_id)
                .order_by(pod_critical_items.c.status, pod_critical_items.c.severity, pod_critical_items.c.due_date)
            ).mappings()]
            opportunity = dict(connection.execute(
                select(opportunities).where(opportunities.c.id == engagement["opportunity_id"])
            ).mappings().one_or_none() or {}) if engagement["opportunity_id"] else None
        return {
            "engagement": dict(engagement),
            "team": team,
            "stakeholders": sponsors,
            "meetings": discussed_in,
            "milestones": milestones,
            "revenue": revenue,
            "risks": risks,
            "opportunity": opportunity,
            "resourcing": {"requirements": demand, "candidates": pipeline, "onboarding": onboarding},
        }

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

    def data_trust_summary(self) -> dict:
        """Describe the freshness and provenance users can actually verify.

        A source without a persisted synchronization timestamp is reported as
        untracked instead of being made to look current because it has rows.
        """
        now = datetime.now(timezone.utc)

        def normalized(value):
            if value is None:
                return None
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

        def freshness(latest_sync, latest_update, *, governed=False):
            evidence = normalized(latest_sync or (latest_update if governed else None))
            if evidence is None:
                return "untracked"
            age_hours = max(0, (now - evidence).total_seconds() / 3600)
            if age_hours <= 24:
                return "current"
            if age_hours <= 72:
                return "aging"
            return "stale"

        source_tables = (
            ("stakeholders", "Stakeholders", stakeholders, True),
            ("meetings", "Meetings and calendar activity", meetings, True),
            ("opportunities", "Commercial pipeline", opportunities, True),
            ("employees", "Capco workforce", employees, True),
            ("resourcing", "Resourcing and onboarding", resource_requirements, False),
        )
        sources = []
        with self.engine.connect() as connection:
            for key, label, table, has_provenance in source_tables:
                latest_update = connection.execute(select(func.max(table.c.updated_at))).scalar_one_or_none()
                latest_sync = connection.execute(select(func.max(table.c.last_synced_at))).scalar_one_or_none() if has_provenance else None
                row_count = connection.execute(select(func.count()).select_from(table)).scalar_one()
                manual_records = connection.execute(
                    select(func.count()).select_from(table).where(table.c.source_system == "manual")
                ).scalar_one() if has_provenance else 0
                sources.append({
                    "key": key,
                    "label": label,
                    "record_count": row_count,
                    "latest_updated_at": latest_update,
                    "latest_synced_at": latest_sync,
                    "manual_records": manual_records,
                    "externally_sourced_records": row_count - manual_records if has_provenance else 0,
                    "freshness_status": "empty" if not row_count else freshness(latest_sync, latest_update, governed=not has_provenance),
                })

            delivery_count = connection.execute(select(func.count()).select_from(engagements)).scalar_one()
            delivery_dates = connection.execute(select(func.max(engagements.c.end_date))).scalar_one_or_none()
            delivery_updated = connection.execute(select(func.max(engagements.c.updated_at))).scalar_one_or_none()
            delivery_synced = connection.execute(select(func.max(engagements.c.last_synced_at))).scalar_one_or_none()
            delivery_manual = connection.execute(select(func.count()).select_from(engagements).where(engagements.c.source_system == "manual")).scalar_one()
            sources.append({
                "key": "delivery",
                "label": "Delivery portfolio and financials",
                "record_count": delivery_count,
                "latest_updated_at": delivery_updated,
                "latest_synced_at": delivery_synced,
                "manual_records": delivery_manual,
                "externally_sourced_records": delivery_count - delivery_manual,
                "freshness_status": "empty" if not delivery_count else freshness(delivery_synced, delivery_updated),
                "coverage_through": delivery_dates,
            })

        return {
            "generated_at": now,
            "sources": sources,
            "controls": {
                "identity": "trusted_proxy" if settings.auth_mode == "trusted_proxy" else "development",
                "repository": getattr(self.engine, "name", "database"),
                "document_storage": "durable" if settings.document_storage_durable else "local_only",
                "assistant_provider": settings.ai_provider,
                "outbound_notifications": "not_configured",
            },
        }
