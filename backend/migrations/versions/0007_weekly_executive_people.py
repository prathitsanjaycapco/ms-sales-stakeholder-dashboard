"""Make Capco people and assignments first-class weekly operating entities.

Revision ID: 0007_weekly_executive_people
Revises: 0006_provenance_indexes
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_weekly_executive_people"
down_revision = "0006_provenance_indexes"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    employee_columns = _columns(bind, "capco_employees")
    additions = (
        ("first_name", sa.String(90)),
        ("last_name", sa.String(90)),
        ("title", sa.String(160)),
        ("capability", sa.String(120)),
        ("manager_employee_id", sa.String(120)),
    )
    for name, column_type in additions:
        if name not in employee_columns:
            op.add_column("capco_employees", sa.Column(name, column_type))
    is_sqlite = bind.dialect.name == "sqlite"
    if "created_at" not in employee_columns:
        op.add_column("capco_employees", sa.Column("created_at", sa.DateTime(timezone=True), nullable=is_sqlite, server_default=None if is_sqlite else sa.func.current_timestamp()))
    if "updated_at" not in employee_columns:
        op.add_column("capco_employees", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=is_sqlite, server_default=None if is_sqlite else sa.func.current_timestamp()))

    assignment_columns = _columns(bind, "engagement_assignments")
    if "assignment_role" not in assignment_columns:
        op.add_column("engagement_assignments", sa.Column("assignment_role", sa.String(120)))
    if "status" not in assignment_columns:
        op.add_column("engagement_assignments", sa.Column("status", sa.String(30), nullable=False, server_default="Active"))

    people = bind.execute(sa.text("SELECT id, name, role FROM capco_employees")).mappings().all()
    bind.execute(sa.text("UPDATE capco_employees SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    bind.execute(sa.text("UPDATE capco_employees SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
    for person in people:
        first_name, _, last_name = person["name"].partition(" ")
        bind.execute(sa.text(
            "UPDATE capco_employees SET first_name=:first_name, last_name=:last_name, "
            "title=COALESCE(title, :role), capability=COALESCE(capability, :role) WHERE id=:id"
        ), {"id": person["id"], "first_name": first_name, "last_name": last_name, "role": person["role"]})
        bind.execute(sa.text(
            "UPDATE engagement_assignments SET assignment_role=COALESCE(assignment_role, :role), "
            "status=COALESCE(status, 'Active') WHERE employee_id=:id"
        ), {"id": person["id"], "role": person["role"]})

    if is_sqlite:
        with op.batch_alter_table("capco_employees") as batch:
            batch.alter_column("created_at", existing_type=sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
            batch.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))

    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("capco_employees")}
    if "idx_capco_employees_manager" not in indexes:
        op.create_index("idx_capco_employees_manager", "capco_employees", ["manager_employee_id"])


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {item["name"] for item in sa.inspect(bind).get_indexes("capco_employees")}
    if "idx_capco_employees_manager" in indexes:
        op.drop_index("idx_capco_employees_manager", table_name="capco_employees")
    for name in ("status", "assignment_role"):
        if name in _columns(bind, "engagement_assignments"):
            op.drop_column("engagement_assignments", name)
    for name in ("updated_at", "created_at", "manager_employee_id", "capability", "title", "last_name", "first_name"):
        if name in _columns(bind, "capco_employees"):
            op.drop_column("capco_employees", name)
