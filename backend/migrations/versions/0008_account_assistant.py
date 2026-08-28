"""Add grounded account assistant retrieval and conversation storage.

Revision ID: 0008_account_assistant
Revises: 0007_weekly_executive_people
"""
from __future__ import annotations

from alembic import op

from backend.canonical_schema import (
    assistant_conversations,
    assistant_document_chunks,
    assistant_document_indexes,
    assistant_messages,
)


revision = "0008_account_assistant"
down_revision = "0007_weekly_executive_people"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        assistant_document_indexes,
        assistant_document_chunks,
        assistant_conversations,
        assistant_messages,
    ):
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        assistant_messages,
        assistant_conversations,
        assistant_document_chunks,
        assistant_document_indexes,
    ):
        table.drop(bind, checkfirst=True)
