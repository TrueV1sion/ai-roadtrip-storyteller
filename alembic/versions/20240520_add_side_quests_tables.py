"""Add side quests tables

Revision ID: 20240520c
Revises: 20240520b
Create Date: 2024-05-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240520c'
down_revision = '20240520b'
branch_labels = None
depends_on = None


def upgrade():
    # Create side_quest_categories table
    op.create_table(
        'side_quest_categories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(), nullable=True),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on category ID
    op.create_index(op.f('ix_side_quest_categories_id'), 'side_quest_categories', ['id'], unique=False)
    
    # Create side_quests table
    op.create_table(
        'side_quests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location_name', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('distance_from_route', sa.Float(), nullable=True),
        sa.Column('detour_time', sa.Integer(), nullable=True),
        sa.Column('uniqueness_score', sa.Float(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('external_id', sa.String(), nullable=True),
        sa.Column('external_rating', sa.Float(), nullable=True),
        sa.Column('external_url', sa.String(), nullable=True),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('rewards', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('operating_hours', sa.JSON(), nullable=True),
        sa.Column('price_level', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('is_user_generated', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_seasonal', sa.Boolean(), default=False),
        sa.Column('seasonal_start', sa.DateTime(), nullable=True),
        sa.Column('seasonal_end', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category'], ['side_quest_categories.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for side quests
    op.create_index(op.f('ix_side_quests_id'), 'side_quests', ['id'], unique=False)
    op.create_index(op.f('ix_side_quests_category'), 'side_quests', ['category'], unique=False)
    op.create_index(op.f('ix_side_quests_created_by'), 'side_quests', ['created_by'], unique=False)
    
    # Create spatial index for coordinates
    op.execute(
        "CREATE INDEX ix_side_quests_coordinates ON side_quests USING gist "
        "(ll_to_earth(latitude, longitude))"
    )
    
    # Create index for active side quests
    op.create_index(op.f('ix_side_quests_is_active'), 'side_quests', ['is_active'], unique=False)
    
    # Create user_side_quests table
    op.create_table(
        'user_side_quests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('side_quest_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), default='available', nullable=False),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('skipped_at', sa.DateTime(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('trip_id', sa.String(), nullable=True),
        sa.Column('recommended_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['side_quest_id'], ['side_quests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for user side quests
    op.create_index(op.f('ix_user_side_quests_id'), 'user_side_quests', ['id'], unique=False)
    op.create_index(op.f('ix_user_side_quests_user_id'), 'user_side_quests', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_side_quests_side_quest_id'), 'user_side_quests', ['side_quest_id'], unique=False)
    op.create_index(op.f('ix_user_side_quests_status'), 'user_side_quests', ['status'], unique=False)
    
    # Create unique constraint for user-side_quest pairs
    op.create_unique_constraint('uq_user_side_quests_user_id_side_quest_id', 'user_side_quests', ['user_id', 'side_quest_id'])


def downgrade():
    # Drop constraints first
    op.drop_constraint('uq_user_side_quests_user_id_side_quest_id', 'user_side_quests', type_='unique')
    
    # Drop indexes
    op.drop_index(op.f('ix_user_side_quests_status'), table_name='user_side_quests')
    op.drop_index(op.f('ix_user_side_quests_side_quest_id'), table_name='user_side_quests')
    op.drop_index(op.f('ix_user_side_quests_user_id'), table_name='user_side_quests')
    op.drop_index(op.f('ix_user_side_quests_id'), table_name='user_side_quests')
    
    op.drop_index(op.f('ix_side_quests_is_active'), table_name='side_quests')
    op.drop_index('ix_side_quests_coordinates', table_name='side_quests')
    op.drop_index(op.f('ix_side_quests_created_by'), table_name='side_quests')
    op.drop_index(op.f('ix_side_quests_category'), table_name='side_quests')
    op.drop_index(op.f('ix_side_quests_id'), table_name='side_quests')
    
    op.drop_index(op.f('ix_side_quest_categories_id'), table_name='side_quest_categories')
    
    # Drop tables
    op.drop_table('user_side_quests')
    op.drop_table('side_quests')
    op.drop_table('side_quest_categories')