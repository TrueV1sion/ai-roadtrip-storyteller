"""
Database Query Optimization Module

Provides comprehensive query optimization strategies, indexes, and monitoring.
"""

import time
import functools
from typing import Dict, List, Any, Optional, Callable, Type, TypeVar
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, Index, text, and_, or_
from sqlalchemy.orm import Session, Query, selectinload, joinedload, subqueryload, contains_eager
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.models import User, Story, Theme, SideQuest, Reservation


T = TypeVar('T')


class QueryOptimizationStrategies:
    """Core query optimization strategies for the application."""
    
    @staticmethod
    def optimize_story_queries(query: Query) -> Query:
        """
        Optimize story-related queries with proper eager loading.
        
        Common access patterns:
        - Stories with themes
        - Stories with side quests
        - Stories with user preferences
        """
        # Eager load commonly accessed relationships
        return query.options(
            selectinload('themes'),
            selectinload('side_quests'),
            selectinload('user')
        )
    
    @staticmethod
    def optimize_user_queries(query: Query) -> Query:
        """
        Optimize user-related queries.
        
        Common access patterns:
        - User with preferences
        - User with recent stories
        - User with reservations
        """
        return query.options(
            selectinload('preferences'),
            selectinload('stories').limit(10),  # Recent stories only
            selectinload('reservations').filter(
                Reservation.status.in_(['confirmed', 'pending'])
            )
        )
    
    @staticmethod
    def optimize_reservation_queries(query: Query) -> Query:
        """
        Optimize reservation queries.
        
        Common patterns:
        - Reservations with user info
        - Reservations with commission data
        - Active reservations only
        """
        return query.options(
            joinedload('user'),  # Join for single query
            selectinload('commission')  # Separate query for 1-to-1
        )
    
    @staticmethod
    def optimize_location_based_queries(
        query: Query,
        latitude: float,
        longitude: float,
        radius_miles: float = 10.0
    ) -> Query:
        """
        Optimize location-based queries using spatial indexes.
        
        Args:
            query: Base query
            latitude: Center latitude
            longitude: Center longitude
            radius_miles: Search radius in miles
            
        Returns:
            Optimized query with spatial filtering
        """
        # Convert miles to degrees (approximate)
        degree_radius = radius_miles / 69.0
        
        # Use bounding box for initial filtering (uses indexes)
        return query.filter(
            and_(
                text("latitude BETWEEN :lat_min AND :lat_max"),
                text("longitude BETWEEN :lon_min AND :lon_max")
            )
        ).params(
            lat_min=latitude - degree_radius,
            lat_max=latitude + degree_radius,
            lon_min=longitude - degree_radius,
            lon_max=longitude + degree_radius
        )


class QueryCache:
    """Advanced query result caching with TTL and invalidation."""
    
    def __init__(self, default_ttl: int = 300):
        """Initialize query cache with default TTL in seconds."""
        self.default_ttl = default_ttl
        self._invalidation_patterns = {}
    
    def cache_result(self, ttl: Optional[int] = None):
        """
        Decorator to cache query results with TTL.
        
        Args:
            ttl: Time to live in seconds (uses default if not specified)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(func.__name__, args, kwargs)
                
                # Try to get from cache
                cached = await cache_manager.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached
                
                # Execute query
                result = await func(*args, **kwargs)
                
                # Cache result
                cache_ttl = ttl or self.default_ttl
                await cache_manager.setex(cache_key, cache_ttl, result)
                
                return result
            
            # Add invalidation method
            wrapper.invalidate_cache = lambda: self._invalidate_pattern(func.__name__)
            
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate a unique cache key for the query."""
        # Create a stable string representation
        key_parts = [
            f"query:{func_name}",
            str(hash(args)),
            str(hash(frozenset(kwargs.items())))
        ]
        return ":".join(key_parts)
    
    async def _invalidate_pattern(self, pattern: str):
        """Invalidate all cache entries matching a pattern."""
        # This would use Redis SCAN in production
        logger.info(f"Invalidating cache pattern: {pattern}")


class DatabaseIndexOptimizer:
    """Manages database indexes for optimal query performance."""
    
    # Define critical indexes for the application
    INDEXES = [
        # User indexes
        Index('idx_user_email', User.email),
        Index('idx_user_created', User.created_at),
        
        # Story indexes
        Index('idx_story_user', Story.user_id),
        Index('idx_story_created', Story.created_at),
        Index('idx_story_location', Story.origin_lat, Story.origin_lng),
        
        # Theme indexes
        Index('idx_theme_name', Theme.name),
        Index('idx_theme_active', Theme.is_active),
        
        # Reservation indexes
        Index('idx_reservation_user', Reservation.user_id),
        Index('idx_reservation_status', Reservation.status),
        Index('idx_reservation_date', Reservation.reservation_date),
        Index('idx_reservation_composite', Reservation.user_id, Reservation.status, Reservation.reservation_date),
        
        # Side quest indexes
        Index('idx_sidequest_story', SideQuest.story_id),
        Index('idx_sidequest_location', SideQuest.latitude, SideQuest.longitude),
    ]
    
    @classmethod
    def create_indexes(cls, engine: Engine):
        """Create all defined indexes if they don't exist."""
        for index in cls.INDEXES:
            try:
                index.create(engine, checkfirst=True)
                logger.info(f"Created index: {index.name}")
            except Exception as e:
                logger.error(f"Failed to create index {index.name}: {e}")
    
    @classmethod
    def analyze_tables(cls, db: Session):
        """Run ANALYZE on tables to update query planner statistics."""
        tables = ['users', 'stories', 'themes', 'reservations', 'side_quests']
        
        for table in tables:
            try:
                db.execute(text(f"ANALYZE {table}"))
                logger.info(f"Analyzed table: {table}")
            except Exception as e:
                logger.error(f"Failed to analyze table {table}: {e}")


class QueryPerformanceMonitor:
    """Monitor and log query performance metrics."""
    
    def __init__(self):
        self.slow_query_threshold = 0.1  # 100ms
        self.query_stats = {}
    
    def monitor_query(self, query_name: str):
        """
        Decorator to monitor query performance.
        
        Args:
            query_name: Name to identify the query in logs
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Update statistics
                    self._update_stats(query_name, execution_time)
                    
                    # Log slow queries
                    if execution_time > self.slow_query_threshold:
                        logger.warning(
                            f"Slow query '{query_name}' executed in {execution_time:.3f}s"
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    logger.error(
                        f"Query '{query_name}' failed after {execution_time:.3f}s: {e}"
                    )
                    raise
            
            return wrapper
        return decorator
    
    def _update_stats(self, query_name: str, execution_time: float):
        """Update query statistics."""
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        stats = self.query_stats[query_name]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['min_time'] = min(stats['min_time'], execution_time)
        stats['max_time'] = max(stats['max_time'], execution_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        summary = {}
        
        for query_name, stats in self.query_stats.items():
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            
            summary[query_name] = {
                'count': stats['count'],
                'avg_time': round(avg_time, 3),
                'min_time': round(stats['min_time'], 3),
                'max_time': round(stats['max_time'], 3),
                'total_time': round(stats['total_time'], 3)
            }
        
        return summary


class OptimizedQueries:
    """Collection of optimized queries for common operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = QueryCache()
        self.monitor = QueryPerformanceMonitor()
    
    @QueryPerformanceMonitor().monitor_query("get_user_with_preferences")
    def get_user_with_preferences(self, user_id: int) -> Optional[User]:
        """Get user with all preferences eagerly loaded."""
        return self.db.query(User).options(
            selectinload(User.preferences),
            selectinload(User.themes).selectinload(Theme.keywords)
        ).filter(User.id == user_id).first()
    
    @QueryPerformanceMonitor().monitor_query("get_recent_stories_for_route")
    def get_recent_stories_for_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        limit: int = 10
    ) -> List[Story]:
        """Get recent stories for a route with optimized spatial query."""
        # Calculate bounding box
        lat_min = min(origin_lat, dest_lat) - 0.1
        lat_max = max(origin_lat, dest_lat) + 0.1
        lng_min = min(origin_lng, dest_lng) - 0.1
        lng_max = max(origin_lng, dest_lng) + 0.1
        
        return self.db.query(Story).options(
            selectinload(Story.themes),
            selectinload(Story.side_quests)
        ).filter(
            and_(
                Story.origin_lat.between(lat_min, lat_max),
                Story.origin_lng.between(lng_min, lng_max)
            )
        ).order_by(
            Story.created_at.desc()
        ).limit(limit).all()
    
    @QueryPerformanceMonitor().monitor_query("get_active_reservations")
    def get_active_reservations(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Reservation]:
        """Get active reservations with optimized filtering."""
        query = self.db.query(Reservation).options(
            joinedload(Reservation.user),
            selectinload(Reservation.commission)
        ).filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(['confirmed', 'pending'])
        )
        
        if start_date:
            query = query.filter(Reservation.reservation_date >= start_date)
        
        if end_date:
            query = query.filter(Reservation.reservation_date <= end_date)
        
        return query.order_by(Reservation.reservation_date).all()
    
    @QueryPerformanceMonitor().monitor_query("search_nearby_sidequests")
    def search_nearby_sidequests(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 5.0,
        limit: int = 20
    ) -> List[SideQuest]:
        """Search for nearby side quests using spatial optimization."""
        # Use Haversine formula approximation
        degree_radius = radius_miles / 69.0
        
        # First filter by bounding box (uses indexes)
        nearby_quests = self.db.query(SideQuest).filter(
            and_(
                SideQuest.latitude.between(
                    latitude - degree_radius,
                    latitude + degree_radius
                ),
                SideQuest.longitude.between(
                    longitude - degree_radius,
                    longitude + degree_radius
                ),
                SideQuest.is_active == True
            )
        ).options(
            selectinload(SideQuest.story).selectinload(Story.themes)
        ).limit(limit * 2).all()  # Get extra for distance filtering
        
        # Then calculate actual distances and sort
        results = []
        for quest in nearby_quests:
            # Simple distance calculation
            dist = ((quest.latitude - latitude) ** 2 + 
                   (quest.longitude - longitude) ** 2) ** 0.5 * 69
            
            if dist <= radius_miles:
                quest.distance = dist
                results.append(quest)
        
        # Sort by distance and return limited results
        results.sort(key=lambda q: q.distance)
        return results[:limit]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get query performance report."""
        return {
            'query_stats': self.monitor.get_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global instances
query_cache = QueryCache()
performance_monitor = QueryPerformanceMonitor()
index_optimizer = DatabaseIndexOptimizer()