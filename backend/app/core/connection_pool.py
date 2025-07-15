"""
Optimized Database Connection Pool Management
"""
from typing import Dict, Any, Optional
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class ConnectionPoolManager:
    """
    Advanced connection pool manager with monitoring and optimization.
    """
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._monitor_thread = None
        self._running = False
        
    def create_optimized_engine(
        self,
        database_url: str,
        pool_name: str = "default",
        **kwargs
    ) -> Any:
        """
        Create an optimized database engine with custom pooling.
        
        Args:
            database_url: Database connection URL
            pool_name: Name for this pool
            **kwargs: Additional engine arguments
            
        Returns:
            SQLAlchemy Engine
        """
        # Determine optimal pool settings based on environment
        pool_settings = self._get_optimal_pool_settings()
        
        # Merge with provided kwargs
        engine_args = {
            **pool_settings,
            **kwargs
        }
        
        # Create engine with optimized settings
        engine = create_engine(
            database_url,
            **engine_args
        )
        
        # Register event listeners for monitoring
        self._register_pool_events(engine, pool_name)
        
        # Store pool reference
        with self._lock:
            self.pools[pool_name] = engine
            self.metrics[pool_name] = {
                "connections_created": 0,
                "connections_recycled": 0,
                "connections_invalidated": 0,
                "overflow_created": 0,
                "checkout_time": [],
                "active_connections": 0,
                "pool_size": pool_settings.get("pool_size", 5)
            }
        
        logger.info(f"Created optimized connection pool '{pool_name}' with settings: {pool_settings}")
        return engine
    
    def _get_optimal_pool_settings(self) -> Dict[str, Any]:
        """Determine optimal pool settings based on environment"""
        if settings.ENVIRONMENT == "production":
            return {
                "poolclass": QueuePool,
                "pool_size": 20,
                "max_overflow": 40,
                "pool_timeout": 30,
                "pool_recycle": 3600,  # 1 hour
                "pool_pre_ping": True,
                "echo_pool": False,
                "connect_args": {
                    "connect_timeout": 10,
                    "application_name": "roadtrip_api",
                    "options": "-c statement_timeout=30000"  # 30 second statement timeout
                }
            }
        elif settings.ENVIRONMENT == "development":
            return {
                "poolclass": QueuePool,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 1800,  # 30 minutes
                "pool_pre_ping": True,
                "echo_pool": True,
                "connect_args": {
                    "connect_timeout": 5,
                    "application_name": "roadtrip_api_dev"
                }
            }
        else:  # test
            return {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False
                }
            }
    
    def _register_pool_events(self, engine: Any, pool_name: str):
        """Register event listeners for connection pool monitoring"""
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Called when a new connection is created"""
            with self._lock:
                self.metrics[pool_name]["connections_created"] += 1
            connection_record.info['connect_time'] = time.time()
            
            # Set connection parameters for PostgreSQL
            if hasattr(dbapi_conn, 'set_session'):
                dbapi_conn.set_session(
                    isolation_level="READ COMMITTED",
                    readonly=False,
                    deferrable=False,
                    autocommit=False
                )
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Called when a connection is checked out from the pool"""
            checkout_time = time.time()
            connection_record.info['checkout_time'] = checkout_time
            with self._lock:
                self.metrics[pool_name]["active_connections"] += 1
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """Called when a connection is returned to the pool"""
            checkout_time = connection_record.info.get('checkout_time')
            if checkout_time:
                duration = time.time() - checkout_time
                with self._lock:
                    self.metrics[pool_name]["checkout_time"].append(duration)
                    self.metrics[pool_name]["active_connections"] -= 1
                    
                    # Keep only last 1000 measurements
                    if len(self.metrics[pool_name]["checkout_time"]) > 1000:
                        self.metrics[pool_name]["checkout_time"] = \
                            self.metrics[pool_name]["checkout_time"][-1000:]
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            """Called when a connection is invalidated"""
            with self._lock:
                self.metrics[pool_name]["connections_invalidated"] += 1
            logger.warning(f"Connection invalidated in pool '{pool_name}': {exception}")
    
    def get_pool_statistics(self, pool_name: str = "default") -> Dict[str, Any]:
        """Get statistics for a connection pool"""
        with self._lock:
            if pool_name not in self.pools:
                return {"error": f"Pool '{pool_name}' not found"}
            
            engine = self.pools[pool_name]
            pool = engine.pool
            metrics = self.metrics[pool_name].copy()
            
            # Calculate average checkout time
            checkout_times = metrics.get("checkout_time", [])
            if checkout_times:
                metrics["avg_checkout_time"] = sum(checkout_times) / len(checkout_times)
                metrics["max_checkout_time"] = max(checkout_times)
                metrics["min_checkout_time"] = min(checkout_times)
            
            # Get current pool status
            if hasattr(pool, 'size'):
                metrics["current_size"] = pool.size()
                metrics["current_overflow"] = pool.overflow()
                metrics["current_checked_out"] = pool.checkedout()
            
            # Calculate pool efficiency
            total_checkouts = len(checkout_times)
            if total_checkouts > 0:
                metrics["pool_efficiency"] = (
                    1 - (metrics["connections_created"] / total_checkouts)
                ) * 100
            
            return metrics
    
    def optimize_pool(self, pool_name: str = "default"):
        """Dynamically optimize pool settings based on usage patterns"""
        stats = self.get_pool_statistics(pool_name)
        
        if "error" in stats:
            return
        
        engine = self.pools[pool_name]
        pool = engine.pool
        
        # Check if pool size needs adjustment
        avg_active = stats.get("active_connections", 0)
        pool_size = stats.get("pool_size", 5)
        
        if avg_active > pool_size * 0.8:
            # Pool is frequently near capacity, consider increasing
            logger.info(f"Pool '{pool_name}' running near capacity, consider increasing pool_size")
            
        elif avg_active < pool_size * 0.2:
            # Pool is oversized, consider decreasing
            logger.info(f"Pool '{pool_name}' is oversized, consider decreasing pool_size")
        
        # Check for connection leaks
        avg_checkout_time = stats.get("avg_checkout_time", 0)
        if avg_checkout_time > 5.0:  # 5 seconds average is concerning
            logger.warning(
                f"Pool '{pool_name}' has high average checkout time: {avg_checkout_time:.2f}s. "
                "Possible connection leak or slow queries."
            )
    
    @contextmanager
    def get_db_session(self, pool_name: str = "default") -> Session:
        """
        Get a database session with automatic cleanup.
        
        Args:
            pool_name: Name of the connection pool to use
            
        Yields:
            Database session
        """
        if pool_name not in self.pools:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        engine = self.pools[pool_name]
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        
        session = SessionLocal()
        try:
            yield session
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error in session: {e}")
            raise
        finally:
            session.close()
    
    def close_all_pools(self):
        """Close all connection pools"""
        with self._lock:
            for pool_name, engine in self.pools.items():
                try:
                    engine.dispose()
                    logger.info(f"Closed connection pool '{pool_name}'")
                except Exception as e:
                    logger.error(f"Error closing pool '{pool_name}': {e}")
            
            self.pools.clear()
            self.metrics.clear()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all connection pools"""
        health = {
            "status": "healthy",
            "pools": {}
        }
        
        with self._lock:
            for pool_name, engine in self.pools.items():
                try:
                    # Test connection
                    with engine.connect() as conn:
                        conn.execute("SELECT 1")
                    
                    pool_health = {
                        "status": "healthy",
                        "stats": self.get_pool_statistics(pool_name)
                    }
                except Exception as e:
                    pool_health = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health["status"] = "degraded"
                
                health["pools"][pool_name] = pool_health
        
        return health


# Global connection pool manager
pool_manager = ConnectionPoolManager()


# Utility functions
def get_optimized_db_engine(database_url: Optional[str] = None) -> Any:
    """Get an optimized database engine"""
    if database_url is None:
        database_url = settings.DATABASE_URL
    
    return pool_manager.create_optimized_engine(database_url)


def get_db() -> Session:
    """Dependency for FastAPI to get database session"""
    with pool_manager.get_db_session() as session:
        yield session


# Connection pool monitoring endpoint data
def get_connection_pool_metrics() -> Dict[str, Any]:
    """Get metrics for all connection pools"""
    metrics = {
        "pools": {},
        "summary": {
            "total_connections": 0,
            "active_connections": 0,
            "pool_efficiency": 0
        }
    }
    
    efficiencies = []
    
    for pool_name in pool_manager.pools:
        pool_stats = pool_manager.get_pool_statistics(pool_name)
        metrics["pools"][pool_name] = pool_stats
        
        # Update summary
        metrics["summary"]["total_connections"] += pool_stats.get("connections_created", 0)
        metrics["summary"]["active_connections"] += pool_stats.get("active_connections", 0)
        
        if "pool_efficiency" in pool_stats:
            efficiencies.append(pool_stats["pool_efficiency"])
    
    # Calculate average efficiency
    if efficiencies:
        metrics["summary"]["pool_efficiency"] = sum(efficiencies) / len(efficiencies)
    
    return metrics