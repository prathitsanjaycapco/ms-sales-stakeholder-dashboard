"""Enforce unique synchronized identities for meetings and opportunities.

Revision ID: 0006_provenance_indexes
Revises: 0005_identity_audit
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_provenance_indexes"
down_revision = "0005_identity_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("meetings")}
    if "uq_meeting_source_record" not in indexes:
        op.create_index("uq_meeting_source_record", "meetings", ["source_system", "source_record_id"], unique=True)
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("opportunities")}
    if "uq_opportunity_source_record" not in indexes:
        op.create_index("uq_opportunity_source_record", "opportunities", ["source_system", "source_record_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    if "uq_opportunity_source_record" in {item["name"] for item in sa.inspect(bind).get_indexes("opportunities")}:
        op.drop_index("uq_opportunity_source_record", table_name="opportunities")
    if "uq_meeting_source_record" in {item["name"] for item in sa.inspect(bind).get_indexes("meetings")}:
        op.drop_index("uq_meeting_source_record", table_name="meetings")
