"""knowledge graph

Revision ID: b7c8d9e0f1a2
Revises: a6e7f8091a2b
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a6e7f8091a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'skill_nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_skill_node_name'),
    )
    op.create_index('ix_skill_nodes_name', 'skill_nodes', ['name'], unique=True)
    op.create_index('ix_skill_nodes_category', 'skill_nodes', ['category'], unique=False)

    op.create_table(
        'skill_edges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('from_skill_id', sa.String(length=36), nullable=False),
        sa.Column('to_skill_id', sa.String(length=36), nullable=False),
        sa.Column(
            'edge_type',
            sa.Enum('PREREQUISITE_OF', 'REQUIRED_BY', 'COMMONLY_PAIRED_WITH', name='skill_edge_type_enum'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['from_skill_id'], ['skill_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_skill_id'], ['skill_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_skill_id', 'to_skill_id', 'edge_type', name='uq_skill_edge'),
    )
    op.create_index('ix_skill_edges_from_skill_id', 'skill_edges', ['from_skill_id'], unique=False)
    op.create_index('ix_skill_edges_to_skill_id', 'skill_edges', ['to_skill_id'], unique=False)
    op.create_index('ix_skill_edges_edge_type', 'skill_edges', ['edge_type'], unique=False)

    op.create_table(
        'role_requirements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('role_name', sa.String(length=120), nullable=False),
        sa.Column('skill_id', sa.String(length=36), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['skill_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_name', 'skill_id', name='uq_role_skill'),
    )
    op.create_index('ix_role_requirements_role_name', 'role_requirements', ['role_name'], unique=False)
    op.create_index('ix_role_requirements_skill_id', 'role_requirements', ['skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_role_requirements_skill_id', table_name='role_requirements')
    op.drop_index('ix_role_requirements_role_name', table_name='role_requirements')
    op.drop_table('role_requirements')

    op.drop_index('ix_skill_edges_edge_type', table_name='skill_edges')
    op.drop_index('ix_skill_edges_to_skill_id', table_name='skill_edges')
    op.drop_index('ix_skill_edges_from_skill_id', table_name='skill_edges')
    op.drop_table('skill_edges')

    op.drop_index('ix_skill_nodes_category', table_name='skill_nodes')
    op.drop_index('ix_skill_nodes_name', table_name='skill_nodes')
    op.drop_table('skill_nodes')

    sa.Enum(name='skill_edge_type_enum').drop(op.get_bind(), checkfirst=True)
