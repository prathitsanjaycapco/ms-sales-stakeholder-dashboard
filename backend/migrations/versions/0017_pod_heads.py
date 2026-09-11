"""Add governed pod heads and complete stakeholder reporting lines.

Revision ID: 0017_pod_heads
Revises: 0016_bench_outcome_check
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_pod_heads"
down_revision = "0016_bench_outcome_check"
branch_labels = None
depends_on = None


POD_HEADS = {
    "ISG": ("isg-pod-head", "Dan Simkowitz", "Co-President; responsible for Institutional Securities Group"),
    "Wealth Management": ("wealth-management-pod-head", "Jed Finn", "Head of Wealth Management"),
    "MSIM": ("msim-pod-head", "Ben Huneke", "Head of Morgan Stanley Investment Management"),
}


def _tables(bind):
    metadata = sa.MetaData()
    return {
        name: sa.Table(name, metadata, autoload_with=bind)
        for name in ("pods", "divisions", "business_units", "stakeholders", "stakeholder_assignments", "enterprise_functions")
    }


def upgrade() -> None:
    bind = op.get_bind()
    pod_columns = {column["name"] for column in sa.inspect(bind).get_columns("pods")}
    if "head_stakeholder_id" not in pod_columns:
        with op.batch_alter_table("pods") as batch:
            batch.add_column(sa.Column("head_stakeholder_id", sa.String(length=180), nullable=True))
            batch.create_foreign_key("fk_pod_head", "stakeholders", ["head_stakeholder_id"], ["id"], ondelete="RESTRICT")
    assignment_columns = {column["name"]: column for column in sa.inspect(bind).get_columns("stakeholder_assignments")}
    if not assignment_columns["division_id"]["nullable"]:
        with op.batch_alter_table("stakeholder_assignments") as batch:
            batch.alter_column("division_id", existing_type=sa.String(length=160), nullable=True)

    tables = _tables(bind)
    pods, divisions, units = tables["pods"], tables["divisions"], tables["business_units"]
    stakeholders, assignments, enterprise = tables["stakeholders"], tables["stakeholder_assignments"], tables["enterprise_functions"]
    pod_rows = {row["name"]: dict(row) for row in bind.execute(sa.select(pods)).mappings()}
    for pod_name, (stakeholder_id, name, title) in POD_HEADS.items():
        pod = pod_rows.get(pod_name)
        if not pod:
            continue
        if bind.execute(sa.select(stakeholders.c.id).where(stakeholders.c.id == stakeholder_id)).scalar_one_or_none() is None:
            bind.execute(stakeholders.insert().values(
                id=stakeholder_id, name=name, title=title, level="Executive Leadership",
                location="Not recorded", country_code="", biography="",
                source_system="hierarchy_migration", source_record_id=f"pod-head:{pod['id']}",
            ))
        current = bind.execute(sa.select(assignments.c.id).where(
            assignments.c.stakeholder_id == stakeholder_id, assignments.c.is_current.is_(True),
        )).scalar_one_or_none()
        if current is None:
            bind.execute(assignments.insert().values(
                id=f"assignment-{stakeholder_id}", stakeholder_id=stakeholder_id, pod_id=pod["id"],
                division_id=None, business_unit_id=None, team_type="Business", organizational_role="Pod Head",
                manager_stakeholder_id=None, is_primary_technology=False, is_buyer=True, is_influencer=True,
                is_budget_holder=True, relationship_strength="Strong", capco_contingents=0,
                tags=[pod_name, "Executive Leadership"], effective_from=sa.func.current_date(), is_current=True,
            ))
        bind.execute(pods.update().where(pods.c.id == pod["id"]).values(head_stakeholder_id=stakeholder_id))

    pod_rows = {row["id"]: dict(row) for row in bind.execute(sa.select(pods)).mappings()}
    division_rows = {row["id"]: dict(row) for row in bind.execute(sa.select(divisions)).mappings()}
    unit_rows = {row["id"]: dict(row) for row in bind.execute(sa.select(units)).mappings()}
    enterprise_lead_by_unit = {row["id"]: row["lead_stakeholder_id"] for row in bind.execute(sa.select(enterprise)).mappings()}
    current_rows = [dict(row) for row in bind.execute(sa.select(assignments).where(assignments.c.is_current.is_(True))).mappings()]
    assignment_by_person = {row["stakeholder_id"]: row for row in current_rows}
    division_head_ids = {row["head_stakeholder_id"] for row in division_rows.values() if row.get("head_stakeholder_id")}
    division_head_by_division = {row["id"]: row["head_stakeholder_id"] for row in division_rows.values()}
    business_head_by_unit = {
        row["business_unit_id"]: row["stakeholder_id"]
        for row in current_rows
        if row["business_unit_id"] and row["organizational_role"] == "Business Unit Head"
    }
    primary_technology_by_unit = {
        row["business_unit_id"]: row["stakeholder_id"]
        for row in current_rows
        if row["business_unit_id"] and row["is_primary_technology"]
    }

    for row in current_rows:
        stakeholder_id = row["stakeholder_id"]
        pod_head_id = pod_rows[row["pod_id"]].get("head_stakeholder_id")
        unit = unit_rows.get(row["business_unit_id"])
        division = division_rows.get(row["division_id"])
        manager_id = row["manager_stakeholder_id"]
        values = {}
        if row["organizational_role"] == "Pod Head":
            values = {"manager_stakeholder_id": None, "division_id": None, "business_unit_id": None}
        elif stakeholder_id in division_head_ids:
            values = {"manager_stakeholder_id": pod_head_id, "organizational_role": "Division Head"}
        elif row["organizational_role"] == "Business Unit Head" and unit:
            values = {"manager_stakeholder_id": division_head_by_division.get(unit["division_id"])}
        elif row["is_primary_technology"] and unit:
            values = {"manager_stakeholder_id": business_head_by_unit.get(unit["id"])}
        elif row["business_unit_id"] in enterprise_lead_by_unit:
            lead_id = enterprise_lead_by_unit[row["business_unit_id"]]
            values = {"manager_stakeholder_id": pod_head_id if stakeholder_id == lead_id else lead_id}
        elif manager_id is None and unit:
            values = {"manager_stakeholder_id": (
                primary_technology_by_unit.get(unit["id"]) if row["team_type"] == "Technology" else business_head_by_unit.get(unit["id"])
            ) or pod_head_id}
        elif manager_id is None:
            values = {"manager_stakeholder_id": pod_head_id}
        if values:
            bind.execute(assignments.update().where(assignments.c.id == row["id"]).values(**values))

    # Repair saved links that point outside the pod or participate in a cycle.
    repaired_rows = [dict(row) for row in bind.execute(sa.select(assignments).where(assignments.c.is_current.is_(True))).mappings()]
    repaired_by_person = {row["stakeholder_id"]: row for row in repaired_rows}

    def fallback_manager(row):
        unit = unit_rows.get(row["business_unit_id"])
        if row["organizational_role"] == "Division Head":
            return pod_rows[row["pod_id"]].get("head_stakeholder_id")
        if row["organizational_role"] == "Business Unit Head" and unit:
            return division_head_by_division.get(unit["division_id"])
        if row["business_unit_id"] in enterprise_lead_by_unit:
            lead_id = enterprise_lead_by_unit[row["business_unit_id"]]
            return pod_rows[row["pod_id"]].get("head_stakeholder_id") if row["stakeholder_id"] == lead_id else lead_id
        if unit:
            return primary_technology_by_unit.get(unit["id"]) if row["team_type"] == "Technology" and not row["is_primary_technology"] else business_head_by_unit.get(unit["id"])
        return pod_rows[row["pod_id"]].get("head_stakeholder_id")

    for row in repaired_rows:
        if row["organizational_role"] == "Pod Head":
            continue
        manager_id = row["manager_stakeholder_id"]
        manager = repaired_by_person.get(manager_id)
        invalid = manager is None or manager["pod_id"] != row["pod_id"] or manager_id == row["stakeholder_id"]
        cursor_id = manager_id
        seen = {row["stakeholder_id"]}
        while not invalid and cursor_id:
            if cursor_id in seen:
                invalid = True
                break
            seen.add(cursor_id)
            cursor = repaired_by_person.get(cursor_id)
            cursor_id = cursor["manager_stakeholder_id"] if cursor else None
        if invalid:
            bind.execute(assignments.update().where(assignments.c.id == row["id"]).values(manager_stakeholder_id=fallback_manager(row)))

    existing_checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("stakeholder_assignments")}
    with op.batch_alter_table("stakeholder_assignments") as batch:
        if "ck_assignment_division_scope" not in existing_checks:
            batch.create_check_constraint("ck_assignment_division_scope", "organizational_role = 'Pod Head' OR division_id IS NOT NULL")
        if "ck_assignment_manager_required" not in existing_checks:
            batch.create_check_constraint("ck_assignment_manager_required", "manager_stakeholder_id IS NOT NULL OR organizational_role = 'Pod Head'")
        if "ck_assignment_pod_head_scope" not in existing_checks:
            batch.create_check_constraint("ck_assignment_pod_head_scope", "organizational_role != 'Pod Head' OR (division_id IS NULL AND business_unit_id IS NULL AND manager_stakeholder_id IS NULL)")


def downgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)
    pods, assignments, stakeholders = tables["pods"], tables["stakeholder_assignments"], tables["stakeholders"]
    head_ids = [item[0] for item in POD_HEADS.values()]
    with op.batch_alter_table("stakeholder_assignments") as batch:
        batch.drop_constraint("ck_assignment_pod_head_scope", type_="check")
        batch.drop_constraint("ck_assignment_manager_required", type_="check")
        batch.drop_constraint("ck_assignment_division_scope", type_="check")
    bind.execute(pods.update().values(head_stakeholder_id=None))
    bind.execute(assignments.update().where(assignments.c.manager_stakeholder_id.in_(head_ids)).values(manager_stakeholder_id=None))
    bind.execute(assignments.delete().where(assignments.c.stakeholder_id.in_(head_ids)))
    bind.execute(stakeholders.delete().where(stakeholders.c.id.in_(head_ids)))
    with op.batch_alter_table("stakeholder_assignments") as batch:
        batch.alter_column("division_id", existing_type=sa.String(length=160), nullable=False)
    with op.batch_alter_table("pods") as batch:
        batch.drop_constraint("fk_pod_head", type_="foreignkey")
        batch.drop_column("head_stakeholder_id")
