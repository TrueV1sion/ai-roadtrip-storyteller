"""Add user role column

Revision ID: 20240517_add_user_role
Revises: 20240210_initial_migration
Create Date: 2024-05-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240517_add_user_role'
down_revision = '20240210_initial'
branch_labels = None
depends_on = None


# Define the enum values directly to avoid importing the model
user_roles = sa.Enum('admin', 'premium', 'standard', 'guest', name='userrole')


def upgrade():
    # Create enum type first
    user_roles.create(op.get_bind())
    
    # Add role column to users table with default value of 'standard'
    op.add_column('users', sa.Column('role', user_roles, nullable=True))
    
    # Set default role for existing users
    op.execute("UPDATE users SET role = 'standard'")
    
    # Make the column not nullable after setting default values
    op.alter_column('users', 'role', nullable=False, server_default='standard')


def downgrade():
    # Remove role column
    op.drop_column('users', 'role')
    
    # Drop the enum type
    user_roles.drop(op.get_bind())