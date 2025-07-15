"""Add 2FA and security fields to users table

Revision ID: 20250603_add_2fa_security_fields
Revises: 20250527_add_parking_reservations
Create Date: 2025-06-03 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250603_add_2fa_security_fields'
down_revision = '20250527_add_parking_reservations'
branch_labels = None
depends_on = None


def upgrade():
    # Add 2FA and security fields to users table
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('two_factor_backup_codes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('two_factor_enabled_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login_ip', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create unique index on username
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    
    # Update existing users to have username = email (temporarily)
    op.execute("""
        UPDATE users 
        SET username = email,
            password_changed_at = created_at
        WHERE username IS NULL
    """)
    
    # Make username not nullable after populating
    op.alter_column('users', 'username', nullable=False)


def downgrade():
    # Remove the added columns
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'is_admin')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'two_factor_enabled_at')
    op.drop_column('users', 'two_factor_backup_codes')
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'username')