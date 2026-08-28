"""Remove the legacy snapshot after canonical import and normalize tag nullability.

Revision ID: 0003_remove_legacy_snapshot
Revises: 0002_cross_domain_integrity
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_remove_legacy_snapshot"
down_revision = "0002_cross_domain_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    table_names = set(inspector.get_table_names())
    if "repository_snapshots" in table_names:
        canonical_count = connection.execute(sa.text("SELECT count(*) FROM stakeholders")).scalar_one()
        if canonical_count == 0:
            raise RuntimeError("Legacy snapshot has not been imported. Run `python -m backend.manage import-legacy` before upgrading.")
        op.drop_table("repository_snapshots")
    for table_name in ("pod_events", "pod_tasks", "pod_critical_items", "pod_milestones"):
        columns = {column["name"]: column for column in sa.inspect(connection).get_columns(table_name)}
        if columns["tags"]["nullable"]:
            connection.execute(sa.text(f"UPDATE {table_name} SET tags = '[]' WHERE tags IS NULL"))
            with op.batch_alter_table(table_name) as batch:
                batch.alter_column("tags", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.create_table(
        "repository_snapshots",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
