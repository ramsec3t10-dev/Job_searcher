"""usage log engine_tier + latency

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orchestrator_usage_log', sa.Column('engine_tier', sa.String(length=20), nullable=False, server_default=''))
    op.add_column('orchestrator_usage_log', sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0'))
    op.create_index('ix_orchestrator_usage_log_engine_tier', 'orchestrator_usage_log', ['engine_tier'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_orchestrator_usage_log_engine_tier', table_name='orchestrator_usage_log')
    op.drop_column('orchestrator_usage_log', 'latency_ms')
    op.drop_column('orchestrator_usage_log', 'engine_tier')
