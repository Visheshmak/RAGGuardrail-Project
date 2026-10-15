"""Add evaluation, baseline, regression result, and threshold models

Revision ID: 005
Revises: 004
Create Date: 2026-10-09 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. evaluation_runs
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('dataset_version_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('total_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('guardrail_summary', sa.JSON(), nullable=False),
        sa.Column('configuration_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_version_id'], ['dataset_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_runs_id'), 'evaluation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_project_id'), 'evaluation_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_dataset_version_id'), 'evaluation_runs', ['dataset_version_id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_name'), 'evaluation_runs', ['name'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_status'), 'evaluation_runs', ['status'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_created_at'), 'evaluation_runs', ['created_at'], unique=False)

    # 2. evaluation_case_results
    op.create_table(
        'evaluation_case_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_run_id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_case_id', sa.Uuid(), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('expected_answer', sa.Text(), nullable=True),
        sa.Column('actual_answer', sa.Text(), nullable=True),
        sa.Column('retrieved_chunks', sa.JSON(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('guardrail_results', sa.JSON(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluation_case_id'], ['evaluation_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_case_results_id'), 'evaluation_case_results', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_case_results_evaluation_run_id'), 'evaluation_case_results', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_case_results_evaluation_case_id'), 'evaluation_case_results', ['evaluation_case_id'], unique=False)

    # 3. baselines
    op.create_table(
        'baselines',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_run_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('configuration_snapshot', sa.JSON(), nullable=False),
        sa.Column('metrics_snapshot', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baselines_id'), 'baselines', ['id'], unique=False)
    op.create_index(op.f('ix_baselines_project_id'), 'baselines', ['project_id'], unique=False)
    op.create_index(op.f('ix_baselines_evaluation_run_id'), 'baselines', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_baselines_is_active'), 'baselines', ['is_active'], unique=False)
    op.create_index(op.f('ix_baselines_created_at'), 'baselines', ['created_at'], unique=False)

    # 4. regression_results
    op.create_table(
        'regression_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_run_id', sa.Uuid(), nullable=False),
        sa.Column('baseline_id', sa.Uuid(), nullable=True),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column('baseline_score', sa.Float(), nullable=False),
        sa.Column('current_score', sa.Float(), nullable=False),
        sa.Column('absolute_difference', sa.Float(), nullable=False),
        sa.Column('relative_difference', sa.Float(), nullable=False),
        sa.Column('allowed_regression', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['baseline_id'], ['baselines.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_regression_results_id'), 'regression_results', ['id'], unique=False)
    op.create_index(op.f('ix_regression_results_evaluation_run_id'), 'regression_results', ['evaluation_run_id'], unique=False)
    op.create_index(op.f('ix_regression_results_baseline_id'), 'regression_results', ['baseline_id'], unique=False)
    op.create_index(op.f('ix_regression_results_metric'), 'regression_results', ['metric'], unique=False)
    op.create_index(op.f('ix_regression_results_status'), 'regression_results', ['status'], unique=False)

    # 5. project_threshold_configs
    op.create_table(
        'project_threshold_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('thresholds', sa.JSON(), nullable=False),
        sa.Column('block_on_critical_guardrail', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index(op.f('ix_project_threshold_configs_id'), 'project_threshold_configs', ['id'], unique=False)
    op.create_index(op.f('ix_project_threshold_configs_project_id'), 'project_threshold_configs', ['project_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_threshold_configs_project_id'), table_name='project_threshold_configs')
    op.drop_index(op.f('ix_project_threshold_configs_id'), table_name='project_threshold_configs')
    op.drop_table('project_threshold_configs')

    op.drop_index(op.f('ix_regression_results_status'), table_name='regression_results')
    op.drop_index(op.f('ix_regression_results_metric'), table_name='regression_results')
    op.drop_index(op.f('ix_regression_results_baseline_id'), table_name='regression_results')
    op.drop_index(op.f('ix_regression_results_evaluation_run_id'), table_name='regression_results')
    op.drop_index(op.f('ix_regression_results_id'), table_name='regression_results')
    op.drop_table('regression_results')

    op.drop_index(op.f('ix_baselines_created_at'), table_name='baselines')
    op.drop_index(op.f('ix_baselines_is_active'), table_name='baselines')
    op.drop_index(op.f('ix_baselines_evaluation_run_id'), table_name='baselines')
    op.drop_index(op.f('ix_baselines_project_id'), table_name='baselines')
    op.drop_index(op.f('ix_baselines_id'), table_name='baselines')
    op.drop_table('baselines')

    op.drop_index(op.f('ix_evaluation_case_results_evaluation_case_id'), table_name='evaluation_case_results')
    op.drop_index(op.f('ix_evaluation_case_results_evaluation_run_id'), table_name='evaluation_case_results')
    op.drop_index(op.f('ix_evaluation_case_results_id'), table_name='evaluation_case_results')
    op.drop_table('evaluation_case_results')

    op.drop_index(op.f('ix_evaluation_runs_created_at'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_status'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_name'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_dataset_version_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_project_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_id'), table_name='evaluation_runs')
    op.drop_table('evaluation_runs')
