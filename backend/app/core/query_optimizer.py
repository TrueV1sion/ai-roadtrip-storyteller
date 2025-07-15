"""
Database query optimization utilities
"""

from typing import List, Optional, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload, Session
from sqlalchemy.sql import Select
import logging

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Optimize database queries for performance"""
    
    @staticmethod
    def optimize_n_plus_one(query: Select, relationships: List[str]) -> Select:
        """Fix N+1 query problems with eager loading"""
        for relationship in relationships:
            if "." in relationship:
                # Handle nested relationships
                query = query.options(selectinload(relationship))
            else:
                # Handle direct relationships
                query = query.options(joinedload(relationship))
        
        return query
    
    @staticmethod
    def add_pagination(query: Select, page: int = 1, per_page: int = 20) -> Select:
        """Add efficient pagination to queries"""
        offset = (page - 1) * per_page
        return query.limit(per_page).offset(offset)
    
    @staticmethod
    def optimize_booking_search(
        session: Session,
        location: str,
        date_range: tuple,
        preferences: dict
    ) -> List[Any]:
        """Optimized booking search with batching"""
        # Use single query with joins instead of multiple queries
        query = (
            select(Booking)
            .join(Hotel)
            .join(Location)
            .options(
                selectinload(Booking.hotel),
                selectinload(Booking.amenities),
                selectinload(Booking.reviews)
            )
            .where(
                and_(
                    Location.city == location,
                    Booking.available_date.between(*date_range),
                    Booking.price <= preferences.get("max_price", float("inf"))
                )
            )
        )
        
        # Add preference filters
        if preferences.get("amenities"):
            query = query.join(Amenity).where(
                Amenity.name.in_(preferences["amenities"])
            )
        
        return session.execute(query).scalars().all()
    
    @staticmethod
    def optimize_trip_history(
        session: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Any]:
        """Optimized trip history query"""
        return (
            session.execute(
                select(Trip)
                .options(
                    selectinload(Trip.stories),
                    selectinload(Trip.bookings),
                    selectinload(Trip.route_points)
                )
                .where(Trip.user_id == user_id)
                .order_by(Trip.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    
    @staticmethod
    def create_indexes_script() -> str:
        """Generate SQL script for missing indexes"""
        return """
-- Performance optimization indexes
CREATE INDEX CONCURRENTLY idx_trips_user_id_created ON trips(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_stories_trip_id ON stories(trip_id);
CREATE INDEX CONCURRENTLY idx_bookings_location_date ON bookings(location_id, available_date);
CREATE INDEX CONCURRENTLY idx_voice_responses_hash ON voice_responses(request_hash);
CREATE INDEX CONCURRENTLY idx_navigation_routes_key ON navigation_routes(route_key);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_trips_active ON trips(user_id) WHERE status = 'active';
CREATE INDEX CONCURRENTLY idx_bookings_available ON bookings(hotel_id, available_date) WHERE is_available = true;
"""


# Query optimization middleware
class QueryOptimizationMiddleware:
    """Automatically optimize queries"""
    
    def __init__(self, app):
        self.app = app
        self._install_hooks()
    
    def _install_hooks(self):
        """Install query optimization hooks"""
        # This would hook into SQLAlchemy to automatically
        # optimize queries before execution
        pass
