"""
Database configuration and dependencies.
Uses the robust DatabaseManager for connection handling.
"""

from sqlalchemy.ext.declarative import declarative_base
from app.core.database_manager import (
    db_manager, 
    get_db, 
    get_async_db, 
    initialize_database,
    get_database_health,
    get_database_info,
    check_database_migrations
)

# Create Base class for declarative models
Base = declarative_base()

# Export the engine for compatibility
engine = db_manager.sync_engine
SessionLocal = db_manager.SessionLocal

# Initialize database on import
if not initialize_database():
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Database initialization failed - will retry on first use") 