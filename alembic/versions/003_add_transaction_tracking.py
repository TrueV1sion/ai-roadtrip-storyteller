"""Add transaction tracking and consistency checks

Revision ID: 003_add_transaction_tracking
Revises: 002_add_journey_tracking_and_memories
Create Date: 2025-01-31

This migration adds:
1. Transaction audit log table for tracking critical operations
2. Database consistency check results table
3. Indexes for better transaction performance
4. Additional constraints for data integrity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers
revision = '003_add_transaction_tracking'
down_revision = '002_add_journey_tracking_and_memories'
branch_labels = None
depends_on = None


def upgrade():
    """Add transaction tracking and consistency check tables."""
    
    # Create transaction audit log table
    op.create_table(
        'transaction_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(50), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for transaction audit logs
    op.create_index('idx_transaction_audit_logs_transaction_id', 'transaction_audit_logs', ['transaction_id'])
    op.create_index('idx_transaction_audit_logs_operation_type', 'transaction_audit_logs', ['operation_type'])
    op.create_index('idx_transaction_audit_logs_user_id', 'transaction_audit_logs', ['user_id'])
    op.create_index('idx_transaction_audit_logs_created_at', 'transaction_audit_logs', ['created_at'])
    
    # Create database consistency check results table
    op.create_table(
        'consistency_check_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.String(50), nullable=False),
        sa.Column('check_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('issues_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_fixed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('check_details', sa.JSON(), nullable=True),
        sa.Column('fix_details', sa.JSON(), nullable=True),
        sa.Column('run_by', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Create indexes for consistency check results
    op.create_index('idx_consistency_check_results_check_id', 'consistency_check_results', ['check_id'])
    op.create_index('idx_consistency_check_results_check_type', 'consistency_check_results', ['check_type'])
    op.create_index('idx_consistency_check_results_status', 'consistency_check_results', ['status'])
    op.create_index('idx_consistency_check_results_created_at', 'consistency_check_results', ['created_at'])
    
    # Add additional indexes for better transaction performance
    
    # Bookings table - add composite index for common queries
    op.create_index(
        'idx_bookings_user_status_date',
        'bookings',
        ['user_id', 'booking_status', 'booking_date']
    )
    op.create_index(
        'idx_bookings_partner_status_date',
        'bookings',
        ['partner_id', 'booking_status', 'booking_date']
    )
    
    # Commissions table - add index for status queries
    op.create_index(
        'idx_commissions_status_date',
        'commissions',
        ['commission_status', 'created_at']
    )
    
    # Add constraints to ensure data integrity
    
    # Ensure booking amounts are positive
    op.create_check_constraint(
        'ck_bookings_positive_amounts',
        'bookings',
        'gross_amount > 0 AND net_amount >= 0'
    )
    
    # Ensure commission amounts are non-negative
    op.create_check_constraint(
        'ck_commissions_non_negative_amount',
        'commissions',
        'commission_amount >= 0'
    )
    
    # Ensure commission rate is between 0 and 1
    op.create_check_constraint(
        'ck_commissions_valid_rate',
        'commissions',
        'commission_rate >= 0 AND commission_rate <= 1'
    )
    
    # Add transaction tracking columns to critical tables
    
    # Add to bookings table
    op.add_column('bookings', sa.Column('last_transaction_id', sa.String(50), nullable=True))
    op.add_column('bookings', sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Add to users table
    op.add_column('users', sa.Column('last_transaction_id', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Create a function to automatically update transaction counts
    op.execute("""
        CREATE OR REPLACE FUNCTION update_transaction_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_TABLE_NAME = 'bookings' THEN
                NEW.transaction_count = COALESCE(OLD.transaction_count, 0) + 1;
                NEW.last_transaction_id = current_setting('app.current_transaction_id', true);
            ELSIF TG_TABLE_NAME = 'users' THEN
                NEW.transaction_count = COALESCE(OLD.transaction_count, 0) + 1;
                NEW.last_transaction_id = current_setting('app.current_transaction_id', true);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create triggers for automatic transaction tracking
    op.execute("""
        CREATE TRIGGER update_booking_transaction_count
        BEFORE UPDATE ON bookings
        FOR EACH ROW
        EXECUTE FUNCTION update_transaction_count();
    """)
    
    op.execute("""
        CREATE TRIGGER update_user_transaction_count
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_transaction_count();
    """)
    
    # Create a materialized view for commission summary
    op.execute("""
        CREATE MATERIALIZED VIEW commission_summary AS
        SELECT 
            p.id as partner_id,
            p.name as partner_name,
            DATE_TRUNC('month', b.booking_date) as month,
            COUNT(b.id) as booking_count,
            SUM(b.gross_amount) as gross_revenue,
            SUM(c.commission_amount) as total_commission,
            AVG(c.commission_rate) as avg_commission_rate,
            SUM(b.gross_amount - c.commission_amount) as net_revenue
        FROM bookings b
        JOIN partners p ON b.partner_id = p.id
        JOIN commissions c ON c.booking_id = b.id
        WHERE b.booking_status = 'COMPLETED'
        GROUP BY p.id, p.name, DATE_TRUNC('month', b.booking_date)
    """)
    
    # Create index on materialized view
    op.execute("""
        CREATE INDEX idx_commission_summary_partner_month 
        ON commission_summary (partner_id, month DESC)
    """)


def downgrade():
    """Remove transaction tracking and consistency check tables."""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS commission_summary")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_booking_transaction_count ON bookings")
    op.execute("DROP TRIGGER IF EXISTS update_user_transaction_count ON users")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_transaction_count()")
    
    # Remove columns from tables
    op.drop_column('users', 'transaction_count')
    op.drop_column('users', 'last_transaction_id')
    op.drop_column('bookings', 'transaction_count')
    op.drop_column('bookings', 'last_transaction_id')
    
    # Drop constraints
    op.drop_constraint('ck_commissions_valid_rate', 'commissions')
    op.drop_constraint('ck_commissions_non_negative_amount', 'commissions')
    op.drop_constraint('ck_bookings_positive_amounts', 'bookings')
    
    # Drop indexes
    op.drop_index('idx_commissions_status_date', 'commissions')
    op.drop_index('idx_bookings_partner_status_date', 'bookings')
    op.drop_index('idx_bookings_user_status_date', 'bookings')
    
    # Drop consistency check results table
    op.drop_index('idx_consistency_check_results_created_at', 'consistency_check_results')
    op.drop_index('idx_consistency_check_results_status', 'consistency_check_results')
    op.drop_index('idx_consistency_check_results_check_type', 'consistency_check_results')
    op.drop_index('idx_consistency_check_results_check_id', 'consistency_check_results')
    op.drop_table('consistency_check_results')
    
    # Drop transaction audit logs table
    op.drop_index('idx_transaction_audit_logs_created_at', 'transaction_audit_logs')
    op.drop_index('idx_transaction_audit_logs_user_id', 'transaction_audit_logs')
    op.drop_index('idx_transaction_audit_logs_operation_type', 'transaction_audit_logs')
    op.drop_index('idx_transaction_audit_logs_transaction_id', 'transaction_audit_logs')
    op.drop_table('transaction_audit_logs')