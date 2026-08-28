"""Cross-domain foreign keys and query indexes for PostgreSQL.

Revision ID: 0002_cross_domain_integrity
Revises: 0001_canonical_account_model
"""
from alembic import op


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
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, source, target, local, remote in FOREIGN_KEYS:
        op.create_foreign_key(name, source, target, local, remote, ondelete="RESTRICT")
    op.create_index("idx_pod_events_stakeholder_date", "pod_events", ["stakeholder_id", "start_at"])
    op.create_index("idx_pod_events_source_meeting", "pod_events", ["source_meeting_id"], unique=True)
    op.create_index("idx_critical_engagement_status", "pod_critical_items", ["engagement_id", "status"])


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_index("idx_critical_engagement_status", table_name="pod_critical_items")
    op.drop_index("idx_pod_events_source_meeting", table_name="pod_events")
    op.drop_index("idx_pod_events_stakeholder_date", table_name="pod_events")
    for name, source, *_ in reversed(FOREIGN_KEYS):
        op.drop_constraint(name, source, type_="foreignkey")
