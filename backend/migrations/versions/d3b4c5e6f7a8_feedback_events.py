"""feedback events

Revision ID: d3b4c5e6f7a8
Revises: c2a3b4d5e6f7
Create Date: 2026-07-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3b4c5e6f7a8'
down_revision: Union[str, None] = 'c2a3b4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=200), nullable=True),
        sa.Column('feedback_type', sa.String(length=30), nullable=False),
        sa.Column('signal', sa.Float(), nullable=True),
        sa.Column('company', sa.String(length=200), nullable=True),
        sa.Column('company_tier', sa.String(length=50), nullable=True),
        sa.Column('skills', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feedback_events_user_id', 'feedback_events', ['user_id'], unique=False)
    op.create_index('ix_feedback_events_job_id', 'feedback_events', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_feedback_events_job_id', table_name='feedback_events')
    op.drop_index('ix_feedback_events_user_id', table_name='feedback_events')
    op.drop_table('feedback_events')
