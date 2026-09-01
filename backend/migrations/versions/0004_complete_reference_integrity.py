"""Complete remaining cross-domain reference constraints.

Revision ID: 0004_reference_integrity
Revises: 0003_remove_legacy_snapshot
"""
from alembic import op
from sqlalchemy import inspect


revision = "0004_reference_integrity"
down_revision = "0003_remove_legacy_snapshot"
branch_labels = None
depends_on = None


FOREIGN_KEYS = [
    ("fk_division_head", "divisions", "stakeholders", ["head_stakeholder_id"], ["id"]),
    ("fk_focus_pod", "pod_focus", "pods", ["pod_id"], ["id"]),
    ("fk_health_pod", "pod_health_metrics", "pods", ["pod_id"], ["id"]),
    ("fk_change_pod", "pod_change_events", "pods", ["pod_id"], ["id"]),
    ("fk_change_stakeholder", "pod_change_events", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_change_opportunity", "pod_change_events", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_context_pod", "pod_opportunity_contexts", "pods", ["pod_id"], ["id"]),
    ("fk_context_opportunity", "pod_opportunity_contexts", "opportunities", ["opportunity_id"], ["id"]),
    ("fk_critical_engagement", "pod_critical_items", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_milestone_engagement", "pod_milestones", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_metric_history_engagement", "account_metric_history", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_metric_history_employee", "account_metric_history", "capco_employees", ["employee_id"], ["id"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, source, target, local, remote in FOREIGN_KEYS:
        existing = {item.get("name") for item in inspect(bind).get_foreign_keys(source)}
        if name not in existing:
            op.create_foreign_key(name, source, target, local, remote, ondelete="RESTRICT")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for name, source, *_ in reversed(FOREIGN_KEYS):
        if name in {item.get("name") for item in inspect(bind).get_foreign_keys(source)}:
            op.drop_constraint(name, source, type_="foreignkey")
