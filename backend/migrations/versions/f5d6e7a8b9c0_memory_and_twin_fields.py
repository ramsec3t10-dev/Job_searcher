"""memory and long-term twin fields

Revision ID: f5d6e7a8b9c0
Revises: e4c5d6f7a8b9
Create Date: 2026-07-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f5d6e7a8b9c0'
down_revision: Union[str, None] = 'e4c5d6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Career Twin: additive long-term memory / goal columns ──────────────
    op.add_column('career_twins', sa.Column('career_goals', sa.JSON(), nullable=True))
    op.add_column('career_twins', sa.Column('learning_style', sa.String(length=30), nullable=True))
    op.add_column('career_twins', sa.Column('interviews_completed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('career_twins', sa.Column('avg_interview_score', sa.Float(), nullable=False, server_default='0'))
    op.add_column('career_twins', sa.Column('weak_interview_topics', sa.JSON(), nullable=True))
    op.add_column('career_twins', sa.Column('skills_learned_this_month', sa.JSON(), nullable=True))
    op.add_column('career_twins', sa.Column('learning_streak_days', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('career_twins', sa.Column('last_active_date', sa.String(length=40), nullable=True))

    # ── Long-term memory store ─────────────────────────────────────────────
    op.create_table(
        'memory_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('memory_type', sa.String(length=30), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('full_content', sa.Text(), nullable=True),
        sa.Column('importance_score', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.String(length=40), nullable=True),
        sa.Column('conversation_id', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memory_entries_user_id'), 'memory_entries', ['user_id'], unique=False)
    op.create_index(op.f('ix_memory_entries_memory_type'), 'memory_entries', ['memory_type'], unique=False)
    op.create_index(op.f('ix_memory_entries_conversation_id'), 'memory_entries', ['conversation_id'], unique=False)

    # ── LLM usage / cost log (Phase 1 model) ───────────────────────────────
    op.create_table(
        'ai_usage_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('task_type', sa.String(length=40), nullable=False),
        sa.Column('model', sa.String(length=80), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0'),
        sa.Column('cached', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_usage_log_user_id'), 'ai_usage_log', ['user_id'], unique=False)

    # ── LLM conversation history (Phase 1 model) ───────────────────────────
    op.create_table(
        'ai_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_conversations_user_id'), 'ai_conversations', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_conversations_conversation_id'), 'ai_conversations', ['conversation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_conversations_conversation_id'), table_name='ai_conversations')
    op.drop_index(op.f('ix_ai_conversations_user_id'), table_name='ai_conversations')
    op.drop_table('ai_conversations')

    op.drop_index(op.f('ix_ai_usage_log_user_id'), table_name='ai_usage_log')
    op.drop_table('ai_usage_log')

    op.drop_index(op.f('ix_memory_entries_conversation_id'), table_name='memory_entries')
    op.drop_index(op.f('ix_memory_entries_memory_type'), table_name='memory_entries')
    op.drop_index(op.f('ix_memory_entries_user_id'), table_name='memory_entries')
    op.drop_table('memory_entries')

    for col in (
        'last_active_date', 'learning_streak_days', 'skills_learned_this_month',
        'weak_interview_topics', 'avg_interview_score', 'interviews_completed',
        'learning_style', 'career_goals',
    ):
        op.drop_column('career_twins', col)
