"""Add journey tracking and trip memories tables

Revision ID: 002_journey_tracking
Revises: 001_initial
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_journey_tracking'
down_revision = 'api_keys_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create journey_tracking table
    op.create_table('journey_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('route_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('engagement_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('stories_delivered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_story_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='SET NULL')
    )
    op.create_index('idx_journey_tracking_user_status', 'journey_tracking', ['user_id', 'status'])
    op.create_index('idx_journey_tracking_session', 'journey_tracking', ['session_id'])

    # Create trip_memories table
    op.create_table('trip_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('journey_id', sa.Integer(), nullable=True),
        sa.Column('phase', sa.String(50), nullable=False),  # pre_trip, in_trip, post_trip, archived
        sa.Column('memory_type', sa.String(50), nullable=False),  # story, interaction, emotion, poi, personality
        sa.Column('memory_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['journey_id'], ['journey_tracking.id'], ondelete='SET NULL')
    )
    op.create_index('idx_trip_memories_user_trip', 'trip_memories', ['user_id', 'trip_id'])
    op.create_index('idx_trip_memories_phase', 'trip_memories', ['phase'])
    op.create_index('idx_trip_memories_type', 'trip_memories', ['memory_type'])

    # Create story_queue table
    op.create_table('story_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('journey_id', sa.Integer(), nullable=False),
        sa.Column('story_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('trigger_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('story_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiry_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['journey_id'], ['journey_tracking.id'], ondelete='CASCADE')
    )
    op.create_index('idx_story_queue_journey_status', 'story_queue', ['journey_id', 'status'])
    op.create_index('idx_story_queue_priority', 'story_queue', ['priority', 'status'])

    # Create progress_tracking table
    op.create_table('progress_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('project_name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('progress_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('milestones', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('team_members', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('voice_notes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('analytics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_update', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_progress_tracking_user_project', 'progress_tracking', ['user_id', 'project_id'])
    op.create_index('idx_progress_tracking_category', 'progress_tracking', ['category'])

    # Create passenger_engagement table
    op.create_table('passenger_engagement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('journey_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('engagement_type', sa.String(50), nullable=False),  # interaction, feedback, skip, request
        sa.Column('engagement_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sentiment', sa.Float(), nullable=True),  # -1.0 to 1.0
        sa.Column('impact_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['journey_id'], ['journey_tracking.id'], ondelete='CASCADE')
    )
    op.create_index('idx_passenger_engagement_journey', 'passenger_engagement', ['journey_id', 'timestamp'])

    # Add new columns to existing tables
    op.add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('voice_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('journey_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    op.add_column('trips', sa.Column('lifecycle_phase', sa.String(50), nullable=False, server_default='planning'))
    op.add_column('trips', sa.Column('memory_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('trips', sa.Column('ar_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('trips', sa.Column('spatial_audio_enabled', sa.Boolean(), nullable=False, server_default='false'))

    # Create trigger for updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply trigger to new tables
    for table in ['journey_tracking', 'progress_tracking']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at BEFORE UPDATE
            ON {table} FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers
    for table in ['journey_tracking', 'progress_tracking']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop new columns from existing tables
    op.drop_column('trips', 'spatial_audio_enabled')
    op.drop_column('trips', 'ar_enabled')
    op.drop_column('trips', 'memory_summary')
    op.drop_column('trips', 'lifecycle_phase')
    
    op.drop_column('users', 'journey_stats')
    op.drop_column('users', 'voice_preferences')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'two_factor_secret')

    # Drop tables
    op.drop_table('passenger_engagement')
    op.drop_table('progress_tracking')
    op.drop_table('story_queue')
    op.drop_table('trip_memories')
    op.drop_table('journey_tracking')