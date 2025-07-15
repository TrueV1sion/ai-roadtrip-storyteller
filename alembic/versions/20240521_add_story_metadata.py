"""add_story_metadata

Revision ID: 20240521_metadata
Revises: 20240210_initial_migration
Create Date: 2024-05-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240521_metadata'
down_revision = '20240210_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Add metadata and feedback columns to the stories table
    op.add_column('stories', sa.Column('metadata', sa.JSON(), nullable=True))
    op.add_column('stories', sa.Column('feedback', sa.Text(), nullable=True))


def downgrade():
    # Drop the columns that were added
    op.drop_column('stories', 'metadata')
    op.drop_column('stories', 'feedback')