"""Add guardrail config and execution log models

Revision ID: 004
Revises: 003
Create Date: 2026-10-09 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_guardrail_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('guardrail_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('target', sa.String(), nullable=False, server_default='both'),
        sa.Column('severity_override', sa.String(), nullable=True),
        sa.Column('action_override', sa.String(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_guardrail_configs_id'), 'project_guardrail_configs', ['id'], unique=False)
    op.create_index(op.f('ix_project_guardrail_configs_project_id'), 'project_guardrail_configs', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_guardrail_configs_guardrail_type'), 'project_guardrail_configs', ['guardrail_type'], unique=False)

    op.create_table(
        'guardrail_execution_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_case_id', sa.Uuid(), nullable=True),
        sa.Column('guardrail_name', sa.String(), nullable=False),
        sa.Column('target', sa.String(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('action_taken', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('execution_metadata', sa.JSON(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluation_case_id'], ['evaluation_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guardrail_execution_logs_id'), 'guardrail_execution_logs', ['id'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_project_id'), 'guardrail_execution_logs', ['project_id'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_evaluation_case_id'), 'guardrail_execution_logs', ['evaluation_case_id'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_guardrail_name'), 'guardrail_execution_logs', ['guardrail_name'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_passed'), 'guardrail_execution_logs', ['passed'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_severity'), 'guardrail_execution_logs', ['severity'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_action_taken'), 'guardrail_execution_logs', ['action_taken'], unique=False)
    op.create_index(op.f('ix_guardrail_execution_logs_created_at'), 'guardrail_execution_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_guardrail_execution_logs_created_at'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_action_taken'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_severity'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_passed'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_guardrail_name'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_evaluation_case_id'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_project_id'), table_name='guardrail_execution_logs')
    op.drop_index(op.f('ix_guardrail_execution_logs_id'), table_name='guardrail_execution_logs')
    op.drop_table('guardrail_execution_logs')

    op.drop_index(op.f('ix_project_guardrail_configs_guardrail_type'), table_name='project_guardrail_configs')
    op.drop_index(op.f('ix_project_guardrail_configs_project_id'), table_name='project_guardrail_configs')
    op.drop_index(op.f('ix_project_guardrail_configs_id'), table_name='project_guardrail_configs')
    op.drop_table('project_guardrail_configs')
