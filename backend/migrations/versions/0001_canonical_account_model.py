"""Canonical account model and operating analytics tables.

Revision ID: 0001_canonical_account_model
Revises: None
"""
from alembic import op
from sqlalchemy import MetaData, inspect

from app.canonical_schema import metadata as canonical_metadata
from app.executive_store import executive_metadata
from app.pod_store import pod_metadata


revision = "0001_canonical_account_model"
down_revision = None
branch_labels = None
depends_on = None


def _metadata() -> MetaData:
    result = MetaData()
    for source in (canonical_metadata, pod_metadata, executive_metadata):
        for table in source.sorted_tables:
            if table.name not in result.tables:
                table.to_metadata(result)
    return result


def upgrade() -> None:
    # checkfirst supports databases created by the prototype while making a fresh
    # deployment fully reproducible through Alembic.
    _metadata().create_all(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    _metadata().drop_all(op.get_bind(), checkfirst=True)
