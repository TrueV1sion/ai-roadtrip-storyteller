"""
Database Manager with Connection Validation and Health Checks
Provides robust database connectivity with automatic retry and failover
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, text, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.pool import QueuePool
import asyncpg
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections with health checks and failover."""
    
    def __init__(self):
        self.sync_engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self.is_connected = False
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds
        
    def initialize(self) -> bool:
        """
        Initialize database connections.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Get database URL from settings
            database_url = getattr(settings, 'DATABASE_URL', None)
            if not database_url:
                logger.error("DATABASE_URL not configured")
                return False
            
            # Determine pool settings based on environment
            # Six Sigma optimized settings
            if settings.ENVIRONMENT == "production":
                pool_size = 50  # Increased from 20 per Six Sigma requirements
                max_overflow = 100  # Increased from 40 per Six Sigma requirements
                pool_timeout = 30
                pool_recycle = 1800  # Reduced from 3600 for better connection freshness
                connect_args = {
                    "connect_timeout": 10,
                    "application_name": "roadtrip_api_optimized",
                    "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000",  # Added idle timeout
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                } if database_url.startswith("postgresql") else {}
            else:
                pool_size = 10  # Increased from 5 for better development performance
                max_overflow = 20  # Increased from 10
                pool_timeout = 30
                pool_recycle = 1800  # Reduced from 3600
                connect_args = {
                    "connect_timeout": 30,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                } if database_url.startswith("postgresql") else {}
            
            # Create synchronous engine
            self.sync_engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_pre_ping=True,
                pool_recycle=pool_recycle,
                echo=False,  # Set to True for SQL debugging
                connect_args=connect_args
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.sync_engine
            )
            
            # Create async engine if URL supports it
            if database_url.startswith("postgresql"):
                async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
                self.async_engine = create_async_engine(
                    async_url,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_pre_ping=True,
                    pool_recycle=pool_recycle,
                    echo=False,
                    pool_timeout=pool_timeout
                )
                
                self.AsyncSessionLocal = async_sessionmaker(
                    bind=self.async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
            
            # Test connection
            if self._test_connection():
                self.is_connected = True
                logger.info("Database manager initialized successfully")
                return True
            else:
                logger.error("Database connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((SQLAlchemyError, asyncpg.PostgresError))
    )
    def _test_connection(self) -> bool:
        """Test database connection with retry logic."""
        try:
            with self.sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test returned unexpected result")
                    return False
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    def get_db_session(self):
        """
        Get a database session (dependency injection pattern).
        
        Yields:
            Session: SQLAlchemy session
        """
        if not self.is_connected:
            if not self.initialize():
                raise RuntimeError("Database not available")
        
        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @asynccontextmanager
    async def get_async_db_session(self):
        """
        Get an async database session.
        
        Yields:
            AsyncSession: SQLAlchemy async session
        """
        if not self.async_engine:
            raise RuntimeError("Async database engine not available")
        
        if not self.is_connected:
            if not self.initialize():
                raise RuntimeError("Database not available")
        
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Async database session error: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check database health and return status.
        
        Returns:
            Dict with health check results
        """
        current_time = time.time()
        
        # Skip if recently checked
        if current_time - self.last_health_check < self.health_check_interval:
            return {
                "status": "healthy" if self.is_connected else "unhealthy",
                "last_check": self.last_health_check,
                "cached": True
            }
        
        health_status = {
            "status": "unknown",
            "connection_pool": {},
            "response_time_ms": 0,
            "last_check": current_time,
            "cached": False
        }
        
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with self.sync_engine.connect() as conn:
                result = conn.execute(text("SELECT version(), now()"))
                row = result.fetchone()
                
                if row:
                    health_status["status"] = "healthy"
                    health_status["database_version"] = str(row[0])[:50]  # Truncate version string
                    health_status["server_time"] = str(row[1])
                    self.is_connected = True
                else:
                    health_status["status"] = "unhealthy"
                    health_status["error"] = "No response from database"
                    self.is_connected = False
            
            # Check connection pool status
            pool = self.sync_engine.pool
            health_status["connection_pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
            
            # Calculate response time
            health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            self.is_connected = False
        
        self.last_health_check = current_time
        return health_status
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information."""
        if not self.sync_engine:
            return {"status": "not_initialized"}
        
        return {
            "url": str(self.sync_engine.url).replace(self.sync_engine.url.password or "", "***"),
            "driver": self.sync_engine.url.drivername,
            "database": self.sync_engine.url.database,
            "host": self.sync_engine.url.host,
            "port": self.sync_engine.url.port,
            "pool_size": self.sync_engine.pool.size(),
            "max_overflow": self.sync_engine.pool._max_overflow,
            "is_connected": self.is_connected
        }
    
    async def run_migration_check(self) -> Dict[str, Any]:
        """Check if database migrations are up to date."""
        try:
            with self.sync_engine.connect() as conn:
                # Check if alembic_version table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    );
                """))
                
                has_alembic = result.fetchone()[0]
                
                if not has_alembic:
                    return {
                        "status": "no_migrations",
                        "message": "Alembic version table not found. Run 'alembic upgrade head'"
                    }
                
                # Get current migration version
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_version = result.fetchone()
                
                if current_version:
                    return {
                        "status": "migrations_applied",
                        "current_version": current_version[0],
                        "message": "Database migrations are applied"
                    }
                else:
                    return {
                        "status": "no_version",
                        "message": "No migration version found. Run 'alembic upgrade head'"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Could not check migration status"
            }
    
    def close(self):
        """Close database connections."""
        try:
            if self.sync_engine:
                self.sync_engine.dispose()
                logger.info("Synchronous database engine disposed")
            
            if self.async_engine:
                # Note: async engine disposal should be done in async context
                logger.info("Async database engine marked for disposal")
                
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance
db_manager = DatabaseManager()


# Dependency function for FastAPI
def get_db():
    """Dependency to get database session for FastAPI routes."""
    yield from db_manager.get_db_session()


async def get_async_db():
    """Dependency to get async database session for FastAPI routes."""
    async with db_manager.get_async_db_session() as session:
        yield session


def initialize_database() -> bool:
    """Initialize the database manager."""
    return db_manager.initialize()


def get_database_health() -> Dict[str, Any]:
    """Get database health status."""
    return db_manager.check_health()


def get_database_info() -> Dict[str, Any]:
    """Get database connection information."""
    return db_manager.get_connection_info()


async def check_database_migrations() -> Dict[str, Any]:
    """Check database migration status."""
    return await db_manager.run_migration_check()