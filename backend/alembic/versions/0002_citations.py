"""citation verification tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('citation_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('project_issues', sa.JSON(), nullable=False),
        sa.Column('llm_used', sa.Boolean(), nullable=False),
        sa.Column('llm_summary', sa.Text(), nullable=True),
        sa.Column('llm_issues', sa.JSON(), nullable=False),
        sa.Column('llm_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['research_projects.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_citation_runs_project_id'), 'citation_runs',
                    ['project_id'], unique=False)
    op.create_index(op.f('ix_citation_runs_user_id'), 'citation_runs',
                    ['user_id'], unique=False)
    op.create_index(op.f('ix_citation_runs_created_at'), 'citation_runs',
                    ['created_at'], unique=False)
    op.create_table('citation_findings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('raw', sa.String(), nullable=False),
        sa.Column('surname', sa.String(), nullable=False),
        sa.Column('year', sa.String(), nullable=False),
        sa.Column('narrative', sa.Boolean(), nullable=False),
        sa.Column('format_issues', sa.JSON(), nullable=False),
        sa.Column('existence_status', sa.String(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['citation_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_citation_findings_run_id'), 'citation_findings',
                    ['run_id'], unique=False)
    op.create_table('citation_lookups',
        sa.Column('surname_norm', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('surname_norm', 'year'),
    )


def downgrade() -> None:
    op.drop_table('citation_lookups')
    op.drop_index(op.f('ix_citation_findings_run_id'), table_name='citation_findings')
    op.drop_table('citation_findings')
    op.drop_index(op.f('ix_citation_runs_created_at'), table_name='citation_runs')
    op.drop_index(op.f('ix_citation_runs_user_id'), table_name='citation_runs')
    op.drop_index(op.f('ix_citation_runs_project_id'), table_name='citation_runs')
    op.drop_table('citation_runs')
