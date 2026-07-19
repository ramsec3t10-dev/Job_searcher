"""domain hierarchy + job industry (Phase 2)

Additive. Adds parent_id/level/keywords to job_domains (self-referential tree)
and industry to discovered_jobs, then transforms the flat Phase-1 domains into
the full hierarchical TAXONOMY (upsert by id; embedded_engineering keeps its id
and skill categories, gaining IT as parent). Obsolete, unreferenced Phase-1-only
codes are removed so the live set matches the catalog exactly.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.domains.catalog import OBSOLETE_DOMAIN_CODES, domain_id, flatten

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('job_domains', sa.Column('parent_id', sa.String(length=36), nullable=True))
    op.add_column('job_domains', sa.Column('level', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('job_domains', sa.Column('keywords', sa.JSON(), nullable=False, server_default='[]'))
    op.create_index('ix_job_domains_parent_id', 'job_domains', ['parent_id'], unique=False)

    op.add_column('discovered_jobs', sa.Column('industry', sa.String(length=120), nullable=True))

    domains_t = sa.table(
        'job_domains',
        sa.column('id', sa.String), sa.column('code', sa.String),
        sa.column('name', sa.String), sa.column('description', sa.Text),
        sa.column('is_active', sa.Boolean), sa.column('parent_id', sa.String),
        sa.column('level', sa.Integer), sa.column('keywords', sa.JSON),
    )
    conn = op.get_bind()
    existing = {r.id for r in conn.execute(sa.select(domains_t.c.id)).fetchall()}

    # Insert level 0 before children so parent rows exist (flatten is DFS: a
    # parent always precedes its descendants).
    for d in flatten():
        values = dict(code=d.code, name=d.name, description=d.description,
                      is_active=True, parent_id=d.parent_id, level=d.level,
                      keywords=d.keywords)
        if d.id in existing:
            conn.execute(domains_t.update().where(domains_t.c.id == d.id).values(**values))
        else:
            conn.execute(domains_t.insert().values(id=d.id, **values))

    # Remove obsolete, unreferenced Phase-1-only domains.
    for code in OBSOLETE_DOMAIN_CODES:
        conn.execute(domains_t.delete().where(domains_t.c.id == domain_id(code)))


def downgrade() -> None:
    op.drop_column('discovered_jobs', 'industry')
    op.drop_index('ix_job_domains_parent_id', table_name='job_domains')
    op.drop_column('job_domains', 'keywords')
    op.drop_column('job_domains', 'level')
    op.drop_column('job_domains', 'parent_id')
