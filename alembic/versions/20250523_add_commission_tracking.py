"""Add commission tracking and revenue analytics tables

Revision ID: add_commission_tracking
Revises: 20240521_major_schema_update
Create Date: 2025-05-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_commission_tracking'
down_revision = '20240521_major_schema_update'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum for booking types
    booking_type_enum = postgresql.ENUM(
        'restaurant',
        'attraction',
        'accommodation',
        'activity',
        'transportation',
        name='booking_type'
    )
    booking_type_enum.create(op.get_bind())
    
    # Create enum for booking status
    booking_status_enum = postgresql.ENUM(
        'pending',
        'confirmed',
        'completed',
        'cancelled',
        'refunded',
        name='booking_status'
    )
    booking_status_enum.create(op.get_bind())
    
    # Create enum for commission status
    commission_status_enum = postgresql.ENUM(
        'pending',
        'approved',
        'paid',
        'disputed',
        name='commission_status'
    )
    commission_status_enum.create(op.get_bind())
    
    # Create partners table
    op.create_table('partners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('partner_code', sa.String(50), nullable=False, unique=True),
        sa.Column('api_endpoint', sa.String(500), nullable=True),
        sa.Column('api_key', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('partner_code')
    )
    
    # Create commission rates table
    op.create_table('commission_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('booking_type', booking_type_enum, nullable=False),
        sa.Column('base_rate', sa.Numeric(5, 4), nullable=False),  # e.g., 0.1500 for 15%
        sa.Column('tier_1_threshold', sa.Numeric(10, 2), nullable=True),
        sa.Column('tier_1_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('tier_2_threshold', sa.Numeric(10, 2), nullable=True),
        sa.Column('tier_2_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('tier_3_threshold', sa.Numeric(10, 2), nullable=True),
        sa.Column('tier_3_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create bookings table
    op.create_table('bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_reference', sa.String(100), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('booking_type', booking_type_enum, nullable=False),
        sa.Column('booking_status', booking_status_enum, nullable=False, default='pending'),
        sa.Column('booking_date', sa.DateTime(), nullable=False),
        sa.Column('service_date', sa.DateTime(), nullable=False),
        sa.Column('gross_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('net_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('partner_booking_id', sa.String(100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_reference')
    )
    
    # Create commissions table
    op.create_table('commissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('commission_rate_id', sa.Integer(), nullable=False),
        sa.Column('commission_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('commission_rate', sa.Numeric(5, 4), nullable=False),
        sa.Column('commission_status', commission_status_enum, nullable=False, default='pending'),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
        sa.ForeignKeyConstraint(['commission_rate_id'], ['commission_rates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create revenue analytics table (for pre-calculated metrics)
    op.create_table('revenue_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=True),
        sa.Column('booking_type', booking_type_enum, nullable=True),
        sa.Column('total_bookings', sa.Integer(), nullable=False, default=0),
        sa.Column('completed_bookings', sa.Integer(), nullable=False, default=0),
        sa.Column('cancelled_bookings', sa.Integer(), nullable=False, default=0),
        sa.Column('gross_revenue', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('net_revenue', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('total_commission', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('conversion_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('average_booking_value', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'partner_id', 'booking_type', name='uq_revenue_analytics_date_partner_type')
    )
    
    # Create indexes for performance
    op.create_index(op.f('ix_bookings_user_id'), 'bookings', ['user_id'], unique=False)
    op.create_index(op.f('ix_bookings_partner_id'), 'bookings', ['partner_id'], unique=False)
    op.create_index(op.f('ix_bookings_booking_date'), 'bookings', ['booking_date'], unique=False)
    op.create_index(op.f('ix_bookings_service_date'), 'bookings', ['service_date'], unique=False)
    op.create_index(op.f('ix_bookings_booking_status'), 'bookings', ['booking_status'], unique=False)
    op.create_index(op.f('ix_commissions_booking_id'), 'commissions', ['booking_id'], unique=False)
    op.create_index(op.f('ix_commissions_commission_status'), 'commissions', ['commission_status'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_date'), 'revenue_analytics', ['date'], unique=False)
    op.create_index(op.f('ix_revenue_analytics_partner_id'), 'revenue_analytics', ['partner_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_revenue_analytics_partner_id'), table_name='revenue_analytics')
    op.drop_index(op.f('ix_revenue_analytics_date'), table_name='revenue_analytics')
    op.drop_index(op.f('ix_commissions_commission_status'), table_name='commissions')
    op.drop_index(op.f('ix_commissions_booking_id'), table_name='commissions')
    op.drop_index(op.f('ix_bookings_booking_status'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_service_date'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_booking_date'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_partner_id'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_user_id'), table_name='bookings')
    
    # Drop tables
    op.drop_table('revenue_analytics')
    op.drop_table('commissions')
    op.drop_table('bookings')
    op.drop_table('commission_rates')
    op.drop_table('partners')
    
    # Drop enums
    commission_status_enum = postgresql.ENUM('pending', 'approved', 'paid', 'disputed', name='commission_status')
    commission_status_enum.drop(op.get_bind())
    
    booking_status_enum = postgresql.ENUM('pending', 'confirmed', 'completed', 'cancelled', 'refunded', name='booking_status')
    booking_status_enum.drop(op.get_bind())
    
    booking_type_enum = postgresql.ENUM('restaurant', 'attraction', 'accommodation', 'activity', 'transportation', name='booking_type')
    booking_type_enum.drop(op.get_bind())