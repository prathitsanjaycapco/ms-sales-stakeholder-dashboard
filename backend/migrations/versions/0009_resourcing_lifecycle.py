"""Add the canonical resource demand through project deployment lifecycle.

Revision ID: 0009_resourcing_lifecycle
Revises: 0008_account_assistant
"""
from alembic import op

from backend.resourcing_store import (
    candidate_interviews, candidate_offers, candidate_stage_history, candidates,
    onboarding_records, onboarding_steps, resource_requirements,
    resourcing_events, resourcing_seed_registry,
)

revision = "0009_resourcing_lifecycle"
down_revision = "0008_account_assistant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        resource_requirements, candidates, candidate_stage_history,
        candidate_interviews, candidate_offers, onboarding_records,
        onboarding_steps, resourcing_events, resourcing_seed_registry,
    ):
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        resourcing_seed_registry, resourcing_events, onboarding_steps,
        onboarding_records, candidate_offers, candidate_interviews,
        candidate_stage_history, candidates, resource_requirements,
    ):
        table.drop(bind, checkfirst=True)
