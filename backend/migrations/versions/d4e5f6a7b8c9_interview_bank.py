"""curated interview question bank (Phase 7)

Purely additive: one new table, ``interview_questions``, domain- and
subrole-scoped. No existing table or endpoint is touched.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CATEGORY = sa.Enum('technical', 'behavioral', 'case_study', 'system_design',
                    name='interview_question_category_enum')
_DIFFICULTY = sa.Enum('junior', 'mid', 'senior',
                      name='interview_question_difficulty_enum')
_SOURCE = sa.Enum('curated', 'generated', name='interview_question_source_enum')


def upgrade() -> None:
    op.create_table(
        'interview_questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('domain_id', sa.String(length=36), nullable=False),
        sa.Column('subrole_code', sa.String(length=80), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('category', _CATEGORY, nullable=False),
        sa.Column('difficulty', _DIFFICULTY, nullable=False),
        sa.Column('model_answer_guideline', sa.Text(), nullable=True),
        sa.Column('source_type', _SOURCE, nullable=False, server_default='curated'),
        sa.ForeignKeyConstraint(['domain_id'], ['job_domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interview_questions_domain_id', 'interview_questions', ['domain_id'])
    op.create_index('ix_interview_questions_subrole_code', 'interview_questions', ['subrole_code'])
    op.create_index('ix_interview_questions_category', 'interview_questions', ['category'])
    op.create_index('ix_interview_questions_difficulty', 'interview_questions', ['difficulty'])


def downgrade() -> None:
    op.drop_index('ix_interview_questions_difficulty', table_name='interview_questions')
    op.drop_index('ix_interview_questions_category', table_name='interview_questions')
    op.drop_index('ix_interview_questions_subrole_code', table_name='interview_questions')
    op.drop_index('ix_interview_questions_domain_id', table_name='interview_questions')
    op.drop_table('interview_questions')
    _CATEGORY.drop(op.get_bind(), checkfirst=True)
    _DIFFICULTY.drop(op.get_bind(), checkfirst=True)
    _SOURCE.drop(op.get_bind(), checkfirst=True)
