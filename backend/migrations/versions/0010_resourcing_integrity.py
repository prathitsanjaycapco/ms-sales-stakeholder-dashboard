"""Enforce canonical resourcing references across account domains.

Revision ID: 0010_resourcing_integrity
Revises: 0009_resourcing_lifecycle
"""
from alembic import op
from sqlalchemy import inspect

revision = "0010_resourcing_integrity"
down_revision = "0009_resourcing_lifecycle"
branch_labels = None
depends_on = None

INTERNAL_FOREIGN_KEYS = [
    ("fk_candidate_requirement", "resourcing_candidates", "resource_requirements", ["resource_requirement_id"], ["id"], "CASCADE"),
    ("fk_stage_history_candidate", "candidate_stage_history", "resourcing_candidates", ["candidate_id"], ["id"], "CASCADE"),
    ("fk_interview_candidate", "candidate_interviews", "resourcing_candidates", ["candidate_id"], ["id"], "CASCADE"),
    ("fk_offer_candidate", "candidate_offers", "resourcing_candidates", ["candidate_id"], ["id"], "CASCADE"),
    ("fk_onboarding_candidate", "onboarding_records", "resourcing_candidates", ["candidate_id"], ["id"], "CASCADE"),
    ("fk_onboarding_step_record", "onboarding_steps", "onboarding_records", ["onboarding_record_id"], ["id"], "CASCADE"),
    ("fk_resourcing_event_requirement", "resourcing_events", "resource_requirements", ["requirement_id"], ["id"], "CASCADE"),
    ("fk_resourcing_event_candidate", "resourcing_events", "resourcing_candidates", ["candidate_id"], ["id"], "CASCADE"),
    ("fk_resourcing_event_onboarding", "resourcing_events", "onboarding_records", ["onboarding_record_id"], ["id"], "CASCADE"),
]

EXTERNAL_FOREIGN_KEYS = [
    ("fk_requirement_pod", "resource_requirements", "pods", ["pod_id"], ["id"], "RESTRICT"),
    ("fk_requirement_division", "resource_requirements", "divisions", ["division_id"], ["id"], "RESTRICT"),
    ("fk_requirement_business_unit", "resource_requirements", "business_units", ["business_unit_id"], ["id"], "RESTRICT"),
    ("fk_requirement_engagement", "resource_requirements", "executive_engagements", ["engagement_id"], ["id"], "RESTRICT"),
    ("fk_requirement_owner", "resource_requirements", "capco_employees", ["request_owner_capco_employee_id"], ["id"], "RESTRICT"),
    ("fk_requirement_client", "resource_requirements", "stakeholders", ["client_stakeholder_id"], ["id"], "RESTRICT"),
    ("fk_candidate_employee", "resourcing_candidates", "capco_employees", ["capco_employee_id"], ["id"], "RESTRICT"),
    ("fk_candidate_capco_reviewer", "resourcing_candidates", "capco_employees", ["capco_reviewer_id"], ["id"], "RESTRICT"),
    ("fk_candidate_ms_reviewer", "resourcing_candidates", "stakeholders", ["ms_reviewer_stakeholder_id"], ["id"], "RESTRICT"),
    ("fk_stage_history_actor", "candidate_stage_history", "capco_employees", ["changed_by_employee_id"], ["id"], "RESTRICT"),
    ("fk_resourcing_event_actor", "resourcing_events", "capco_employees", ["actor_employee_id"], ["id"], "RESTRICT"),
]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    inspector = inspect(op.get_bind())
    for name, source, target, local, remote, ondelete in INTERNAL_FOREIGN_KEYS + EXTERNAL_FOREIGN_KEYS:
        existing = {item.get("name") for item in inspector.get_foreign_keys(source)}
        if name not in existing:
            op.create_foreign_key(name, source, target, local, remote, ondelete=ondelete)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name, source, *_ in reversed(INTERNAL_FOREIGN_KEYS + EXTERNAL_FOREIGN_KEYS):
        op.drop_constraint(name, source, type_="foreignkey")
