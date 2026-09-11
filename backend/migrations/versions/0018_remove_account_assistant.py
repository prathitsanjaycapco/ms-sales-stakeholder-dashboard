"""Remove legacy account-assistant storage.

Revision ID: 0018_remove_account_assistant
Revises: 0017_pod_heads
"""
from alembic import op


revision = "0018_remove_account_assistant"
down_revision = "0017_pod_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in (
        "assistant_messages",
        "assistant_conversations",
        "assistant_document_chunks",
        "assistant_document_indexes",
    ):
        if bind.dialect.has_table(bind, table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    # This variant intentionally has no account-assistant persistence.
    pass
