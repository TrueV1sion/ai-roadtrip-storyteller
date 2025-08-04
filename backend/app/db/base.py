"""
Compatibility module - redirects to the centralized database module.
"""
from app.database import Base, engine, SessionLocal, get_db

# Export all database components for compatibility
__all__ = ['Base', 'engine', 'SessionLocal', 'get_db']
