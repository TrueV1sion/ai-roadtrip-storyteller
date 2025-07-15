"""Add event journeys table

Revision ID: 20250123_add_event_journeys
Revises: 20240521_major_schema_update
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250123_add_event_journeys'
down_revision = '20240521_major_schema_update'
branch_labels = None
depends_on = None


def upgrade():
    # Create event_journeys table
    op.create_table(
        'event_journeys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('event_name', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('venue_id', sa.String(), nullable=True),
        sa.Column('venue_name', sa.String(), nullable=False),
        sa.Column('venue_address', sa.String(), nullable=False),
        sa.Column('venue_lat', sa.Float(), nullable=False),
        sa.Column('venue_lon', sa.Float(), nullable=False),
        sa.Column('origin_address', sa.String(), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=False),
        sa.Column('origin_lon', sa.Float(), nullable=False),
        sa.Column('departure_time', sa.DateTime(), nullable=False),
        sa.Column('estimated_arrival', sa.DateTime(), nullable=False),
        sa.Column('voice_personality', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('journey_content', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('theme', sa.String(), nullable=True),
        sa.Column('preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(), server_default='planned', nullable=True),
        sa.Column('actual_departure', sa.DateTime(), nullable=True),
        sa.Column('actual_arrival', sa.DateTime(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('milestones_completed', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('trivia_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_event_journeys_id'), 'event_journeys', ['id'], unique=False)
    op.create_index(op.f('ix_event_journeys_event_id'), 'event_journeys', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_journeys_user_id'), 'event_journeys', ['user_id'], unique=False)
    op.create_index(op.f('ix_event_journeys_event_date'), 'event_journeys', ['event_date'], unique=False)
    op.create_index(op.f('ix_event_journeys_status'), 'event_journeys', ['status'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_event_journeys_status'), table_name='event_journeys')
    op.drop_index(op.f('ix_event_journeys_event_date'), table_name='event_journeys')
    op.drop_index(op.f('ix_event_journeys_user_id'), table_name='event_journeys')
    op.drop_index(op.f('ix_event_journeys_event_id'), table_name='event_journeys')
    op.drop_index(op.f('ix_event_journeys_id'), table_name='event_journeys')
    
    # Drop table
    op.drop_table('event_journeys')