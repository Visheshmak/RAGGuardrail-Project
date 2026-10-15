"""Add dataset and evaluation case models

Revision ID: 003
Revises: 002
Create Date: 2026-09-26 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'datasets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasets_id'), 'datasets', ['id'], unique=False)
    op.create_index(op.f('ix_datasets_project_id'), 'datasets', ['project_id'], unique=False)
    op.create_index(op.f('ix_datasets_name'), 'datasets', ['name'], unique=False)

    op.create_table(
        'dataset_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('dataset_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('case_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_versions_id'), 'dataset_versions', ['id'], unique=False)
    op.create_index(op.f('ix_dataset_versions_dataset_id'), 'dataset_versions', ['dataset_id'], unique=False)

    op.create_table(
        'evaluation_cases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('dataset_version_id', sa.Uuid(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('expected_context', sa.JSON(), nullable=True),
        sa.Column('category', sa.String(), nullable=False, server_default='general'),
        sa.Column('difficulty', sa.String(), nullable=False, server_default='medium'),
        sa.Column('case_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_version_id'], ['dataset_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_cases_id'), 'evaluation_cases', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_dataset_version_id'), 'evaluation_cases', ['dataset_version_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_evaluation_cases_dataset_version_id'), table_name='evaluation_cases')
    op.drop_index(op.f('ix_evaluation_cases_id'), table_name='evaluation_cases')
    op.drop_table('evaluation_cases')

    op.drop_index(op.f('ix_dataset_versions_dataset_id'), table_name='dataset_versions')
    op.drop_index(op.f('ix_dataset_versions_id'), table_name='dataset_versions')
    op.drop_table('dataset_versions')

    op.drop_index(op.f('ix_datasets_name'), table_name='datasets')
    op.drop_index(op.f('ix_datasets_project_id'), table_name='datasets')
    op.drop_index(op.f('ix_datasets_id'), table_name='datasets')
    op.drop_table('datasets')
