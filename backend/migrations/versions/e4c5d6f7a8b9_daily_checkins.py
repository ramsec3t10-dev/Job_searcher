"""daily checkins

Revision ID: e4c5d6f7a8b9
Revises: d3b4c5e6f7a8
Create Date: 2026-07-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4c5d6f7a8b9'
down_revision: Union[str, None] = 'd3b4c5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'daily_checkins',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('checkin_date', sa.String(length=10), nullable=False),
        sa.Column('tasks_completed', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_daily_checkins_user_id', 'daily_checkins', ['user_id'], unique=False)
    op.create_index('ix_daily_checkins_checkin_date', 'daily_checkins', ['checkin_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_daily_checkins_checkin_date', table_name='daily_checkins')
    op.drop_index('ix_daily_checkins_user_id', table_name='daily_checkins')
    op.drop_table('daily_checkins')
