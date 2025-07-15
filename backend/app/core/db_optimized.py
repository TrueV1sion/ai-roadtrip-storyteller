from typing import Dict, List, Any, Optional, Callable, Generator, Type, TypeVar
import time
import logging
import functools
import contextlib
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

# Configure optimized connection pool
optimized_engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=settings.SQL_ECHO if hasattr(settings, 'SQL_ECHO') else False
)

# Create SessionLocal class with optimized settings
OptimizedSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=optimized_engine
)

# Create Base class
OptimizedBase = declarative_base()

# Add event listeners for query performance monitoring
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Store execution start time in context
    context._query_start_time = time.time()
    
    # Log the query if debug logging is enabled
    if logger.isEnabledFor(logging.DEBUG):
        # Security: Don't log parameters which may contain sensitive data
        logger.debug(f"Executing query type: {statement.split()[0] if statement else 'Unknown'}")

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Calculate query execution time
    total_time = time.time() - context._query_start_time
    
    # Log slow queries (more than 100ms)
    if total_time > 0.1:
        logger.warning(f"Slow query detected ({total_time:.4f}s): {statement}")
        logger.warning(f"Parameters: {parameters}")
    elif logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Query executed in {total_time:.4f}s")


def get_optimized_db() -> Generator[Session, None, None]:
    """
    Get a database session from the optimized connection pool.
    For use with FastAPI Depends.
    """
    db = OptimizedSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    For use with 'with' statements.
    """
    db = OptimizedSessionLocal()
    try:
        yield db
    finally:
        db.close()


def with_db(func: Callable) -> Callable:
    """
    Decorator to provide a database session to a function.
    
    Example:
        @with_db
        def get_user(db, user_id):
            return db.query(User).filter(User.id == user_id).first()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_context() as db:
            return func(db, *args, **kwargs)
    return wrapper


class QueryOptimizer:
    """Utility class for optimizing database queries."""
    
    @staticmethod
    def optimize_query(query: Query) -> Query:
        """
        Apply general optimizations to a query.
        
        Args:
            query: SQLAlchemy query object
            
        Returns:
            Optimized query
        """
        # This is a placeholder for query-specific optimizations
        # In a real-world scenario, you might analyze the query and apply
        # specific optimizations based on the entities involved
        return query
    
    @staticmethod
    def with_prefetch(query: Query, *relations: str) -> Query:
        """
        Optimize a query with eager loading for specified relations.
        
        Args:
            query: SQLAlchemy query object
            relations: Relationship attributes to eagerly load
            
        Returns:
            Query with eager loading applied
        """
        for relation in relations:
            query = query.options(selectinload(relation))
        return query
    
    @staticmethod
    def paginate(query: Query, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Paginate a query result.
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Dictionary with pagination metadata and items
        """
        # Ensure valid pagination parameters
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count (without fetching all rows)
        total = query.count()
        
        # Get paginated results
        items = query.offset(offset).limit(page_size).all()
        
        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        # Return paginated result
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

    @staticmethod
    def bulk_insert(db: Session, objects: List[Any], batch_size: int = 1000) -> None:
        """
        Perform bulk insert with batching for better performance.
        
        Args:
            db: SQLAlchemy session
            objects: List of objects to insert
            batch_size: Size of each batch
        """
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            db.bulk_save_objects(batch, return_defaults=False)
            db.flush()
    
    @staticmethod
    def execute_raw_sql(db: Session, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute raw SQL for performance-critical operations.
        
        Args:
            db: SQLAlchemy session
            sql: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries with query results
        """
        result = db.execute(text(sql), params or {})
        return [dict(row) for row in result]
    
    @staticmethod
    def cache_query_result(func: Callable) -> Callable:
        """
        Decorator to cache query results.
        
        Example:
            @QueryOptimizer.cache_query_result
            def get_popular_stories(db):
                return db.query(Story).order_by(Story.views.desc()).limit(10).all()
        """
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a basic cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            if key in cache:
                return cache[key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        
        # Add method to clear the cache
        def clear_cache():
            cache.clear()
        
        wrapper.clear_cache = clear_cache
        return wrapper


def check_db_connection() -> bool:
    """
    Check database connection and report status.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


def get_db_stats() -> Dict[str, Any]:
    """
    Get database connection pool statistics.
    
    Returns:
        Dict with pool statistics
    """
    stats = {
        "pool_size": optimized_engine.pool.size(),
        "checkedin": optimized_engine.pool.checkedin(),
        "checkedout": optimized_engine.pool.checkedout(),
        "overflow": optimized_engine.pool.overflow(),
        "overflow_max": optimized_engine.pool._max_overflow
    }
    
    logger.info(f"DB Pool Stats: {stats}")
    return stats