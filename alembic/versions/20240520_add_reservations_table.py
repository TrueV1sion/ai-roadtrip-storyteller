"""Add reservations table

Revision ID: 20240520a
Revises: 20240210_initial_migration
Create Date: 2024-05-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240520a'
down_revision = '20240210_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=True),
        sa.Column('venue_name', sa.String(), nullable=False),
        sa.Column('venue_id', sa.String(), nullable=True),
        sa.Column('venue_address', sa.Text(), nullable=True),
        sa.Column('reservation_time', sa.DateTime(), nullable=False),
        sa.Column('party_size', sa.String(), nullable=False),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('confirmation_number', sa.String(), nullable=True),
        sa.Column('contact_phone', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on user_id for faster lookups of user reservations
    op.create_index(op.f('ix_reservations_id'), 'reservations', ['id'], unique=False)
    op.create_index(op.f('ix_reservations_user_id'), 'reservations', ['user_id'], unique=False)
    
    # Create index on reservation_time for efficient date range queries
    op.create_index(op.f('ix_reservations_reservation_time'), 'reservations', ['reservation_time'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_reservations_reservation_time'), table_name='reservations')
    op.drop_index(op.f('ix_reservations_user_id'), table_name='reservations')
    op.drop_index(op.f('ix_reservations_id'), table_name='reservations')
    
    # Drop the table
    op.drop_table('reservations')