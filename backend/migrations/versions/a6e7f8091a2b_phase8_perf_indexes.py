"""phase 8 performance indexes

Adds composite indexes for the hottest AI query paths: memory retrieval,
usage/cost aggregation and conversation history lookups. The single-column
``career_twins.user_id`` index already exists (unique) from the career_twin
migration, so it is only verified here, not recreated.

Revision ID: a6e7f8091a2b
Revises: f5d6e7a8b9c0
Create Date: 2026-07-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a6e7f8091a2b'
down_revision: Union[str, None] = 'f5d6e7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # memory_entries: relevance retrieval by user + type ordered by recency.
    op.create_index(
        'ix_memory_entries_user_type_created',
        'memory_entries',
        ['user_id', 'memory_type', 'created_at'],
        unique=False,
    )
    # memory_entries: expiry sweep (weekly cleanup task).
    op.create_index(
        'ix_memory_entries_user_expires',
        'memory_entries',
        ['user_id', 'expires_at'],
        unique=False,
    )
    # ai_usage_log: per-user cost/usage aggregation over a time window.
    op.create_index(
        'ix_ai_usage_log_user_created',
        'ai_usage_log',
        ['user_id', 'created_at'],
        unique=False,
    )
    # ai_conversations: history fetch for one conversation, oldest-first.
    op.create_index(
        'ix_ai_conversations_user_conv_created',
        'ai_conversations',
        ['user_id', 'conversation_id', 'created_at'],
        unique=False,
    )
    # career_twins.user_id index already exists (unique) — nothing to add.


def downgrade() -> None:
    op.drop_index('ix_ai_conversations_user_conv_created', table_name='ai_conversations')
    op.drop_index('ix_ai_usage_log_user_created', table_name='ai_usage_log')
    op.drop_index('ix_memory_entries_user_expires', table_name='memory_entries')
    op.drop_index('ix_memory_entries_user_type_created', table_name='memory_entries')
