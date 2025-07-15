"""major_schema_update

Revision ID: 20240521_major
Revises: 20240521_metadata
Create Date: 2024-05-21 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240521_major'
down_revision = '20240521_metadata'
branch_labels = None
depends_on = None


def upgrade():
    # Update users table with new fields
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('timezone', sa.String(), nullable=True))
    op.add_column('users', sa.Column('language_preference', sa.String(), nullable=True))
    op.add_column('users', sa.Column('notification_settings', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('privacy_settings', sa.JSON(), nullable=True)) 
    op.add_column('users', sa.Column('accessibility_settings', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('metadata', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    
    # Create unique index on username
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('storytelling_style', sa.String(), nullable=True),
        sa.Column('family_friendly', sa.Boolean(), nullable=True),
        sa.Column('voice_interaction', sa.Boolean(), nullable=True),
        sa.Column('age_group', sa.String(), nullable=True),
        sa.Column('education_level', sa.String(), nullable=True),
        sa.Column('travel_style', sa.String(), nullable=True),
        sa.Column('accessibility_needs', sa.JSON(), nullable=True),
        sa.Column('content_filters', sa.JSON(), nullable=True),
        sa.Column('preferred_topics', sa.JSON(), nullable=True),
        sa.Column('avoided_topics', sa.JSON(), nullable=True),
        sa.Column('content_length_preference', sa.String(), nullable=True),
        sa.Column('detail_level', sa.String(), nullable=True),
        sa.Column('media_type_preferences', sa.JSON(), nullable=True),
        sa.Column('language_preferences', sa.JSON(), nullable=True),
        sa.Column('personalization_strategy', sa.String(), nullable=True),
        sa.Column('auto_generate_content', sa.Boolean(), nullable=True),
        sa.Column('share_data_for_improvement', sa.Boolean(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('preference_version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)

    # Create themes table
    op.create_table('themes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('style_attributes', sa.JSON(), nullable=True),
        sa.Column('content_guidelines', sa.JSON(), nullable=True),
        sa.Column('mood_keywords', sa.JSON(), nullable=True),
        sa.Column('color_palette', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_themes_name'), 'themes', ['name'], unique=True)
    op.create_index(op.f('ix_themes_category'), 'themes', ['category'])

    # Create user_theme_preferences table
    op.create_table('user_theme_preferences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=False),
        sa.Column('preference_strength', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_user_theme_preferences_user_id'), 'user_theme_preferences', ['user_id'])
    op.create_index(op.f('ix_user_theme_preferences_theme_id'), 'user_theme_preferences', ['theme_id'])

    # Update stories table - add theme relationship and other missing fields
    op.add_column('stories', sa.Column('title', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('theme_id', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('theme_attributes_used', sa.JSON(), nullable=True))
    op.add_column('stories', sa.Column('location_name', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('language', sa.String(), nullable=False, server_default='en-US'))
    op.add_column('stories', sa.Column('audio_url', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('stories', sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('stories', sa.Column('rating', sa.Integer(), nullable=True))
    op.add_column('stories', sa.Column('play_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('stories', sa.Column('completion_rate', sa.Float(), nullable=True))
    op.create_foreign_key('fk_stories_theme_id', 'stories', 'themes', ['theme_id'], ['id'])

    # Create user_saved_experiences table
    op.create_table('user_saved_experiences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('story_text', sa.Text(), nullable=False),
        sa.Column('playlist_name', sa.String(), nullable=True),
        sa.Column('playlist_tracks', sa.JSON(), nullable=True),
        sa.Column('playlist_provider', sa.String(), nullable=True),
        sa.Column('tts_audio_identifier', sa.String(), nullable=True),
        sa.Column('location_latitude', sa.Float(), nullable=True),
        sa.Column('location_longitude', sa.Float(), nullable=True),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('context_time_of_day', sa.String(), nullable=True),
        sa.Column('context_weather', sa.String(), nullable=True),
        sa.Column('context_mood', sa.String(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('saved_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_user_saved_experiences_user_id'), 'user_saved_experiences', ['user_id'])

    # Create reservations table
    op.create_table('reservations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('reservation_type', sa.String(), nullable=False),
        sa.Column('venue_name', sa.String(), nullable=False),
        sa.Column('venue_address', sa.String(), nullable=True),
        sa.Column('venue_phone', sa.String(), nullable=True),
        sa.Column('reservation_date', sa.DateTime(), nullable=False),
        sa.Column('party_size', sa.Integer(), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('confirmation_number', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_reservations_user_id'), 'reservations', ['user_id'])
    op.create_index(op.f('ix_reservations_status'), 'reservations', ['status'])
    op.create_index(op.f('ix_reservations_reservation_date'), 'reservations', ['reservation_date'])

    # Create side_quests table
    op.create_table('side_quests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location_name', sa.String(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('reward_points', sa.Integer(), nullable=True),
        sa.Column('prerequisites', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('hints', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='available'),
        sa.Column('progress_percentage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('skipped_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_side_quests_user_id'), 'side_quests', ['user_id'])
    op.create_index(op.f('ix_side_quests_status'), 'side_quests', ['status'])
    op.create_index(op.f('ix_side_quests_category'), 'side_quests', ['category'])

    # Create experiences table (if we have a separate Experience model)
    op.create_table('experiences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('experience_type', sa.String(), nullable=True),
        sa.Column('start_latitude', sa.Float(), nullable=True),
        sa.Column('start_longitude', sa.Float(), nullable=True),
        sa.Column('end_latitude', sa.Float(), nullable=True),
        sa.Column('end_longitude', sa.Float(), nullable=True),
        sa.Column('start_location_name', sa.String(), nullable=True),
        sa.Column('end_location_name', sa.String(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='planning'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_experiences_user_id'), 'experiences', ['user_id'])
    op.create_index(op.f('ix_experiences_status'), 'experiences', ['status'])


def downgrade():
    # Drop new tables in reverse order
    op.drop_table('experiences')
    op.drop_table('side_quests')
    op.drop_table('reservations')
    op.drop_table('user_saved_experiences')
    op.drop_table('user_theme_preferences')
    op.drop_table('themes')
    op.drop_table('user_preferences')
    
    # Remove new columns from stories table
    op.drop_constraint('fk_stories_theme_id', 'stories', type_='foreignkey')
    op.drop_column('stories', 'completion_rate')
    op.drop_column('stories', 'play_count')
    op.drop_column('stories', 'rating')
    op.drop_column('stories', 'is_favorite')
    op.drop_column('stories', 'image_url')
    op.drop_column('stories', 'audio_url')
    op.drop_column('stories', 'language')
    op.drop_column('stories', 'location_name')
    op.drop_column('stories', 'theme_attributes_used')
    op.drop_column('stories', 'theme_id')
    op.drop_column('stories', 'title')
    
    # Remove new columns from users table
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'metadata')
    op.drop_column('users', 'role')
    op.drop_column('users', 'is_premium')
    op.drop_column('users', 'accessibility_settings')
    op.drop_column('users', 'privacy_settings')
    op.drop_column('users', 'notification_settings')
    op.drop_column('users', 'language_preference')
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'username')