"""Cross-domain PostgreSQL constraints represented in canonical migration metadata.

The Pod and Executive stores retain separate SQLAlchemy ``MetaData`` objects so
they can be tested independently.  References between those stores and the
canonical account model are therefore attached after the metadata is combined
for Alembic.
"""
from __future__ import annotations

from sqlalchemy import ForeignKeyConstraint, Index, MetaData


POSTGRESQL_FOREIGN_KEYS = (
    ("fk_pod_events_pod", "pod_events", "pods", ("pod_id",), ("id",)),
    ("fk_pod_events_stakeholder", "pod_events", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_pod_events_opportunity", "pod_events", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_pod_events_meeting", "pod_events", "meetings", ("source_meeting_id",), ("id",)),
    ("fk_pod_attendees_event", "pod_event_attendees", "pod_events", ("event_id",), ("id",)),
    ("fk_pod_tasks_pod", "pod_tasks", "pods", ("pod_id",), ("id",)),
    ("fk_pod_tasks_stakeholder", "pod_tasks", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_pod_tasks_meeting", "pod_tasks", "meetings", ("meeting_id",), ("id",)),
    ("fk_pod_tasks_opportunity", "pod_tasks", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_critical_pod", "pod_critical_items", "pods", ("pod_id",), ("id",)),
    ("fk_critical_stakeholder", "pod_critical_items", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_critical_opportunity", "pod_critical_items", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_milestones_pod", "pod_milestones", "pods", ("pod_id",), ("id",)),
    ("fk_milestones_stakeholder", "pod_milestones", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_milestones_opportunity", "pod_milestones", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_relationship_signal_pod", "pod_relationship_signals", "pods", ("pod_id",), ("id",)),
    ("fk_relationship_signal_stakeholder", "pod_relationship_signals", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_engagement_pod", "executive_engagements", "pods", ("pod_id",), ("id",)),
    ("fk_engagement_sponsor", "executive_engagements", "stakeholders", ("executive_sponsor_id",), ("id",)),
    ("fk_engagement_opportunity", "executive_engagements", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_employee_skills_employee", "employee_skills", "capco_employees", ("employee_id",), ("id",)),
    ("fk_employee_capacity_employee", "employee_capacity", "capco_employees", ("employee_id",), ("id",)),
    ("fk_assignments_employee", "engagement_assignments", "capco_employees", ("employee_id",), ("id",)),
    ("fk_assignments_engagement", "engagement_assignments", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_revenue_engagement", "revenue_records", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_delivery_milestone_engagement", "engagement_milestones", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_demand_pod", "resource_demand", "pods", ("pod_id",), ("id",)),
    ("fk_demand_engagement", "resource_demand", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_demand_opportunity", "resource_demand", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_division_head", "divisions", "stakeholders", ("head_stakeholder_id",), ("id",)),
    ("fk_focus_pod", "pod_focus", "pods", ("pod_id",), ("id",)),
    ("fk_health_pod", "pod_health_metrics", "pods", ("pod_id",), ("id",)),
    ("fk_change_pod", "pod_change_events", "pods", ("pod_id",), ("id",)),
    ("fk_change_stakeholder", "pod_change_events", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_change_opportunity", "pod_change_events", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_context_pod", "pod_opportunity_contexts", "pods", ("pod_id",), ("id",)),
    ("fk_context_opportunity", "pod_opportunity_contexts", "opportunities", ("opportunity_id",), ("id",)),
    ("fk_critical_engagement", "pod_critical_items", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_milestone_engagement", "pod_milestones", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_metric_history_engagement", "account_metric_history", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_metric_history_employee", "account_metric_history", "capco_employees", ("employee_id",), ("id",)),
    ("fk_meeting_employees_employee", "meeting_employees", "capco_employees", ("employee_id",), ("id",)),
    ("fk_opportunity_employees_employee", "opportunity_employees", "capco_employees", ("employee_id",), ("id",)),
    ("fk_stakeholder_employee_relationship_employee", "stakeholder_employee_relationships", "capco_employees", ("employee_id",), ("id",)),
    ("fk_engagement_stakeholders_engagement", "engagement_stakeholders", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_engagement_stakeholders_stakeholder", "engagement_stakeholders", "stakeholders", ("stakeholder_id",), ("id",)),
    ("fk_engagement_division", "executive_engagements", "divisions", ("division_id",), ("id",)),
    ("fk_engagement_business_unit", "executive_engagements", "business_units", ("business_unit_id",), ("id",)),
    ("fk_pod_attendee_employee", "pod_event_attendees", "capco_employees", ("employee_id",), ("id",)),
    ("fk_pod_task_owner_employee", "pod_tasks", "capco_employees", ("owner_employee_id",), ("id",)),
    ("fk_critical_owner_employee", "pod_critical_items", "capco_employees", ("owner_employee_id",), ("id",)),
    ("fk_pod_milestone_owner_employee", "pod_milestones", "capco_employees", ("owner_employee_id",), ("id",)),
    ("fk_requirement_pod", "resource_requirements", "pods", ("pod_id",), ("id",)),
    ("fk_requirement_division", "resource_requirements", "divisions", ("division_id",), ("id",)),
    ("fk_requirement_business_unit", "resource_requirements", "business_units", ("business_unit_id",), ("id",)),
    ("fk_requirement_engagement", "resource_requirements", "executive_engagements", ("engagement_id",), ("id",)),
    ("fk_requirement_owner", "resource_requirements", "capco_employees", ("request_owner_capco_employee_id",), ("id",)),
    ("fk_requirement_client", "resource_requirements", "stakeholders", ("client_stakeholder_id",), ("id",)),
    ("fk_candidate_employee", "resourcing_candidates", "capco_employees", ("capco_employee_id",), ("id",)),
    ("fk_candidate_capco_reviewer", "resourcing_candidates", "capco_employees", ("capco_reviewer_id",), ("id",)),
    ("fk_candidate_ms_reviewer", "resourcing_candidates", "stakeholders", ("ms_reviewer_stakeholder_id",), ("id",)),
    ("fk_stage_history_actor", "candidate_stage_history", "capco_employees", ("changed_by_employee_id",), ("id",)),
    ("fk_resourcing_event_actor", "resourcing_events", "capco_employees", ("actor_employee_id",), ("id",)),
    ("fk_note_author_employee", "notes", "capco_employees", ("author_employee_id",), ("id",)),
    ("fk_document_owner_employee", "stakeholder_documents", "capco_employees", ("owner_employee_id",), ("id",)),
    ("fk_audit_actor_employee", "audit_events", "capco_employees", ("actor_employee_id",), ("id",)),
)

POSTGRESQL_INDEXES = (
    ("idx_pod_events_stakeholder_date", "pod_events", ("stakeholder_id", "start_at"), False),
    ("idx_pod_events_source_meeting", "pod_events", ("source_meeting_id",), True),
    ("idx_critical_engagement_status", "pod_critical_items", ("engagement_id", "status"), False),
)


def attach_postgresql_integrity(metadata: MetaData) -> None:
    """Attach the PostgreSQL-only cross-domain objects to combined metadata."""
    existing_constraints = {
        constraint.name
        for table in metadata.tables.values()
        for constraint in table.constraints
        if constraint.name
    }
    for name, source, target, local_columns, remote_columns in POSTGRESQL_FOREIGN_KEYS:
        if name in existing_constraints:
            continue
        metadata.tables[source].append_constraint(
            ForeignKeyConstraint(
                local_columns,
                tuple(f"{target}.{column}" for column in remote_columns),
                name=name,
                ondelete="RESTRICT",
            )
        )

    existing_indexes = {
        index.name
        for table in metadata.tables.values()
        for index in table.indexes
        if index.name
    }
    for name, table_name, column_names, unique in POSTGRESQL_INDEXES:
        if name in existing_indexes:
            continue
        table = metadata.tables[table_name]
        Index(name, *(table.c[column] for column in column_names), unique=unique)
