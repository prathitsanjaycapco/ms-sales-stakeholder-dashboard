"""Store a country code for resource requirement offices.

Revision ID: 0015_role_office_directory
Revises: 0014_resourcing_trash
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_role_office_directory"
down_revision = "0014_resourcing_trash"
branch_labels = None
depends_on = None


OFFICES = {
    "Charlotte": "US", "New York": "US", "Toronto": "CA", "London": "GB",
    "Frankfurt": "DE", "Hong Kong": "HK", "Mumbai": "IN", "Tokyo": "JP", "Singapore": "SG",
}


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("resource_requirements")}
    if "country_code" not in columns:
        op.add_column("resource_requirements", sa.Column("country_code", sa.String(length=2), nullable=True))
    for office, country in OFFICES.items():
        bind.execute(sa.text("UPDATE resource_requirements SET country_code = :country WHERE location = :office AND country_code IS NULL"), {"office": office, "country": country})


def downgrade() -> None:
    op.drop_column("resource_requirements", "country_code")
