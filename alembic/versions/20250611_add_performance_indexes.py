"""Add performance indexes

Revision ID: add_performance_indexes
Revises: 20250603_add_2fa_security_fields
Create Date: 2025-06-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = '20250603_add_2fa_security_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Users table indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Stories table indexes
    op.create_index('idx_stories_user_id', 'stories', ['user_id'])
    op.create_index('idx_stories_journey_id', 'stories', ['journey_id'])
    op.create_index('idx_stories_created_at', 'stories', ['created_at'])
    op.create_index('idx_stories_is_active', 'stories', ['is_active'])
    op.create_index('idx_stories_user_created', 'stories', ['user_id', 'created_at'])
    
    # Journeys table indexes
    op.create_index('idx_journeys_user_id', 'journeys', ['user_id'])
    op.create_index('idx_journeys_status', 'journeys', ['status'])
    op.create_index('idx_journeys_created_at', 'journeys', ['created_at'])
    op.create_index('idx_journeys_start_time', 'journeys', ['start_time'])
    op.create_index('idx_journeys_user_status', 'journeys', ['user_id', 'status'])
    
    # Bookings table indexes
    op.create_index('idx_bookings_user_id', 'bookings', ['user_id'])
    op.create_index('idx_bookings_journey_id', 'bookings', ['journey_id'])
    op.create_index('idx_bookings_status', 'bookings', ['status'])
    op.create_index('idx_bookings_provider', 'bookings', ['provider'])
    op.create_index('idx_bookings_created_at', 'bookings', ['created_at'])
    op.create_index('idx_bookings_booking_time', 'bookings', ['booking_time'])
    op.create_index('idx_bookings_user_status', 'bookings', ['user_id', 'status'])
    
    # Reservations table indexes
    op.create_index('idx_reservations_user_id', 'reservations', ['user_id'])
    op.create_index('idx_reservations_booking_id', 'reservations', ['booking_id'])
    op.create_index('idx_reservations_status', 'reservations', ['status'])
    op.create_index('idx_reservations_check_in_date', 'reservations', ['check_in_date'])
    op.create_index('idx_reservations_user_status', 'reservations', ['user_id', 'status'])
    
    # Parking reservations table indexes
    op.create_index('idx_parking_reservations_user_id', 'parking_reservations', ['user_id'])
    op.create_index('idx_parking_reservations_journey_id', 'parking_reservations', ['journey_id'])
    op.create_index('idx_parking_reservations_status', 'parking_reservations', ['status'])
    op.create_index('idx_parking_reservations_start_time', 'parking_reservations', ['start_time'])
    
    # Commission tracking table indexes
    op.create_index('idx_commission_tracking_booking_id', 'commission_tracking', ['booking_id'])
    op.create_index('idx_commission_tracking_provider', 'commission_tracking', ['provider'])
    op.create_index('idx_commission_tracking_status', 'commission_tracking', ['status'])
    op.create_index('idx_commission_tracking_created_at', 'commission_tracking', ['created_at'])
    op.create_index('idx_commission_tracking_provider_date', 'commission_tracking', ['provider', 'created_at'])
    
    # Event journeys table indexes
    op.create_index('idx_event_journeys_journey_id', 'event_journeys', ['journey_id'])
    op.create_index('idx_event_journeys_event_id', 'event_journeys', ['event_id'])
    op.create_index('idx_event_journeys_event_date', 'event_journeys', ['event_date'])
    op.create_index('idx_event_journeys_venue_id', 'event_journeys', ['venue_id'])
    
    # Side quests table indexes
    op.create_index('idx_side_quests_journey_id', 'side_quests', ['journey_id'])
    op.create_index('idx_side_quests_status', 'side_quests', ['status'])
    op.create_index('idx_side_quests_created_at', 'side_quests', ['created_at'])
    
    # Themes table indexes
    op.create_index('idx_themes_user_id', 'themes', ['user_id'])
    op.create_index('idx_themes_journey_id', 'themes', ['journey_id'])
    op.create_index('idx_themes_is_active', 'themes', ['is_active'])
    
    # User preferences table indexes
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])
    
    # Story metadata table indexes
    op.create_index('idx_story_metadata_story_id', 'story_metadata', ['story_id'])
    op.create_index('idx_story_metadata_journey_id', 'story_metadata', ['journey_id'])
    
    # Create composite indexes for common query patterns
    op.create_index('idx_stories_user_journey_created', 'stories', 
                    ['user_id', 'journey_id', 'created_at'])
    op.create_index('idx_bookings_user_created_status', 'bookings', 
                    ['user_id', 'created_at', 'status'])
    op.create_index('idx_journeys_user_start_status', 'journeys', 
                    ['user_id', 'start_time', 'status'])
    
    # Create partial indexes for active records (PostgreSQL specific)
    op.execute("""
        CREATE INDEX idx_stories_active_recent 
        ON stories (created_at DESC) 
        WHERE is_active = true
    """)
    
    op.execute("""
        CREATE INDEX idx_bookings_pending 
        ON bookings (created_at DESC) 
        WHERE status = 'pending'
    """)
    
    op.execute("""
        CREATE INDEX idx_journeys_active 
        ON journeys (start_time DESC) 
        WHERE status = 'active'
    """)
    
    # Create indexes for text search (if using PostgreSQL full-text search)
    op.execute("""
        CREATE INDEX idx_stories_content_search 
        ON stories 
        USING gin(to_tsvector('english', content))
    """)
    
    op.execute("""
        CREATE INDEX idx_venues_name_search 
        ON event_journeys 
        USING gin(to_tsvector('english', venue_name))
    """)
    
    print("Performance indexes created successfully")


def downgrade():
    # Drop all indexes in reverse order
    op.drop_index('idx_venues_name_search', 'event_journeys')
    op.drop_index('idx_stories_content_search', 'stories')
    op.drop_index('idx_journeys_active', 'journeys')
    op.drop_index('idx_bookings_pending', 'bookings')
    op.drop_index('idx_stories_active_recent', 'stories')
    
    # Drop composite indexes
    op.drop_index('idx_journeys_user_start_status', 'journeys')
    op.drop_index('idx_bookings_user_created_status', 'bookings')
    op.drop_index('idx_stories_user_journey_created', 'stories')
    
    # Drop regular indexes
    op.drop_index('idx_story_metadata_journey_id', 'story_metadata')
    op.drop_index('idx_story_metadata_story_id', 'story_metadata')
    op.drop_index('idx_user_preferences_user_id', 'user_preferences')
    op.drop_index('idx_themes_is_active', 'themes')
    op.drop_index('idx_themes_journey_id', 'themes')
    op.drop_index('idx_themes_user_id', 'themes')
    op.drop_index('idx_side_quests_created_at', 'side_quests')
    op.drop_index('idx_side_quests_status', 'side_quests')
    op.drop_index('idx_side_quests_journey_id', 'side_quests')
    op.drop_index('idx_event_journeys_venue_id', 'event_journeys')
    op.drop_index('idx_event_journeys_event_date', 'event_journeys')
    op.drop_index('idx_event_journeys_event_id', 'event_journeys')
    op.drop_index('idx_event_journeys_journey_id', 'event_journeys')
    op.drop_index('idx_commission_tracking_provider_date', 'commission_tracking')
    op.drop_index('idx_commission_tracking_created_at', 'commission_tracking')
    op.drop_index('idx_commission_tracking_status', 'commission_tracking')
    op.drop_index('idx_commission_tracking_provider', 'commission_tracking')
    op.drop_index('idx_commission_tracking_booking_id', 'commission_tracking')
    op.drop_index('idx_parking_reservations_start_time', 'parking_reservations')
    op.drop_index('idx_parking_reservations_status', 'parking_reservations')
    op.drop_index('idx_parking_reservations_journey_id', 'parking_reservations')
    op.drop_index('idx_parking_reservations_user_id', 'parking_reservations')
    op.drop_index('idx_reservations_user_status', 'reservations')
    op.drop_index('idx_reservations_check_in_date', 'reservations')
    op.drop_index('idx_reservations_status', 'reservations')
    op.drop_index('idx_reservations_booking_id', 'reservations')
    op.drop_index('idx_reservations_user_id', 'reservations')
    op.drop_index('idx_bookings_user_status', 'bookings')
    op.drop_index('idx_bookings_booking_time', 'bookings')
    op.drop_index('idx_bookings_created_at', 'bookings')
    op.drop_index('idx_bookings_provider', 'bookings')
    op.drop_index('idx_bookings_status', 'bookings')
    op.drop_index('idx_bookings_journey_id', 'bookings')
    op.drop_index('idx_bookings_user_id', 'bookings')
    op.drop_index('idx_journeys_user_status', 'journeys')
    op.drop_index('idx_journeys_start_time', 'journeys')
    op.drop_index('idx_journeys_created_at', 'journeys')
    op.drop_index('idx_journeys_status', 'journeys')
    op.drop_index('idx_journeys_user_id', 'journeys')
    op.drop_index('idx_stories_user_created', 'stories')
    op.drop_index('idx_stories_is_active', 'stories')
    op.drop_index('idx_stories_created_at', 'stories')
    op.drop_index('idx_stories_journey_id', 'stories')
    op.drop_index('idx_stories_user_id', 'stories')
    op.drop_index('idx_users_created_at', 'users')
    op.drop_index('idx_users_is_active', 'users')
    op.drop_index('idx_users_email', 'users')