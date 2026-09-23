"""Add production integrity, financial precision and idempotency records.

Revision ID: 0011_production_hardening
Revises: 0010_resourcing_integrity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

from app.canonical_schema import idempotency_records


revision = "0011_production_hardening"
down_revision = "0010_resourcing_integrity"
branch_labels = None
depends_on = None


CHECKS = (
    ("executive_engagements", "ck_engagement_commercial_value", "commercial_value >= 0"),
    ("executive_engagements", "ck_engagement_revenue_target", "quarterly_revenue_target >= 0"),
    ("executive_engagements", "ck_engagement_dates", "end_date >= start_date"),
    ("executive_engagements", "ck_engagement_health", "health IN ('GREEN', 'AMBER', 'RED')"),
    ("executive_engagements", "ck_engagement_status", "status IN ('Active', 'Planned', 'Completed', 'Cancelled')"),
    ("employee_capacity", "ck_employee_capacity_dates", "period_end >= period_start"),
    ("employee_capacity", "ck_employee_capacity_hours", "available_hours >= 0"),
    ("engagement_assignments", "ck_engagement_assignment_allocation", "allocation_percent > 0 AND allocation_percent <= 100"),
    ("engagement_assignments", "ck_engagement_assignment_dates", "end_date >= start_date"),
    ("engagement_assignments", "ck_engagement_assignment_status", "status IN ('Active', 'Planned', 'Completed', 'Cancelled')"),
    ("revenue_records", "ck_revenue_amount", "amount >= 0"),
    ("resource_requirements", "ck_resource_requirement_priority", "priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')"),
    ("resource_requirements", "ck_resource_requirement_status", "status IN ('DRAFT', 'OPEN', 'SOURCING', 'PARTIALLY_FILLED', 'ON_HOLD', 'FILLED', 'CANCELLED')"),
    ("resourcing_candidates", "ck_candidate_match_score", "match_score IS NULL OR (match_score >= 0 AND match_score <= 100)"),
    ("candidate_offers", "ck_offer_proposed_rate", "proposed_rate IS NULL OR proposed_rate >= 0"),
    ("candidate_offers", "ck_offer_agreed_rate", "agreed_rate IS NULL OR agreed_rate >= 0"),
)


def _constraint_names(inspector, table: str) -> set[str]:
    return {
        item.get("name")
        for item in [*inspector.get_check_constraints(table), *inspector.get_unique_constraints(table), *inspector.get_foreign_keys(table)]
        if item.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    idempotency_records.create(bind, checkfirst=True)
    if bind.dialect.name != "postgresql":
        return

    # Correct only the four known synthetic rows from the original demo seed.
    bind.execute(text("""
        UPDATE engagement_assignments
        SET allocation_percent = 100
        WHERE id IN ('assignment-012', 'assignment-038', 'assignment-063', 'assignment-080')
          AND allocation_percent > 100
    """))
    invalid = bind.execute(text(
        "SELECT id FROM engagement_assignments WHERE allocation_percent <= 0 OR allocation_percent > 100 ORDER BY id"
    )).scalars().all()
    if invalid:
        raise RuntimeError(f"Review invalid engagement allocation rows before migration: {', '.join(invalid)}")

    numeric_columns = (
        ("executive_engagements", "commercial_value", sa.Numeric(14, 2)),
        ("executive_engagements", "quarterly_revenue_target", sa.Numeric(14, 2)),
        ("employee_capacity", "available_hours", sa.Numeric(10, 2)),
        ("engagement_assignments", "allocation_percent", sa.Numeric(5, 2)),
        ("revenue_records", "amount", sa.Numeric(14, 2)),
        ("candidate_offers", "proposed_rate", sa.Numeric(12, 2)),
        ("candidate_offers", "agreed_rate", sa.Numeric(12, 2)),
    )
    for table, column, column_type in numeric_columns:
        op.alter_column(table, column, type_=column_type, postgresql_using=f"round({column}::numeric, 2)")

    inspector = inspect(bind)
    for table, name, condition in CHECKS:
        if name not in _constraint_names(inspector, table):
            op.create_check_constraint(name, table, condition)

    if "fk_capco_employee_manager" not in _constraint_names(inspector, "capco_employees"):
        op.create_foreign_key(
            "fk_capco_employee_manager", "capco_employees", "capco_employees",
            ["manager_employee_id"], ["id"], ondelete="RESTRICT",
        )
    if "uq_employee_skill" not in _constraint_names(inspector, "employee_skills"):
        op.create_unique_constraint("uq_employee_skill", "employee_skills", ["employee_id", "capability"])
    if "uq_employee_capacity_period" not in _constraint_names(inspector, "employee_capacity"):
        op.create_unique_constraint("uq_employee_capacity_period", "employee_capacity", ["employee_id", "period_start", "period_end"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        inspector = inspect(bind)
        for table, name, _condition in reversed(CHECKS):
            if name in _constraint_names(inspector, table):
                op.drop_constraint(name, table, type_="check")
        for table, name, kind in (
            ("employee_capacity", "uq_employee_capacity_period", "unique"),
            ("employee_skills", "uq_employee_skill", "unique"),
            ("capco_employees", "fk_capco_employee_manager", "foreignkey"),
        ):
            if name in _constraint_names(inspector, table):
                op.drop_constraint(name, table, type_=kind)
    idempotency_records.drop(bind, checkfirst=True)
