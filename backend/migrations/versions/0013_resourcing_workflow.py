"""Add role sourcing workflow and canonical candidate stages.

Revision ID: 0013_resourcing_workflow
Revises: 0012_executive_provenance
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_resourcing_workflow"
down_revision = "0012_executive_provenance"
branch_labels = None
depends_on = None


STAGE_MAP = {
    "IDENTIFIED": "RESUME_REVIEW",
    "CAPCO_REVIEW": "RESUME_REVIEW",
    "SUBMITTED_TO_MS": "CAPCO_INTERVIEW",
    "MS_REVIEW": "CAPCO_INTERVIEW",
    "INTERVIEW_SCHEDULED": "MS_INTERVIEW",
    "INTERVIEWING": "MS_INTERVIEW",
}


def upgrade() -> None:
    bind = op.get_bind()
    existing = {item["name"] for item in sa.inspect(bind).get_columns("resource_requirements")}
    columns = (
        sa.Column("resourcing_app_created", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("bench_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bench_outcome", sa.String(40)),
        sa.Column("resourcing_request_submitted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for column in columns:
        if column.name not in existing:
            op.add_column("resource_requirements", column)

    # Existing pipelines are already sourced; untouched empty roles enter the new bench workflow.
    bind.execute(sa.text("""
        UPDATE resource_requirements SET bench_checked = true, bench_outcome = 'EXISTING_PIPELINE'
        WHERE id IN (SELECT DISTINCT resource_requirement_id FROM resourcing_candidates
                     WHERE stage NOT IN ('REJECTED', 'WITHDRAWN'))
    """))
    stage_migrations = list(STAGE_MAP.items()) + [("SELECTED_WITH_ONBOARDING", "ONBOARDING"), ("SELECTED_WITHOUT_ONBOARDING", "OFFER")]
    for old, new in stage_migrations:
        if old == "SELECTED_WITH_ONBOARDING":
            query = "SELECT id FROM resourcing_candidates WHERE stage = 'SELECTED' AND id IN (SELECT candidate_id FROM onboarding_records)"
        elif old == "SELECTED_WITHOUT_ONBOARDING":
            query = "SELECT id FROM resourcing_candidates WHERE stage = 'SELECTED' AND id NOT IN (SELECT candidate_id FROM onboarding_records)"
        else:
            query = "SELECT id FROM resourcing_candidates WHERE stage = :old"
        candidate_ids = bind.execute(sa.text(query), {"old": old} if ":old" in query else {}).scalars().all()
        if not candidate_ids:
            continue
        bind.execute(sa.text("UPDATE candidate_stage_history SET exited_at = COALESCE(exited_at, CURRENT_TIMESTAMP) WHERE candidate_id IN :ids AND exited_at IS NULL").bindparams(sa.bindparam("ids", expanding=True)), {"ids": candidate_ids})
        bind.execute(sa.text("UPDATE resourcing_candidates SET stage = :new, updated_at = CURRENT_TIMESTAMP WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True)), {"new": new, "ids": candidate_ids})
        for candidate_id in candidate_ids:
            bind.execute(sa.text("INSERT INTO candidate_stage_history (id, candidate_id, stage, entered_at, note) VALUES (:id, :candidate_id, :stage, CURRENT_TIMESTAMP, :note)"), {
                "id": f"migration-0013-{candidate_id}", "candidate_id": candidate_id, "stage": new, "note": f"Migrated from legacy stage {old.replace('_WITH_ONBOARDING', '').replace('_WITHOUT_ONBOARDING', '')}",
            })


def downgrade() -> None:
    reverse = {"RESUME_REVIEW": "CAPCO_REVIEW", "CAPCO_INTERVIEW": "MS_REVIEW", "MS_INTERVIEW": "INTERVIEWING", "ONBOARDING": "SELECTED"}
    bind = op.get_bind()
    for current, old in reverse.items():
        bind.execute(sa.text("UPDATE resourcing_candidates SET stage = :old WHERE stage = :current"), {"old": old, "current": current})
    for name in ("resourcing_request_submitted", "bench_outcome", "bench_checked", "resourcing_app_created"):
        op.drop_column("resource_requirements", name)
