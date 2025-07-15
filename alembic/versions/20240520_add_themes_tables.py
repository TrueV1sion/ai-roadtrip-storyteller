"""Add themes tables and update story model

Revision ID: 20240520b
Revises: 20240520a
Create Date: 2024-05-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240520b'
down_revision = '20240520a'
branch_labels = None
depends_on = None


def upgrade():
    # Create themes table
    op.create_table(
        'themes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('style_guide', sa.JSON(), nullable=False),
        sa.Column('recommended_interests', sa.JSON(), nullable=True),
        sa.Column('music_genres', sa.JSON(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_seasonal', sa.Boolean(), default=False),
        sa.Column('available_from', sa.DateTime(), nullable=True),
        sa.Column('available_until', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_theme_preferences table
    op.create_table(
        'user_theme_preferences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=False),
        sa.Column('is_favorite', sa.Boolean(), default=False),
        sa.Column('preference_level', sa.String(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add theme columns to stories table
    op.add_column('stories', sa.Column('theme_id', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('theme_attributes_used', sa.JSON(), nullable=True))
    op.create_foreign_key('fk_stories_theme_id', 'stories', 'themes', ['theme_id'], ['id'])
    
    # Create indexes
    op.create_index(op.f('ix_themes_id'), 'themes', ['id'], unique=False)
    op.create_index(op.f('ix_user_theme_preferences_id'), 'user_theme_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_user_theme_preferences_user_id'), 'user_theme_preferences', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_theme_preferences_theme_id'), 'user_theme_preferences', ['theme_id'], unique=False)


def downgrade():
    # Drop foreign key constraint from stories table
    op.drop_constraint('fk_stories_theme_id', 'stories', type_='foreignkey')
    
    # Drop theme columns from stories table
    op.drop_column('stories', 'theme_attributes_used')
    op.drop_column('stories', 'theme_id')
    
    # Drop indexes
    op.drop_index(op.f('ix_user_theme_preferences_theme_id'), table_name='user_theme_preferences')
    op.drop_index(op.f('ix_user_theme_preferences_user_id'), table_name='user_theme_preferences')
    op.drop_index(op.f('ix_user_theme_preferences_id'), table_name='user_theme_preferences')
    op.drop_index(op.f('ix_themes_id'), table_name='themes')
    
    # Drop tables
    op.drop_table('user_theme_preferences')
    op.drop_table('themes')