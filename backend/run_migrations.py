#!/usr/bin/env python
"""Run database migrations programmatically"""
import os
import sys
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

def run_migrations():
    """Run Alembic migrations"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    print(f"Running migrations...")
    
    # Test database connection
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print(f"Connected to: {result.scalar()}")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)
    
    # Run migrations
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        print("Current revision:")
        command.current(alembic_cfg)
        
        print("Upgrading to head...")
        command.upgrade(alembic_cfg, "head")
        
        print("New revision:")
        command.current(alembic_cfg)
        
        print("✅ Migrations completed successfully!")
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()