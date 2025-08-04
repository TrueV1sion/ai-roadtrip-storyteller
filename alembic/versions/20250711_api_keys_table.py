"""Create API keys table

Revision ID: api_keys_001
Revises: 
Create Date: 2025-07-11 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'api_keys_001'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create api_keys table for API key management."""
    op.create_table(
        'api_keys',
        sa.Column('key_id', sa.String(), nullable=False),
        sa.Column('secret_key_hash', sa.String(), nullable=False),
        sa.Column('client_name', sa.String(), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=True, default=1000),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('key_id')
    )
    
    # Create indexes for performance
    op.create_index(
        'idx_api_keys_key_id',
        'api_keys',
        ['key_id'],
        unique=True
    )
    
    op.create_index(
        'idx_api_keys_is_active',
        'api_keys',
        ['is_active']
    )
    
    op.create_index(
        'idx_api_keys_client_name',
        'api_keys',
        ['client_name']
    )
    
    op.create_index(
        'idx_api_keys_expires_at',
        'api_keys',
        ['expires_at']
    )


def downgrade() -> None:
    """Drop api_keys table."""
    op.drop_index('idx_api_keys_expires_at', table_name='api_keys')
    op.drop_index('idx_api_keys_client_name', table_name='api_keys')
    op.drop_index('idx_api_keys_is_active', table_name='api_keys')
    op.drop_index('idx_api_keys_key_id', table_name='api_keys')
    op.drop_table('api_keys')