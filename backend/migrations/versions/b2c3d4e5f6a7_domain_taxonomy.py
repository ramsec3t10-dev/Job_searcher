"""domain taxonomy + multi-domain columns (Phase 1)

Additive only. Creates the domain taxonomy tables, seeds all domains plus the
embedded skill categories, adds domain columns to candidate_profiles and
discovered_jobs, and backfills every existing row to embedded_engineering —
copying the embedded-specific score into domain_profile_data so the future
embedded plugin has a data source while old code keeps reading the original
columns unchanged.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.domains.catalog import (
    DEFAULT_DOMAIN_CODE, DOMAINS, EMBEDDED_CATEGORIES,
    domain_id, skill_category_id,
)

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Taxonomy tables ──────────────────────────────────────────────
    op.create_table(
        'job_domains',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('code', sa.String(length=60), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_domains_code', 'job_domains', ['code'], unique=True)

    op.create_table(
        'skill_categories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('domain_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=60), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False, server_default='10'),
        sa.ForeignKeyConstraint(['domain_id'], ['job_domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_categories_domain_id', 'skill_categories', ['domain_id'], unique=False)
    op.create_index('ix_skill_categories_code', 'skill_categories', ['code'], unique=False)

    op.create_table(
        'skills',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('category_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['skill_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skills_category_id', 'skills', ['category_id'], unique=False)
    op.create_index('ix_skills_name', 'skills', ['name'], unique=False)

    # ── 2. Additive columns on existing tables ──────────────────────────
    op.add_column('candidate_profiles',
                  sa.Column('primary_domain_id', sa.String(length=36), nullable=True))
    op.add_column('candidate_profiles',
                  sa.Column('secondary_domain_ids', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('candidate_profiles',
                  sa.Column('domain_profile_data', sa.JSON(), nullable=False, server_default='{}'))
    op.create_index('ix_candidate_profiles_primary_domain_id', 'candidate_profiles',
                    ['primary_domain_id'], unique=False)

    op.add_column('discovered_jobs',
                  sa.Column('domain_id', sa.String(length=36), nullable=True))
    op.create_index('ix_discovered_jobs_domain_id', 'discovered_jobs', ['domain_id'], unique=False)

    # ── 3. Seed domains + embedded skill categories ─────────────────────
    conn = op.get_bind()
    domains_t = sa.table(
        'job_domains',
        sa.column('id', sa.String), sa.column('code', sa.String),
        sa.column('name', sa.String), sa.column('description', sa.Text),
        sa.column('is_active', sa.Boolean),
    )
    op.bulk_insert(domains_t, [
        {'id': domain_id(code), 'code': code, 'name': name,
         'description': desc, 'is_active': True}
        for code, name, desc in DOMAINS
    ])

    cats_t = sa.table(
        'skill_categories',
        sa.column('id', sa.String), sa.column('domain_id', sa.String),
        sa.column('code', sa.String), sa.column('name', sa.String),
        sa.column('weight', sa.Integer),
    )
    emb_id = domain_id(DEFAULT_DOMAIN_CODE)
    op.bulk_insert(cats_t, [
        {'id': skill_category_id(DEFAULT_DOMAIN_CODE, code),
         'domain_id': emb_id, 'code': code, 'name': name, 'weight': weight}
        for code, name, weight in EMBEDDED_CATEGORIES
    ])

    # ── 4. Backfill existing rows to embedded_engineering ───────────────
    conn.execute(
        sa.text("UPDATE discovered_jobs SET domain_id = :d WHERE domain_id IS NULL"),
        {"d": emb_id},
    )
    conn.execute(
        sa.text("UPDATE candidate_profiles SET primary_domain_id = :d "
                "WHERE primary_domain_id IS NULL"),
        {"d": emb_id},
    )

    # Copy embedded_domain_score into domain_profile_data.embedded_engineering
    # per row (JSON-typed reflection serialises correctly on both SQLite/PG).
    profiles_t = sa.table(
        'candidate_profiles',
        sa.column('id', sa.String),
        sa.column('embedded_domain_score', sa.Integer),
        sa.column('domain_profile_data', sa.JSON),
    )
    rows = conn.execute(
        sa.select(profiles_t.c.id, profiles_t.c.embedded_domain_score)
    ).fetchall()
    for row in rows:
        conn.execute(
            profiles_t.update()
            .where(profiles_t.c.id == row.id)
            .values(domain_profile_data={
                "embedded_engineering": {
                    "embedded_domain_score": int(row.embedded_domain_score or 0),
                }
            })
        )


def downgrade() -> None:
    op.drop_index('ix_discovered_jobs_domain_id', table_name='discovered_jobs')
    op.drop_column('discovered_jobs', 'domain_id')

    op.drop_index('ix_candidate_profiles_primary_domain_id', table_name='candidate_profiles')
    op.drop_column('candidate_profiles', 'domain_profile_data')
    op.drop_column('candidate_profiles', 'secondary_domain_ids')
    op.drop_column('candidate_profiles', 'primary_domain_id')

    op.drop_index('ix_skills_name', table_name='skills')
    op.drop_index('ix_skills_category_id', table_name='skills')
    op.drop_table('skills')
    op.drop_index('ix_skill_categories_code', table_name='skill_categories')
    op.drop_index('ix_skill_categories_domain_id', table_name='skill_categories')
    op.drop_table('skill_categories')
    op.drop_index('ix_job_domains_code', table_name='job_domains')
    op.drop_table('job_domains')
