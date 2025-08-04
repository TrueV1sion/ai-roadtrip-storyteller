"""Add progress tracking models (Task table)

Revision ID: 20250130_progress_tracking
Revises: 20250711_api_keys_table
Create Date: 2025-01-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250130_progress_tracking'
down_revision = '002_journey_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tasks table for progress tracking."""
    # Check if tasks table already exists (from 002 migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'tasks' not in tables:
        op.create_table(
            'tasks',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('project_id', sa.String(), nullable=False),
            sa.Column('assignee_id', sa.String(), nullable=True),
            sa.Column('team_id', sa.String(), nullable=True),
            sa.Column('priority', sa.String(), nullable=True, server_default='medium'),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.Column('estimated_hours', sa.Float(), nullable=True),
            sa.Column('status', sa.String(), nullable=True, server_default='todo'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
        op.create_index(op.f('ix_tasks_project_id'), 'tasks', ['project_id'], unique=False)
        op.create_index(op.f('ix_tasks_assignee_id'), 'tasks', ['assignee_id'], unique=False)
        op.create_index(op.f('ix_tasks_team_id'), 'tasks', ['team_id'], unique=False)
        op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)


def downgrade() -> None:
    """Drop tasks table."""
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_team_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_assignee_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_project_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    op.drop_table('tasks')