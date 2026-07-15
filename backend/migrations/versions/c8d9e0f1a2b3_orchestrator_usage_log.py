"""orchestrator usage log

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'orchestrator_usage_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('task_type', sa.String(length=60), nullable=False),
        sa.Column('engine_used', sa.String(length=80), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False),
        sa.Column('tokens_out', sa.Integer(), nullable=False),
        sa.Column('cost_estimate_usd', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_orchestrator_usage_log_user_id', 'orchestrator_usage_log', ['user_id'], unique=False)
    op.create_index('ix_orchestrator_usage_log_task_type', 'orchestrator_usage_log', ['task_type'], unique=False)
    op.create_index('ix_orchestrator_usage_log_engine_used', 'orchestrator_usage_log', ['engine_used'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_orchestrator_usage_log_engine_used', table_name='orchestrator_usage_log')
    op.drop_index('ix_orchestrator_usage_log_task_type', table_name='orchestrator_usage_log')
    op.drop_index('ix_orchestrator_usage_log_user_id', table_name='orchestrator_usage_log')
    op.drop_table('orchestrator_usage_log')
