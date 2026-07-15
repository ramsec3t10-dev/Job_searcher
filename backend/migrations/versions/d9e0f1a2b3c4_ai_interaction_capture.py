"""ai interaction capture + usage telemetry

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 5 telemetry on the lean usage log.
    op.add_column('orchestrator_usage_log', sa.Column('escalated', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('orchestrator_usage_log', sa.Column('confidence', sa.Float(), nullable=True))

    # Training-capture table (full IO pairs + consent + quality/outcome labels).
    op.create_table(
        'ai_interaction',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('task_type', sa.String(length=60), nullable=False),
        sa.Column('engine_used', sa.String(length=80), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('system', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('cost_estimate_usd', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False),
        sa.Column('consented', sa.Boolean(), nullable=False),
        sa.Column('pii_scrubbed', sa.Boolean(), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=True),
        sa.Column('edited', sa.Boolean(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('outcome', sa.String(length=40), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_interaction_user_id', 'ai_interaction', ['user_id'], unique=False)
    op.create_index('ix_ai_interaction_task_type', 'ai_interaction', ['task_type'], unique=False)
    op.create_index('ix_ai_interaction_engine_used', 'ai_interaction', ['engine_used'], unique=False)
    op.create_index('ix_ai_interaction_role', 'ai_interaction', ['role'], unique=False)
    op.create_index('ix_ai_interaction_parent_id', 'ai_interaction', ['parent_id'], unique=False)
    op.create_index('ix_ai_interaction_outcome', 'ai_interaction', ['outcome'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ai_interaction_outcome', table_name='ai_interaction')
    op.drop_index('ix_ai_interaction_parent_id', table_name='ai_interaction')
    op.drop_index('ix_ai_interaction_role', table_name='ai_interaction')
    op.drop_index('ix_ai_interaction_engine_used', table_name='ai_interaction')
    op.drop_index('ix_ai_interaction_task_type', table_name='ai_interaction')
    op.drop_index('ix_ai_interaction_user_id', table_name='ai_interaction')
    op.drop_table('ai_interaction')

    op.drop_column('orchestrator_usage_log', 'confidence')
    op.drop_column('orchestrator_usage_log', 'escalated')
