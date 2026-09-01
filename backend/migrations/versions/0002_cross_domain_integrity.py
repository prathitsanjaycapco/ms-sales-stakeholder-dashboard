"""Cross-domain foreign keys and query indexes for PostgreSQL.

Revision ID: 0002_cross_domain_integrity
Revises: 0001_canonical_account_model
"""
from alembic import op
from sqlalchemy import inspect


revision = "0002_cross_domain_integrity"
down_revision = "0001_canonical_account_model"
branch_labels = None
depends_on = None


FOREIGN_KEYS = [
    ("fk_pod_events_pod", "pod_events", "pods", ["pod_id"], ["id"]),
    ("fk_pod_events_stakeholder", "pod_events", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_pod_events_opportunity", "pod_events", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_pod_events_meeting", "pod_events", "meetings", ["source_meeting_id"], ["id"]),
    ("fk_pod_attendees_event", "pod_event_attendees", "pod_events", ["event_id"], ["id"]),
    ("fk_pod_tasks_pod", "pod_tasks", "pods", ["pod_id"], ["id"]),
    ("fk_pod_tasks_stakeholder", "pod_tasks", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_pod_tasks_meeting", "pod_tasks", "meetings", ["meeting_id"], ["id"]),
    ("fk_pod_tasks_opportunity", "pod_tasks", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_critical_pod", "pod_critical_items", "pods", ["pod_id"], ["id"]),
    ("fk_critical_stakeholder", "pod_critical_items", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_critical_opportunity", "pod_critical_items", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_milestones_pod", "pod_milestones", "pods", ["pod_id"], ["id"]),
    ("fk_milestones_stakeholder", "pod_milestones", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_milestones_opportunity", "pod_milestones", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_relationship_signal_pod", "pod_relationship_signals", "pods", ["pod_id"], ["id"]),
    ("fk_relationship_signal_stakeholder", "pod_relationship_signals", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_engagement_pod", "executive_engagements", "pods", ["pod_id"], ["id"]),
    ("fk_engagement_sponsor", "executive_engagements", "stakeholders", ["executive_sponsor_id"], ["id"]),
    ("fk_engagement_opportunity", "executive_engagements", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_employee_skills_employee", "employee_skills", "capco_employees", ["employee_id"], ["id"]),
    ("fk_employee_capacity_employee", "employee_capacity", "capco_employees", ["employee_id"], ["id"]),
    ("fk_assignments_employee", "engagement_assignments", "capco_employees", ["employee_id"], ["id"]),
    ("fk_assignments_engagement", "engagement_assignments", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_revenue_engagement", "revenue_records", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_delivery_milestone_engagement", "engagement_milestones", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_demand_pod", "resource_demand", "pods", ["pod_id"], ["id"]),
    ("fk_demand_engagement", "resource_demand", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_demand_opportunity", "resource_demand", "opportunities", ["opportunity_id"], ["id"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, source, target, local, remote in FOREIGN_KEYS:
        existing = {item.get("name") for item in inspect(bind).get_foreign_keys(source)}
        if name not in existing:
            op.create_foreign_key(name, source, target, local, remote, ondelete="RESTRICT")
    for name, table, columns, unique in (
        ("idx_pod_events_stakeholder_date", "pod_events", ["stakeholder_id", "start_at"], False),
        ("idx_pod_events_source_meeting", "pod_events", ["source_meeting_id"], True),
        ("idx_critical_engagement_status", "pod_critical_items", ["engagement_id", "status"], False),
    ):
        existing = {item.get("name") for item in inspect(bind).get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, columns, unique=unique)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, table in (
        ("idx_critical_engagement_status", "pod_critical_items"),
        ("idx_pod_events_source_meeting", "pod_events"),
        ("idx_pod_events_stakeholder_date", "pod_events"),
    ):
        if name in {item.get("name") for item in inspect(bind).get_indexes(table)}:
            op.drop_index(name, table_name=table)
    for name, source, *_ in reversed(FOREIGN_KEYS):
        if name in {item.get("name") for item in inspect(bind).get_foreign_keys(source)}:
            op.drop_constraint(name, source, type_="foreignkey")
