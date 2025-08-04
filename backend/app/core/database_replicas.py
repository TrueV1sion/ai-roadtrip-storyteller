"""
Database configuration with read replicas and data warehouse architecture.

This module provides:
- Read replica routing for query load distribution
- Write/read split for performance
- Data warehouse connections for analytics
- Automatic failover handling
"""

import random
from typing import Dict, List, Optional, Any, Callable
from contextlib import contextmanager
from enum import Enum

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.core.logger import get_logger
from app.core.tracing import trace_method, add_span_attributes

logger = get_logger(__name__)


class DatabaseRole(str, Enum):
    """Database instance roles."""
    PRIMARY = "primary"
    REPLICA = "replica"
    ANALYTICS = "analytics"


class ReplicaRouter:
    """
    Routes database queries to appropriate instances based on operation type.
    
    Features:
    - Automatic read/write splitting
    - Load balancing across replicas
    - Health checking and failover
    - Analytics workload isolation
    """
    
    def __init__(self):
        self.engines: Dict[DatabaseRole, List[Engine]] = {
            DatabaseRole.PRIMARY: [],
            DatabaseRole.REPLICA: [],
            DatabaseRole.ANALYTICS: []
        }
        self._health_status: Dict[str, bool] = {}
        self._init_engines()
    
    def _init_engines(self):
        """Initialize database engines for all instances."""
        
        # Primary database (writes)
        primary_url = settings.DATABASE_URL
        primary_engine = create_engine(
            primary_url,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG,
            connect_args={
                "application_name": "roadtrip_api_primary",
                "options": "-c default_transaction_isolation='read committed'"
            }
        )
        self.engines[DatabaseRole.PRIMARY] = [primary_engine]
        self._health_status[primary_url] = True
        
        # Read replicas
        replica_urls = settings.DATABASE_READ_REPLICAS or []
        for i, replica_url in enumerate(replica_urls):
            replica_engine = create_engine(
                replica_url,
                pool_size=30,  # More connections for read workload
                max_overflow=60,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
                connect_args={
                    "application_name": f"roadtrip_api_replica_{i}",
                    "options": "-c default_transaction_isolation='read committed'"
                }
            )
            self.engines[DatabaseRole.REPLICA].append(replica_engine)
            self._health_status[replica_url] = True
        
        # Analytics database (data warehouse)
        if settings.DATABASE_ANALYTICS_URL:
            analytics_engine = create_engine(
                settings.DATABASE_ANALYTICS_URL,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=7200,  # Longer recycle for analytics
                echo=False,
                poolclass=NullPool,  # No connection pooling for analytics
                connect_args={
                    "application_name": "roadtrip_analytics",
                    "options": "-c statement_timeout=300000"  # 5 minute timeout
                }
            )
            self.engines[DatabaseRole.ANALYTICS] = [analytics_engine]
            self._health_status[settings.DATABASE_ANALYTICS_URL] = True
        
        # Set up event listeners for monitoring
        for role, engines in self.engines.items():
            for engine in engines:
                self._setup_engine_events(engine, role)
    
    def _setup_engine_events(self, engine: Engine, role: DatabaseRole):
        """Set up SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault("query_start_time", []).append(time.time())
            add_span_attributes({
                "db.role": role.value,
                "db.statement": statement[:100],  # First 100 chars
                "db.engine": str(engine.url)
            })
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info["query_start_time"].pop(-1)
            logger.debug(
                f"Query executed on {role.value}",
                extra={
                    "duration_ms": total * 1000,
                    "role": role.value,
                    "statement_preview": statement[:50]
                }
            )
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            logger.error(
                f"Database error on {role.value}",
                extra={
                    "role": role.value,
                    "engine": str(engine.url),
                    "error": str(exception_context.original_exception)
                }
            )
            # Mark engine as unhealthy
            self._health_status[str(engine.url)] = False
    
    @trace_method(name="db.get_engine")
    def get_engine(self, role: DatabaseRole = DatabaseRole.PRIMARY) -> Engine:
        """
        Get an engine based on role with health checking.
        
        Args:
            role: The database role (primary, replica, analytics)
            
        Returns:
            A healthy database engine
            
        Raises:
            RuntimeError: If no healthy engines available
        """
        engines = self.engines.get(role, [])
        
        # Filter healthy engines
        healthy_engines = [
            engine for engine in engines
            if self._health_status.get(str(engine.url), False)
        ]
        
        if not healthy_engines:
            # Fallback to primary if no healthy replicas
            if role == DatabaseRole.REPLICA and self.engines[DatabaseRole.PRIMARY]:
                logger.warning("No healthy replicas, falling back to primary")
                return self.get_engine(DatabaseRole.PRIMARY)
            
            raise RuntimeError(f"No healthy {role.value} database engines available")
        
        # Load balance across healthy engines
        selected_engine = random.choice(healthy_engines)
        
        add_span_attributes({
            "db.selected_role": role.value,
            "db.selected_engine": str(selected_engine.url),
            "db.healthy_count": len(healthy_engines)
        })
        
        return selected_engine
    
    def check_health(self):
        """Check health of all database engines."""
        for role, engines in self.engines.items():
            for engine in engines:
                try:
                    # Simple health check query
                    with engine.connect() as conn:
                        conn.execute("SELECT 1")
                    self._health_status[str(engine.url)] = True
                except Exception as e:
                    logger.error(f"Health check failed for {engine.url}: {str(e)}")
                    self._health_status[str(engine.url)] = False
    
    @contextmanager
    def get_session(
        self,
        role: DatabaseRole = DatabaseRole.PRIMARY,
        **kwargs
    ) -> Session:
        """
        Get a database session with automatic routing.
        
        Args:
            role: Database role for this session
            **kwargs: Additional session options
            
        Yields:
            Database session
        """
        engine = self.get_engine(role)
        SessionClass = sessionmaker(bind=engine, **kwargs)
        session = SessionClass()
        
        try:
            yield session
            if role == DatabaseRole.PRIMARY:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class ReadWriteSplitter:
    """
    Middleware for automatic read/write splitting.
    
    This class intercepts queries and routes them to appropriate
    database instances based on the operation type.
    """
    
    def __init__(self, router: ReplicaRouter):
        self.router = router
    
    @contextmanager
    def session(self, readonly: bool = False, analytics: bool = False):
        """
        Get a session with automatic routing based on operation type.
        
        Args:
            readonly: If True, route to read replica
            analytics: If True, route to analytics database
            
        Yields:
            Routed database session
        """
        if analytics:
            role = DatabaseRole.ANALYTICS
        elif readonly:
            role = DatabaseRole.REPLICA
        else:
            role = DatabaseRole.PRIMARY
        
        with self.router.get_session(role=role) as session:
            yield session
    
    def execute_read(self, query_func: Callable, *args, **kwargs):
        """Execute a read query on a replica."""
        with self.session(readonly=True) as session:
            return query_func(session, *args, **kwargs)
    
    def execute_write(self, query_func: Callable, *args, **kwargs):
        """Execute a write query on the primary."""
        with self.session(readonly=False) as session:
            return query_func(session, *args, **kwargs)
    
    def execute_analytics(self, query_func: Callable, *args, **kwargs):
        """Execute an analytics query on the data warehouse."""
        with self.session(analytics=True) as session:
            return query_func(session, *args, **kwargs)


class OptimizedDatabaseManager:
    """
    Enhanced database manager with read replica support.
    
    This replaces the standard DatabaseManager with replica-aware
    connection management.
    """
    
    def __init__(self):
        self.router = ReplicaRouter()
        self.splitter = ReadWriteSplitter(self.router)
        
        # Start health checking
        self._start_health_checks()
    
    def _start_health_checks(self):
        """Start periodic health checks for all databases."""
        import threading
        import time
        
        def health_check_loop():
            while True:
                try:
                    self.router.check_health()
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                time.sleep(30)  # Check every 30 seconds
        
        thread = threading.Thread(target=health_check_loop, daemon=True)
        thread.start()
    
    @contextmanager
    def read_session(self) -> Session:
        """Get a read-only session (uses replicas)."""
        with self.splitter.session(readonly=True) as session:
            yield session
    
    @contextmanager
    def write_session(self) -> Session:
        """Get a write session (uses primary)."""
        with self.splitter.session(readonly=False) as session:
            yield session
    
    @contextmanager
    def analytics_session(self) -> Session:
        """Get an analytics session (uses data warehouse)."""
        with self.splitter.session(analytics=True) as session:
            yield session
    
    def execute_read_query(self, query: Query) -> List[Any]:
        """Execute a query on read replicas."""
        with self.read_session() as session:
            return query.with_session(session).all()
    
    def execute_analytics_query(self, query: Query) -> List[Any]:
        """Execute a query on analytics database."""
        with self.analytics_session() as session:
            return query.with_session(session).all()


# Global instance
db_manager = OptimizedDatabaseManager()


# Example usage in services
class OptimizedStoryService:
    """Example service using read replicas."""
    
    def get_stories_for_route(self, origin: str, destination: str) -> List[Dict]:
        """Get stories using read replica."""
        def query_func(session):
            # This query goes to a read replica
            return session.query(Story).filter_by(
                origin=origin,
                destination=destination
            ).all()
        
        return db_manager.splitter.execute_read(query_func)
    
    def create_story(self, story_data: Dict) -> Dict:
        """Create story using primary database."""
        def query_func(session):
            # This query goes to primary
            story = Story(**story_data)
            session.add(story)
            session.flush()
            return story
        
        return db_manager.splitter.execute_write(query_func)
    
    def get_story_analytics(self, date_range: Dict) -> List[Dict]:
        """Get analytics using data warehouse."""
        def query_func(session):
            # Complex analytics query goes to data warehouse
            return session.execute("""
                SELECT 
                    DATE_TRUNC('day', created_at) as day,
                    theme,
                    COUNT(*) as story_count,
                    AVG(duration_seconds) as avg_duration
                FROM stories
                WHERE created_at BETWEEN :start_date AND :end_date
                GROUP BY 1, 2
                ORDER BY 1, 2
            """, date_range).fetchall()
        
        return db_manager.splitter.execute_analytics(query_func)


import time  # Import at module level