from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import and_, func, select

from .canonical_schema import (
    business_units, divisions, meeting_employees, meeting_opportunities,
    opportunities as opportunity_table, opportunity_employees, pods,
    stakeholder_assignments, stakeholder_employee_relationships, stakeholders,
)
from .executive_store import employees, engagements, engagement_assignments, employee_capacity
from .pod_store import pod_critical_items, pod_event_attendees, pod_events, pod_milestones, pod_tasks
from .repository import POD_STRUCTURE


def _money(value: float) -> float:
    return round(float(value), 2)


def reconcile_account(repository, pod_store, executive_store, anchor: date | None = None) -> dict:
    """Return machine-readable lineage and cross-screen reconciliation evidence."""
    anchor = anchor or date.today()
    active = [item for item in repository.list_opportunities() if item.stage not in {"Closed Won", "Closed Lost"}]
    canonical_by_pod = defaultdict(float)
    canonical_weighted_by_pod = defaultdict(float)
    for item in active:
        person = next((repository.stakeholders.get(value) for value in item.stakeholder_ids if value in repository.stakeholders), None)
        if person:
            canonical_by_pod[person.pod] += item.estimated_value
            canonical_weighted_by_pod[person.pod] += item.estimated_value * item.probability / 100

    executive = executive_store.overview("quarter", anchor=anchor)
    executive_pipeline = executive["accountPulse"]["pipeline"]
    executive_weighted = executive["accountPulse"]["weightedPipeline"]
    checks = []

    def add(name: str, expected, actual, *, scope: str, evidence: list[str] | None = None):
        delta = _money(actual - expected) if isinstance(expected, (int, float)) and isinstance(actual, (int, float)) else None
        checks.append({
            "name": name, "scope": scope, "passed": actual == expected or (delta is not None and abs(delta) < 0.01),
            "expected": expected, "actual": actual, "delta": delta, "evidence_ids": evidence or [],
        })

    add("Executive pipeline equals canonical active opportunities", _money(sum(canonical_by_pod.values())), _money(executive_pipeline), scope="account", evidence=[item.id for item in active])
    add("Executive weighted pipeline uses the canonical value × probability formula", _money(sum(canonical_weighted_by_pod.values())), _money(executive_weighted), scope="account", evidence=[item.id for item in active])
    for pod_name in POD_STRUCTURE:
        dashboard = pod_store.dashboard(pod_name, "week")
        add(f"{pod_name} Pod pipeline equals its canonical opportunities", _money(canonical_by_pod[pod_name]), _money(dashboard["summary"]["pipelineValue"]), scope=pod_name, evidence=[item["id"] for item in dashboard["opportunities"]])
        add(f"{pod_name} weighted pipeline reconciles", _money(canonical_weighted_by_pod[pod_name]), _money(dashboard["summary"]["weightedPipelineValue"]), scope=pod_name)

    canonical_meeting_ids = set(repository.meetings)
    with executive_store.engine.connect() as connection:
        linked_meeting_ids = set(connection.execute(select(pod_events.c.source_meeting_id).where(pod_events.c.source_meeting_id.is_not(None))).scalars())
        orphan_pod_events = connection.execute(
            select(func.count()).select_from(pod_events.outerjoin(pods, pod_events.c.pod_id == pods.c.id)).where(pods.c.id.is_(None))
        ).scalar_one()
        orphan_event_stakeholders = connection.execute(
            select(func.count()).select_from(pod_events.outerjoin(stakeholders, pod_events.c.stakeholder_id == stakeholders.c.id)).where(and_(pod_events.c.stakeholder_id.is_not(None), stakeholders.c.id.is_(None)))
        ).scalar_one()
        orphan_engagement_sponsors = connection.execute(
            select(func.count()).select_from(engagements.outerjoin(stakeholders, engagements.c.executive_sponsor_id == stakeholders.c.id)).where(and_(engagements.c.executive_sponsor_id.is_not(None), stakeholders.c.id.is_(None)))
        ).scalar_one()
        orphan_engagement_opportunities = connection.execute(
            select(func.count()).select_from(engagements.outerjoin(opportunity_table, engagements.c.opportunity_id == opportunity_table.c.id)).where(and_(engagements.c.opportunity_id.is_not(None), opportunity_table.c.id.is_(None)))
        ).scalar_one()
        multiple_current_assignments = connection.execute(select(func.count()).select_from(
            select(stakeholder_assignments.c.stakeholder_id)
            .where(stakeholder_assignments.c.is_current.is_(True))
            .group_by(stakeholder_assignments.c.stakeholder_id)
            .having(func.count() > 1).subquery()
        )).scalar_one()
        multiple_primary_technology = connection.execute(select(func.count()).select_from(
            select(stakeholder_assignments.c.business_unit_id)
            .where(and_(stakeholder_assignments.c.is_current.is_(True), stakeholder_assignments.c.is_primary_technology.is_(True)))
            .group_by(stakeholder_assignments.c.business_unit_id)
            .having(func.count() > 1).subquery()
        )).scalar_one()
        duplicate_source_records = connection.execute(select(func.count()).select_from(
            select(stakeholders.c.source_system, stakeholders.c.source_record_id)
            .where(stakeholders.c.source_record_id.is_not(None))
            .group_by(stakeholders.c.source_system, stakeholders.c.source_record_id)
            .having(func.count() > 1).subquery()
        )).scalar_one()
        duplicate_employee_sources = connection.execute(select(func.count()).select_from(
            select(employees.c.source_system, employees.c.source_record_id)
            .where(employees.c.source_record_id.is_not(None))
            .group_by(employees.c.source_system, employees.c.source_record_id)
            .having(func.count() > 1).subquery()
        )).scalar_one()
        orphan_meeting_employees = connection.execute(select(func.count()).select_from(
            meeting_employees.outerjoin(employees, meeting_employees.c.employee_id == employees.c.id)
        ).where(employees.c.id.is_(None))).scalar_one()
        orphan_opportunity_employees = connection.execute(select(func.count()).select_from(
            opportunity_employees.outerjoin(employees, opportunity_employees.c.employee_id == employees.c.id)
        ).where(employees.c.id.is_(None))).scalar_one()
        orphan_relationship_employees = connection.execute(select(func.count()).select_from(
            stakeholder_employee_relationships.outerjoin(employees, stakeholder_employee_relationships.c.employee_id == employees.c.id)
        ).where(employees.c.id.is_(None))).scalar_one()
        orphan_meeting_opportunities = connection.execute(select(func.count()).select_from(
            meeting_opportunities.outerjoin(opportunity_table, meeting_opportunities.c.opportunity_id == opportunity_table.c.id)
        ).where(opportunity_table.c.id.is_(None))).scalar_one()
        unresolved_engagement_scope = connection.execute(select(func.count()).select_from(
            engagements
            .outerjoin(divisions, engagements.c.division_id == divisions.c.id)
            .outerjoin(business_units, engagements.c.business_unit_id == business_units.c.id)
        ).where((divisions.c.id.is_(None)) | (business_units.c.id.is_(None)))).scalar_one()
        unlinked_operating_people = sum(connection.execute(
            select(func.count()).select_from(table).where(employee_column.is_(None))
        ).scalar_one() for table, employee_column in (
            (pod_event_attendees, pod_event_attendees.c.employee_id),
            (pod_tasks, pod_tasks.c.owner_employee_id),
            (pod_critical_items, pod_critical_items.c.owner_employee_id),
            (pod_milestones, pod_milestones.c.owner_employee_id),
        ))

    missing_calendar_links = sorted(canonical_meeting_ids - linked_meeting_ids)
    add("Canonical meetings are represented by Pod calendar events", 0, len(missing_calendar_links), scope="account", evidence=missing_calendar_links[:50])
    add("Pod facts reference canonical pods", 0, orphan_pod_events, scope="database")
    add("Pod events reference canonical stakeholders", 0, orphan_event_stakeholders, scope="database")
    add("Engagement sponsors reference canonical stakeholders", 0, orphan_engagement_sponsors, scope="database")
    add("Engagement opportunities reference canonical opportunities", 0, orphan_engagement_opportunities, scope="database")
    add("Stakeholders have one current organizational assignment", 0, multiple_current_assignments, scope="database")
    add("Business units have at most one current primary technology stakeholder", 0, multiple_primary_technology, scope="database")
    add("External source identities are unique", 0, duplicate_source_records, scope="database")
    add("Capco source identities are unique", 0, duplicate_employee_sources, scope="database")
    add("Meeting attendees reference canonical Capco employees", 0, orphan_meeting_employees, scope="database")
    add("Opportunity owners reference canonical Capco employees", 0, orphan_opportunity_employees, scope="database")
    add("Stakeholder relationships reference canonical Capco employees", 0, orphan_relationship_employees, scope="database")
    add("Meeting opportunity links resolve", 0, orphan_meeting_opportunities, scope="database")
    add("Engagements use canonical division and business-unit IDs", 0, unresolved_engagement_scope, scope="database")
    add("Operating records use canonical employee IDs", 0, unlinked_operating_people, scope="database")

    # Workforce lineage is recomputed from the same persisted capacity and allocation records.
    start = date(anchor.year, ((anchor.month - 1) // 3) * 3 + 1, 1)
    end_month = start.month + 3
    end = date(start.year + (end_month > 12), 1 if end_month > 12 else end_month, 1)
    period_end = end - timedelta(days=1)
    with executive_store.engine.connect() as connection:
        capacity_rows = connection.execute(select(employee_capacity).where(and_(employee_capacity.c.period_start < end, employee_capacity.c.period_end >= start))).mappings().all()
        assignment_rows = connection.execute(select(engagement_assignments).join(
            engagements, engagements.c.id == engagement_assignments.c.engagement_id,
        ).where(and_(
            func.lower(engagements.c.status) == "active",
            engagement_assignments.c.start_date < end,
            engagement_assignments.c.end_date >= start,
        ))).mappings().all()
    capacity_by_person = {}
    for row in capacity_rows:
        capacity_days = executive_store._working_days(row["period_start"], row["period_end"])
        overlap_days = executive_store._overlap_working_days(start, period_end, row["period_start"], row["period_end"])
        capacity_by_person[row["employee_id"]] = capacity_by_person.get(row["employee_id"], 0) + float(row["available_hours"]) * overlap_days / capacity_days
    available = sum(capacity_by_person.values())
    period_days = executive_store._working_days(start, period_end)
    billable = sum(
        capacity_by_person.get(row["employee_id"], 0)
        * executive_store._overlap_working_days(start, period_end, row["start_date"], row["end_date"]) / period_days
        * float(row["allocation_percent"]) / 100
        for row in assignment_rows if row["billable"]
    )
    expected_utilization = billable / available if available else None
    actual_utilization = executive["workforce"]["utilization"]
    add("Executive utilization equals billable allocation ÷ available capacity", round(expected_utilization, 8) if expected_utilization is not None else None, round(actual_utilization, 8) if actual_utilization is not None else None, scope="workforce", evidence=[row["id"] for row in assignment_rows])

    failed = [item for item in checks if not item["passed"]]
    return {
        "status": "passed" if not failed else "failed", "as_of": anchor.isoformat(),
        "checks": checks, "failed_checks": len(failed), "total_checks": len(checks),
        "source": "normalized-sql", "metric_definitions": executive["meta"]["definitions"],
    }
