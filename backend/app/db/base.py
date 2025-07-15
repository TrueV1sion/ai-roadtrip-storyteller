from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Check connection before using it
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create sessionmaker with the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Dependency to get a database session
def get_db():
    """
    Dependency for FastAPI to get a database session.
    Will be used in route dependencies to access the database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
