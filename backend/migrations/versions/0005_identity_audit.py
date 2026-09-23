"""Canonical Capco identities, project scope, relationship joins, and audit events.

Revision ID: 0005_identity_audit
Revises: 0004_reference_integrity
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.canonical_schema import (
    audit_events,
    meeting_employees,
    meeting_opportunities,
    opportunity_employees,
    stakeholder_employee_relationships,
)
from app.executive_store import engagement_stakeholders


revision = "0005_identity_audit"
down_revision = "0004_reference_integrity"
branch_labels = None
depends_on = None


NEW_FOREIGN_KEYS = (
    ("fk_meeting_employees_employee", "meeting_employees", "capco_employees", ["employee_id"], ["id"]),
    ("fk_opportunity_employees_employee", "opportunity_employees", "capco_employees", ["employee_id"], ["id"]),
    ("fk_stakeholder_employee_relationship_employee", "stakeholder_employee_relationships", "capco_employees", ["employee_id"], ["id"]),
    ("fk_engagement_stakeholders_engagement", "engagement_stakeholders", "executive_engagements", ["engagement_id"], ["id"]),
    ("fk_engagement_stakeholders_stakeholder", "engagement_stakeholders", "stakeholders", ["stakeholder_id"], ["id"]),
    ("fk_engagement_division", "executive_engagements", "divisions", ["division_id"], ["id"]),
    ("fk_engagement_business_unit", "executive_engagements", "business_units", ["business_unit_id"], ["id"]),
    ("fk_pod_attendee_employee", "pod_event_attendees", "capco_employees", ["employee_id"], ["id"]),
    ("fk_pod_task_owner_employee", "pod_tasks", "capco_employees", ["owner_employee_id"], ["id"]),
    ("fk_critical_owner_employee", "pod_critical_items", "capco_employees", ["owner_employee_id"], ["id"]),
    ("fk_pod_milestone_owner_employee", "pod_milestones", "capco_employees", ["owner_employee_id"], ["id"]),
    ("fk_note_author_employee", "notes", "capco_employees", ["author_employee_id"], ["id"]),
    ("fk_document_owner_employee", "stakeholder_documents", "capco_employees", ["owner_employee_id"], ["id"]),
    ("fk_audit_actor_employee", "audit_events", "capco_employees", ["actor_employee_id"], ["id"]),
)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _add_column(bind, table_name: str, column: sa.Column) -> None:
    if not _has_column(bind, table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(bind, name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if name not in {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}:
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()

    _add_column(bind, "notes", sa.Column("author_employee_id", sa.String(120)))
    _add_column(bind, "notes", sa.Column("created_by", sa.String(180)))
    _add_column(bind, "notes", sa.Column("updated_by", sa.String(180)))
    _add_column(bind, "stakeholder_documents", sa.Column("owner_employee_id", sa.String(120)))
    _add_column(bind, "stakeholder_documents", sa.Column("created_by", sa.String(180)))
    _add_column(bind, "stakeholder_documents", sa.Column("updated_by", sa.String(180)))
    _add_column(bind, "pod_event_attendees", sa.Column("employee_id", sa.String(120)))
    _add_column(bind, "pod_tasks", sa.Column("owner_employee_id", sa.String(120)))
    _add_column(bind, "pod_critical_items", sa.Column("owner_employee_id", sa.String(120)))
    _add_column(bind, "pod_milestones", sa.Column("owner_employee_id", sa.String(120)))
    _add_column(bind, "executive_engagements", sa.Column("division_id", sa.String(160)))
    _add_column(bind, "executive_engagements", sa.Column("business_unit_id", sa.String(220)))
    _add_column(bind, "capco_employees", sa.Column("source_system", sa.String(80), server_default="manual"))
    _add_column(bind, "capco_employees", sa.Column("source_record_id", sa.String(240)))
    _add_column(bind, "capco_employees", sa.Column("last_synced_at", sa.DateTime(timezone=True)))

    for table in (
        meeting_employees,
        opportunity_employees,
        meeting_opportunities,
        stakeholder_employee_relationships,
        engagement_stakeholders,
        audit_events,
    ):
        table.create(bind, checkfirst=True)

    bind.execute(sa.text("""
        UPDATE executive_engagements
        SET division_id = (
            SELECT divisions.id FROM divisions
            WHERE divisions.pod_id = executive_engagements.pod_id
              AND divisions.name = executive_engagements.division
        )
        WHERE division_id IS NULL
    """))
    bind.execute(sa.text("""
        UPDATE executive_engagements
        SET business_unit_id = (
            SELECT business_units.id
            FROM business_units
            JOIN divisions ON divisions.id = business_units.division_id
            WHERE divisions.pod_id = executive_engagements.pod_id
              AND divisions.name = executive_engagements.division
              AND business_units.name = executive_engagements.business_unit
        )
        WHERE business_unit_id IS NULL
    """))
    unresolved = bind.execute(sa.text(
        "SELECT COUNT(*) FROM executive_engagements WHERE division_id IS NULL OR business_unit_id IS NULL"
    )).scalar_one()
    if unresolved:
        raise RuntimeError(f"Cannot migrate {unresolved} engagements with unresolved canonical organization scope")

    with op.batch_alter_table("executive_engagements") as batch:
        batch.alter_column("division_id", existing_type=sa.String(160), nullable=False)
        batch.alter_column("business_unit_id", existing_type=sa.String(220), nullable=False)
    with op.batch_alter_table("capco_employees") as batch:
        batch.alter_column("source_system", existing_type=sa.String(80), nullable=False, server_default=None)

    _create_index_if_missing(bind, "uq_capco_employee_source_record", "capco_employees", ["source_system", "source_record_id"], unique=True)

    if bind.dialect.name == "postgresql":
        inspector = sa.inspect(bind)
        existing = {
            foreign_key.get("name")
            for table_name in inspector.get_table_names()
            for foreign_key in inspector.get_foreign_keys(table_name)
        }
        for name, source, target, local, remote in NEW_FOREIGN_KEYS:
            if name not in existing:
                op.create_foreign_key(name, source, target, local, remote, ondelete="RESTRICT")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name, source, *_ in reversed(NEW_FOREIGN_KEYS):
            if name in {item.get("name") for item in sa.inspect(bind).get_foreign_keys(source)}:
                op.drop_constraint(name, source, type_="foreignkey")

    for table in reversed((
        meeting_employees,
        opportunity_employees,
        meeting_opportunities,
        stakeholder_employee_relationships,
        engagement_stakeholders,
        audit_events,
    )):
        table.drop(bind, checkfirst=True)

    columns = {
        "notes": ("author_employee_id", "created_by", "updated_by"),
        "stakeholder_documents": ("owner_employee_id", "created_by", "updated_by"),
        "pod_event_attendees": ("employee_id",),
        "pod_tasks": ("owner_employee_id",),
        "pod_critical_items": ("owner_employee_id",),
        "pod_milestones": ("owner_employee_id",),
        "executive_engagements": ("division_id", "business_unit_id"),
        "capco_employees": ("source_system", "source_record_id", "last_synced_at"),
    }
    for table_name, names in columns.items():
        with op.batch_alter_table(table_name) as batch:
            for name in names:
                if _has_column(bind, table_name, name):
                    batch.drop_column(name)
