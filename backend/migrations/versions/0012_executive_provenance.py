"""Add governed provenance to executive engagements.

Revision ID: 0012_executive_provenance
Revises: 0011_production_hardening
"""
from alembic import op
import sqlalchemy as sa


revision = "0012_executive_provenance"
down_revision = "0011_production_hardening"
branch_labels = None
depends_on = None


def _columns(nullable: bool = True):
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=nullable),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=nullable),
        sa.Column("source_system", sa.String(80), nullable=nullable),
        sa.Column("source_record_id", sa.String(240)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {item["name"] for item in inspector.get_columns("executive_engagements")}
    missing = [column for column in _columns() if column.name not in existing_columns]
    for column in missing:
        op.add_column("executive_engagements", column)
    if not missing:
        return
    bind.execute(sa.text(
        "UPDATE executive_engagements SET created_at=COALESCE(created_at, CURRENT_TIMESTAMP), "
        "updated_at=COALESCE(updated_at, CURRENT_TIMESTAMP), source_system=COALESCE(source_system, 'manual')"
    ))
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("executive_engagements", recreate="always") as batch:
            batch.alter_column("created_at", existing_type=sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
            batch.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
            batch.alter_column("source_system", existing_type=sa.String(80), nullable=False, server_default="manual")
            batch.create_unique_constraint("uq_engagement_source_record", ["source_system", "source_record_id"])
    else:
        op.alter_column("executive_engagements", "created_at", nullable=False, server_default=sa.func.current_timestamp())
        op.alter_column("executive_engagements", "updated_at", nullable=False, server_default=sa.func.current_timestamp())
        op.alter_column("executive_engagements", "source_system", nullable=False, server_default="manual")
        op.create_unique_constraint("uq_engagement_source_record", "executive_engagements", ["source_system", "source_record_id"])
    if "idx_executive_engagement_sync" not in {item["name"] for item in sa.inspect(bind).get_indexes("executive_engagements")}:
        op.create_index("idx_executive_engagement_sync", "executive_engagements", ["source_system", "last_synced_at"])


def downgrade() -> None:
    op.drop_index("idx_executive_engagement_sync", table_name="executive_engagements")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("executive_engagements", recreate="always") as batch:
            batch.drop_constraint("uq_engagement_source_record", type_="unique")
            for name in ("last_synced_at", "source_record_id", "source_system", "updated_at", "created_at"):
                batch.drop_column(name)
    else:
        op.drop_constraint("uq_engagement_source_record", "executive_engagements", type_="unique")
        for name in ("last_synced_at", "source_record_id", "source_system", "updated_at", "created_at"):
            op.drop_column("executive_engagements", name)
