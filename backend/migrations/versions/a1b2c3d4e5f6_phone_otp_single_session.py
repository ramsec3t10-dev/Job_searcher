"""Phone OTP registration + single-session enforcement.

Adds users.phone_verified, users.session_version, a unique index on
users.phone, and the phone_otps staging table.

Revision ID: a1b2c3d4e5f6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_verified', sa.Boolean(),
                                     nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('session_version', sa.Integer(),
                                     nullable=False, server_default='0'))
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)

    op.create_table(
        'phone_otps',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.String(length=50), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_phone_otps_phone', 'phone_otps', ['phone'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_phone_otps_phone', table_name='phone_otps')
    op.drop_table('phone_otps')
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_column('users', 'session_version')
    op.drop_column('users', 'phone_verified')
