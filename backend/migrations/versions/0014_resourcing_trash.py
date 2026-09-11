"""Add recoverable Trash metadata to resourcing records.

Revision ID: 0014_resourcing_trash
Revises: 0013_resourcing_workflow
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_resourcing_trash"
down_revision = "0013_resourcing_workflow"
branch_labels = None
depends_on = None


COLUMNS = (
    ("archived_at", sa.DateTime(timezone=True)),
    ("archived_by_employee_id", sa.String(120)),
    ("archive_reason", sa.Text()),
    ("archive_root_type", sa.String(30)),
    ("archive_root_id", sa.String(150)),
)
TABLES = ("resource_requirements", "resourcing_candidates", "onboarding_records")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in TABLES:
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type in COLUMNS:
            if name not in existing:
                op.add_column(table, sa.Column(name, column_type, nullable=True))
        op.create_index(f"idx_{table}_archive_root", table, ["archived_at", "archive_root_type", "archive_root_id"], if_not_exists=True)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"idx_{table}_archive_root", table_name=table, if_exists=True)
        for name, _column_type in reversed(COLUMNS):
            op.drop_column(table, name)
