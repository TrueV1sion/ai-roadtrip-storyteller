"""Add performance indexes for common queries

Revision ID: add_performance_indexes
Revises: 
Create Date: 2024-01-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes_old'
down_revision = '20250123_add_event_journeys'
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes to improve query performance."""
    
    # Stories table indexes
    op.create_index(
        'idx_stories_user_created',
        'stories',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_stories_trip_id',
        'stories',
        ['trip_id'],
        postgresql_using='btree'
    )
    
    # Trips table indexes
    op.create_index(
        'idx_trips_user_status',
        'trips',
        ['user_id', 'status'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_trips_created_at',
        'trips',
        ['created_at'],
        postgresql_using='btree'
    )
    
    # Bookings table indexes
    op.create_index(
        'idx_bookings_trip_created',
        'bookings',
        ['trip_id', 'created_at'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_bookings_user_id',
        'bookings',
        ['user_id'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_bookings_partner_status',
        'bookings',
        ['partner_id', 'booking_status'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_bookings_service_date',
        'bookings',
        ['service_date'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_bookings_reference',
        'bookings',
        ['booking_reference'],
        unique=True,
        postgresql_using='btree'
    )
    
    # Users table indexes
    op.create_index(
        'idx_users_email',
        'users',
        ['email'],
        unique=True,
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_users_created_at',
        'users',
        ['created_at'],
        postgresql_using='btree'
    )
    
    # Sessions table indexes
    op.create_index(
        'idx_sessions_token',
        'sessions',
        ['session_token'],
        unique=True,
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_sessions_user_expires',
        'sessions',
        ['user_id', 'expires_at'],
        postgresql_using='btree'
    )
    
    # Commissions table indexes
    op.create_index(
        'idx_commissions_booking_id',
        'commissions',
        ['booking_id'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_commissions_partner_status',
        'commissions',
        ['partner_id', 'status'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_commissions_payout_date',
        'commissions',
        ['payout_date', 'status'],
        postgresql_using='btree'
    )
    
    # Voice interactions table indexes
    op.create_index(
        'idx_voice_interactions_user_created',
        'voice_interactions',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # Locations table indexes (for spatial queries)
    op.execute(
        "CREATE INDEX idx_locations_coordinates ON locations USING GIST (ST_MakePoint(longitude, latitude))"
    )
    
    # Notifications table indexes
    op.create_index(
        'idx_notifications_user_read',
        'notifications',
        ['user_id', 'is_read', 'created_at'],
        postgresql_using='btree'
    )
    
    # Audit logs table indexes
    op.create_index(
        'idx_audit_logs_user_action',
        'audit_logs',
        ['user_id', 'action', 'created_at'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_audit_logs_entity',
        'audit_logs',
        ['entity_type', 'entity_id'],
        postgresql_using='btree'
    )
    
    # Full-text search indexes for story content
    op.execute(
        "CREATE INDEX idx_stories_content_search ON stories USING GIN (to_tsvector('english', content))"
    )
    
    # Partial indexes for common filters
    op.create_index(
        'idx_bookings_pending',
        'bookings',
        ['created_at'],
        postgresql_where="booking_status = 'PENDING'",
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_users_active',
        'users',
        ['email', 'created_at'],
        postgresql_where="is_active = true",
        postgresql_using='btree'
    )
    
    # Composite indexes for complex queries
    op.create_index(
        'idx_bookings_date_range_user',
        'bookings',
        ['user_id', 'service_date', 'booking_status'],
        postgresql_using='btree'
    )
    
    # Add comment to document index purpose
    op.execute(
        "COMMENT ON INDEX idx_stories_user_created IS 'Optimize user story listing queries'"
    )
    op.execute(
        "COMMENT ON INDEX idx_bookings_service_date IS 'Optimize availability and calendar queries'"
    )
    op.execute(
        "COMMENT ON INDEX idx_locations_coordinates IS 'Spatial index for nearby location queries'"
    )


def downgrade():
    """Remove performance indexes."""
    
    # Drop indexes in reverse order
    op.drop_index('idx_bookings_date_range_user', 'bookings')
    op.drop_index('idx_users_active', 'users')
    op.drop_index('idx_bookings_pending', 'bookings')
    
    op.execute("DROP INDEX IF EXISTS idx_stories_content_search")
    op.execute("DROP INDEX IF EXISTS idx_locations_coordinates")
    
    op.drop_index('idx_audit_logs_entity', 'audit_logs')
    op.drop_index('idx_audit_logs_user_action', 'audit_logs')
    op.drop_index('idx_notifications_user_read', 'notifications')
    op.drop_index('idx_voice_interactions_user_created', 'voice_interactions')
    
    op.drop_index('idx_commissions_payout_date', 'commissions')
    op.drop_index('idx_commissions_partner_status', 'commissions')
    op.drop_index('idx_commissions_booking_id', 'commissions')
    
    op.drop_index('idx_sessions_user_expires', 'sessions')
    op.drop_index('idx_sessions_token', 'sessions')
    
    op.drop_index('idx_users_created_at', 'users')
    op.drop_index('idx_users_email', 'users')
    
    op.drop_index('idx_bookings_reference', 'bookings')
    op.drop_index('idx_bookings_service_date', 'bookings')
    op.drop_index('idx_bookings_partner_status', 'bookings')
    op.drop_index('idx_bookings_user_id', 'bookings')
    op.drop_index('idx_bookings_trip_created', 'bookings')
    
    op.drop_index('idx_trips_created_at', 'trips')
    op.drop_index('idx_trips_user_status', 'trips')
    
    op.drop_index('idx_stories_trip_id', 'stories')
    op.drop_index('idx_stories_user_created', 'stories')