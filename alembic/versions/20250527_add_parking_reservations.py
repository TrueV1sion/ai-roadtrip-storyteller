"""Add parking reservations table

Revision ID: 20250527_add_parking_reservations
Revises: 20250523_add_commission_tracking
Create Date: 2025-05-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250527_add_parking_reservations'
down_revision = 'add_commission_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Create parking_reservations table
    op.create_table('parking_reservations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('parking_type', sa.String(), nullable=False),
        sa.Column('location_name', sa.String(), nullable=False),
        sa.Column('terminal', sa.String(), nullable=True),
        sa.Column('lot_name', sa.String(), nullable=True),
        sa.Column('spot_number', sa.String(), nullable=True),
        sa.Column('vehicle_make', sa.String(), nullable=True),
        sa.Column('vehicle_model', sa.String(), nullable=True),
        sa.Column('vehicle_color', sa.String(), nullable=True),
        sa.Column('license_plate', sa.String(), nullable=True),
        sa.Column('check_in_time', sa.DateTime(), nullable=False),
        sa.Column('check_out_time', sa.DateTime(), nullable=False),
        sa.Column('daily_rate', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('parking_photo_url', sa.String(), nullable=True),
        sa.Column('photo_uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('photo_metadata', sa.JSON(), nullable=True),
        sa.Column('return_reminder_sent', sa.Boolean(), nullable=True, default=False),
        sa.Column('return_journey_scheduled', sa.Boolean(), nullable=True, default=False),
        sa.Column('estimated_pickup_time', sa.DateTime(), nullable=True),
        sa.Column('outbound_flight', sa.String(), nullable=True),
        sa.Column('return_flight', sa.String(), nullable=True),
        sa.Column('airline', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['reservations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_parking_check_out_time', 'parking_reservations', ['check_out_time'])
    op.create_index('idx_parking_location', 'parking_reservations', ['location_name'])
    op.create_index('idx_parking_return_reminder', 'parking_reservations', ['return_reminder_sent', 'check_out_time'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_parking_return_reminder', table_name='parking_reservations')
    op.drop_index('idx_parking_location', table_name='parking_reservations')
    op.drop_index('idx_parking_check_out_time', table_name='parking_reservations')
    
    # Drop table
    op.drop_table('parking_reservations')