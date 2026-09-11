"""Align the role sourcing outcome constraint with the canonical model.

Revision ID: 0016_bench_outcome_check
Revises: 0015_role_office_directory
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_bench_outcome_check"
down_revision = "0015_role_office_directory"
branch_labels = None
depends_on = None


CONSTRAINT = "ck_resource_requirement_bench_outcome"
RULE = "bench_outcome IS NULL OR bench_outcome IN ('CANDIDATE_AVAILABLE', 'NO_CANDIDATE', 'EXISTING_PIPELINE')"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = {item["name"] for item in sa.inspect(bind).get_check_constraints("resource_requirements")}
    if CONSTRAINT not in existing:
        op.create_check_constraint(CONSTRAINT, "resource_requirements", RULE)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(CONSTRAINT, "resource_requirements", type_="check")
