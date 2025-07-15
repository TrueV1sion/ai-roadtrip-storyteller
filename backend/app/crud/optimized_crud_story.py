from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, text
import time
from datetime import datetime, timedelta

from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate
from app.crud.optimized_crud_base import CRUDOptimizedBase
from app.core.logger import get_logger

logger = get_logger(__name__)


class CRUDOptimizedStory(CRUDOptimizedBase[Story, StoryCreate, StoryUpdate]):
    """Optimized CRUD operations for the Story model."""
    
    def get_with_user(self, db: Session, story_id: str) -> Optional[Story]:
        """
        Get a story by ID with preloaded user relationship.
        
        Args:
            db: Database session
            story_id: Story ID
            
        Returns:
            Story with user preloaded or None
        """
        start_time = time.time()
        
        story = (
            db.query(Story)
            .options(joinedload(Story.user))  # Eagerly load the user relationship
            .filter(Story.id == story_id)
            .first()
        )
        
        query_time = time.time() - start_time
        if query_time > 0.1:
            logger.warning(f"Slow get_with_user query for story {story_id}: {query_time:.4f}s")
            
        return story
    
    def get_by_location(
        self,
        db: Session,
        *,
        latitude: float,
        longitude: float,
        radius_km: float = 1.0,
        limit: int = 10
    ) -> List[Story]:
        """
        Get stories near a specific location.
        
        Args:
            db: Database session
            latitude: Location latitude
            longitude: Location longitude
            radius_km: Search radius in kilometers
            limit: Maximum number of stories to return
            
        Returns:
            List of nearby stories
        """
        start_time = time.time()
        
        # Haversine formula as SQL expression
        # This calculates the great-circle distance between two points on a sphere
        # We use the raw SQL query for performance with spatial queries
        query = text("""
            SELECT 
                id,
                latitude,
                longitude,
                location_name,
                title,
                (
                    6371 * acos(
                        cos(radians(:lat)) * 
                        cos(radians(latitude)) * 
                        cos(radians(longitude) - radians(:lng)) + 
                        sin(radians(:lat)) * 
                        sin(radians(latitude))
                    )
                ) AS distance
            FROM stories
            WHERE (
                6371 * acos(
                    cos(radians(:lat)) * 
                    cos(radians(latitude)) * 
                    cos(radians(longitude) - radians(:lng)) + 
                    sin(radians(:lat)) * 
                    sin(radians(latitude))
                )
            ) < :radius
            ORDER BY distance
            LIMIT :limit
        """)
        
        # Execute the raw SQL query with parameters
        result = db.execute(
            query, 
            {
                "lat": latitude,
                "lng": longitude,
                "radius": radius_km,
                "limit": limit
            }
        )
        
        # Convert to list of dicts
        nearby_stories = [dict(row) for row in result]
        
        # Now get the full Story objects for the found IDs
        if nearby_stories:
            story_ids = [story["id"] for story in nearby_stories]
            stories = (
                db.query(Story)
                .filter(Story.id.in_(story_ids))
                .all()
            )
            
            # Sort by the original distance order
            id_to_distance = {story["id"]: story["distance"] for story in nearby_stories}
            stories.sort(key=lambda s: id_to_distance.get(s.id, float('inf')))
        else:
            stories = []
            
        query_time = time.time() - start_time
        if query_time > 0.2:
            logger.warning(f"Slow get_by_location query: {query_time:.4f}s")
            
        return stories
    
    def get_popular_stories(
        self,
        db: Session,
        *,
        days: int = 7,
        limit: int = 10
    ) -> List[Story]:
        """
        Get popular stories based on play count and rating.
        
        Args:
            db: Database session
            days: Number of days to consider
            limit: Maximum number of stories to return
            
        Returns:
            List of popular stories
        """
        start_time = time.time()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Query stories with a popularity score (play_count + rating*5)
        stories = (
            db.query(Story)
            .filter(Story.created_at >= cutoff_date)
            .filter(Story.play_count > 0)  # Only include stories that have been played
            .order_by(
                desc(Story.play_count + func.coalesce(Story.rating, 0) * 5)
            )
            .limit(limit)
            .all()
        )
        
        query_time = time.time() - start_time
        if query_time > 0.2:
            logger.warning(f"Slow get_popular_stories query: {query_time:.4f}s")
            
        return stories
    
    def get_stories_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        include_favorites_only: bool = False
    ) -> Tuple[List[Story], int]:
        """
        Get stories created by a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of stories to skip
            limit: Maximum number of stories to return
            include_favorites_only: Include only favorite stories
            
        Returns:
            Tuple of (stories, total_count)
        """
        start_time = time.time()
        
        # Base query
        query = db.query(Story).filter(Story.user_id == user_id)
        
        # Apply favorites filter if requested
        if include_favorites_only:
            query = query.filter(Story.is_favorite == True)
            
        # Get total count
        total = query.count()
        
        # Get paginated results
        stories = (
            query
            .order_by(Story.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        query_time = time.time() - start_time
        if query_time > 0.2:
            logger.warning(f"Slow get_stories_by_user query: {query_time:.4f}s")
            
        return stories, total
    
    def increment_play_count(self, db: Session, *, story_id: str) -> Optional[Story]:
        """
        Increment the play count for a story.
        
        Args:
            db: Database session
            story_id: Story ID
            
        Returns:
            Updated story or None if not found
        """
        # Use direct SQL update for efficiency
        query = text("""
            UPDATE stories 
            SET play_count = play_count + 1, 
                updated_at = NOW() 
            WHERE id = :story_id 
            RETURNING *
        """)
        
        start_time = time.time()
        
        try:
            result = db.execute(query, {"story_id": story_id})
            db.commit()
            
            # Get the updated story
            story = None
            for row in result:
                story = Story(**dict(row))
                break
                
            query_time = time.time() - start_time
            if query_time > 0.1:
                logger.warning(f"Slow increment_play_count query for story {story_id}: {query_time:.4f}s")
                
            return story
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in increment_play_count: {str(e)}")
            return None
    
    def search_stories(
        self,
        db: Session,
        *,
        query: str,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Story], int]:
        """
        Search stories by text content, title, or location.
        
        Args:
            db: Database session
            query: Search query text
            user_id: Optional user ID to filter by
            skip: Number of stories to skip
            limit: Maximum number of stories to return
            
        Returns:
            Tuple of (matching_stories, total_count)
        """
        start_time = time.time()
        
        # Convert query to lowercase for case-insensitive search
        search_term = f"%{query.lower()}%"
        
        # Base search query
        search_query = (
            db.query(Story)
            .filter(
                # Search in multiple fields
                (func.lower(Story.title).like(search_term)) |
                (func.lower(Story.content).like(search_term)) |
                (func.lower(Story.location_name).like(search_term))
            )
        )
        
        # Apply user filter if provided
        if user_id:
            search_query = search_query.filter(Story.user_id == user_id)
            
        # Get total count
        total = search_query.count()
        
        # Get paginated results
        stories = (
            search_query
            .order_by(Story.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        query_time = time.time() - start_time
        if query_time > 0.3:  # Higher threshold for search operations
            logger.warning(f"Slow search_stories query: {query_time:.4f}s")
            
        return stories, total
    
    def update_completion_rate(
        self,
        db: Session,
        *,
        story_id: str,
        completion_rate: float
    ) -> Optional[Story]:
        """
        Update the completion rate for a story.
        
        Args:
            db: Database session
            story_id: Story ID
            completion_rate: New completion rate (0.0 to 1.0)
            
        Returns:
            Updated story or None if not found
        """
        start_time = time.time()
        
        # Find the story
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return None
            
        # Update completion rate if the new value is higher
        if story.completion_rate is None or completion_rate > story.completion_rate:
            story.completion_rate = completion_rate
            story.updated_at = func.now()
            
            db.add(story)
            db.commit()
            db.refresh(story)
            
        query_time = time.time() - start_time
        if query_time > 0.1:
            logger.warning(f"Slow update_completion_rate query for story {story_id}: {query_time:.4f}s")
            
        return story
    
    def bulk_update_favorites(
        self,
        db: Session,
        *,
        user_id: str,
        story_ids: List[str],
        is_favorite: bool
    ) -> int:
        """
        Update favorite status for multiple stories at once.
        
        Args:
            db: Database session
            user_id: User ID (for authorization)
            story_ids: List of story IDs to update
            is_favorite: New favorite status
            
        Returns:
            Number of stories updated
        """
        if not story_ids:
            return 0
            
        start_time = time.time()
        
        # Update multiple stories at once
        query = text("""
            UPDATE stories 
            SET is_favorite = :favorite,
                updated_at = NOW()
            WHERE id IN :story_ids
              AND user_id = :user_id
        """)
        
        try:
            result = db.execute(
                query, 
                {
                    "favorite": is_favorite,
                    "story_ids": tuple(story_ids),
                    "user_id": user_id
                }
            )
            db.commit()
            
            updated_count = result.rowcount
            
            query_time = time.time() - start_time
            if query_time > 0.2:
                logger.warning(f"Slow bulk_update_favorites query: {query_time:.4f}s")
                
            return updated_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in bulk_update_favorites: {str(e)}")
            return 0


# Create singleton instance
story_crud = CRUDOptimizedStory(Story)