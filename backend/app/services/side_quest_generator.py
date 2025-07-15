import math
from datetime import datetime, timedelta
import json
import random
import string
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, or_, func, desc, asc, cast, String, Float
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.database import get_db
from app.models.side_quest import SideQuest, SideQuestCategory, UserSideQuest, SideQuestStatus, SideQuestDifficulty
from app.models.user import User
from app.models.directions import Route, RouteLeg, RouteStep, Location

logger = get_logger(__name__)


class SideQuestGenerator:
    """Service for generating and managing side quests."""
    
    def __init__(self, db: Session):
        """Initialize the side quest generator with database session."""
        self.db = db
    
    async def get_side_quest(self, side_quest_id: str) -> Optional[SideQuest]:
        """
        Get a specific side quest by ID.
        
        Args:
            side_quest_id: ID of the side quest to retrieve
            
        Returns:
            SideQuest object or None if not found
        """
        try:
            side_quest = self.db.query(SideQuest).filter(SideQuest.id == side_quest_id).first()
            return side_quest
        except Exception as e:
            logger.error(f"Error retrieving side quest {side_quest_id}: {str(e)}")
            return None
    
    async def get_user_side_quest(self, user_id: str, side_quest_id: str) -> Optional[UserSideQuest]:
        """
        Get a specific user side quest by user ID and side quest ID.
        
        Args:
            user_id: ID of the user
            side_quest_id: ID of the side quest
            
        Returns:
            UserSideQuest object or None if not found
        """
        try:
            user_side_quest = self.db.query(UserSideQuest).filter(
                UserSideQuest.user_id == user_id,
                UserSideQuest.side_quest_id == side_quest_id
            ).first()
            return user_side_quest
        except Exception as e:
            logger.error(f"Error retrieving user side quest for user {user_id} and quest {side_quest_id}: {str(e)}")
            return None
    
    async def get_nearby_side_quests(
        self,
        latitude: float,
        longitude: float,
        radius: float = 10.0,  # km
        limit: int = 20,
        categories: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        max_detour_time: Optional[int] = None,
        min_uniqueness: Optional[float] = None,
        include_inactive: bool = False,
        include_seasonal: bool = True
    ) -> List[SideQuest]:
        """
        Get side quests near a location.
        
        Args:
            latitude: Latitude of the center point
            longitude: Longitude of the center point
            radius: Search radius in kilometers
            limit: Maximum number of results to return
            categories: Optional list of category IDs to filter by
            difficulty: Optional difficulty level to filter by
            max_detour_time: Maximum detour time in minutes
            min_uniqueness: Minimum uniqueness score (0-100)
            include_inactive: Include inactive side quests
            include_seasonal: Include out-of-season side quests
            
        Returns:
            List of SideQuest objects
        """
        try:
            # Base query
            query = self.db.query(SideQuest)
            
            # Filter by active status
            if not include_inactive:
                query = query.filter(SideQuest.is_active == True)
            
            # Filter by seasonal availability
            if not include_seasonal:
                current_date = datetime.utcnow()
                query = query.filter(
                    or_(
                        SideQuest.is_seasonal == False,
                        and_(
                            SideQuest.is_seasonal == True,
                            or_(
                                SideQuest.seasonal_start == None,
                                SideQuest.seasonal_start <= current_date
                            ),
                            or_(
                                SideQuest.seasonal_end == None,
                                SideQuest.seasonal_end >= current_date
                            )
                        )
                    )
                )
            
            # Filter by category
            if categories:
                query = query.filter(SideQuest.category.in_(categories))
            
            # Filter by difficulty
            if difficulty:
                query = query.filter(SideQuest.difficulty == difficulty)
            
            # Filter by detour time
            if max_detour_time is not None:
                query = query.filter(or_(
                    SideQuest.detour_time == None,
                    SideQuest.detour_time <= max_detour_time
                ))
            
            # Filter by uniqueness score
            if min_uniqueness is not None:
                query = query.filter(or_(
                    SideQuest.uniqueness_score == None,
                    SideQuest.uniqueness_score >= min_uniqueness
                ))
            
            # Use PostgreSQL's earthdistance extension to find nearby quests
            # Calculate distance in meters (earthdistance returns meters)
            distance_meters = radius * 1000
            query = query.filter(
                text(f"earth_distance(ll_to_earth({latitude}, {longitude}), ll_to_earth(latitude, longitude)) <= {distance_meters}")
            )
            
            # Add distance calculation for sorting
            query = query.add_columns(
                text(f"earth_distance(ll_to_earth({latitude}, {longitude}), ll_to_earth(latitude, longitude)) as distance")
            )
            
            # Sort by distance (closest first)
            query = query.order_by(text("distance ASC"))
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query and extract side quests
            results = query.all()
            side_quests = [row[0] for row in results]
            
            return side_quests
        except Exception as e:
            logger.error(f"Error retrieving nearby side quests: {str(e)}")
            return []
    
    async def get_side_quests_along_route(
        self,
        route: Route,
        max_distance: float = 5.0,  # km
        limit: int = 20,
        categories: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        max_detour_time: Optional[int] = None,
        min_uniqueness: Optional[float] = None,
        include_inactive: bool = False,
        include_seasonal: bool = True
    ) -> List[Tuple[SideQuest, float]]:
        """
        Get side quests along a route.
        
        Args:
            route: Route object with legs and steps
            max_distance: Maximum distance from the route in kilometers
            limit: Maximum number of results to return
            categories: Optional list of category IDs to filter by
            difficulty: Optional difficulty level to filter by
            max_detour_time: Maximum detour time in minutes
            min_uniqueness: Minimum uniqueness score (0-100)
            include_inactive: Include inactive side quests
            include_seasonal: Include out-of-season side quests
            
        Returns:
            List of tuples containing (SideQuest, distance_from_route_km)
        """
        try:
            # Extract route points
            route_points = []
            for leg in route.legs:
                for step in leg.steps:
                    route_points.append((step.start_location.lat, step.start_location.lng))
                    route_points.append((step.end_location.lat, step.end_location.lng))
            
            # Deduplicate points and ensure we have a reasonable number
            # For very long routes, we'll sample points to keep the calculation reasonable
            unique_points = list(set(route_points))
            if len(unique_points) > 100:
                step = len(unique_points) // 100
                route_points = unique_points[::step]
            else:
                route_points = unique_points
            
            # Get candidate side quests
            # We'll get side quests near any point on the route
            candidate_quests = set()
            for lat, lng in route_points:
                nearby_quests = await self.get_nearby_side_quests(
                    latitude=lat,
                    longitude=lng,
                    radius=max_distance,
                    limit=50,  # Get more than we need to ensure good coverage
                    categories=categories,
                    difficulty=difficulty,
                    max_detour_time=max_detour_time,
                    min_uniqueness=min_uniqueness,
                    include_inactive=include_inactive,
                    include_seasonal=include_seasonal
                )
                for quest in nearby_quests:
                    candidate_quests.add(quest.id)
            
            # If we have too few candidates, expand the search
            if len(candidate_quests) < limit and max_distance < 20:
                expanded_radius = min(max_distance * 2, 20)
                for lat, lng in route_points[::3]:  # Use fewer points for expanded search
                    nearby_quests = await self.get_nearby_side_quests(
                        latitude=lat,
                        longitude=lng,
                        radius=expanded_radius,
                        limit=30,
                        categories=categories,
                        difficulty=difficulty,
                        max_detour_time=max_detour_time,
                        min_uniqueness=min_uniqueness,
                        include_inactive=include_inactive,
                        include_seasonal=include_seasonal
                    )
                    for quest in nearby_quests:
                        candidate_quests.add(quest.id)
            
            # Get full details for candidate quests
            quest_objects = {}
            if candidate_quests:
                quests = self.db.query(SideQuest).filter(SideQuest.id.in_(candidate_quests)).all()
                for quest in quests:
                    quest_objects[quest.id] = quest
            
            # Calculate minimum distance from each quest to the route
            quest_distances = []
            for quest_id, quest in quest_objects.items():
                min_distance = float('inf')
                for lat, lng in route_points:
                    distance = self._haversine_distance(
                        lat1=lat,
                        lon1=lng,
                        lat2=quest.latitude,
                        lon2=quest.longitude
                    )
                    min_distance = min(min_distance, distance)
                
                # Add the quest and its distance to our results
                quest_distances.append((quest, min_distance))
            
            # Sort by distance and limit results
            quest_distances.sort(key=lambda x: x[1])
            return quest_distances[:limit]
        except Exception as e:
            logger.error(f"Error retrieving side quests along route: {str(e)}")
            return []
    
    async def get_user_side_quests(
        self,
        user_id: str,
        status: Optional[str] = None,
        include_details: bool = True,
        trip_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a user's side quests.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            include_details: Include full side quest details
            trip_id: Optional trip ID filter
            
        Returns:
            List of user side quests with details
        """
        try:
            query = self.db.query(UserSideQuest).filter(UserSideQuest.user_id == user_id)
            
            if status:
                query = query.filter(UserSideQuest.status == status)
                
            if trip_id:
                query = query.filter(UserSideQuest.trip_id == trip_id)
            
            # Eager load side quest details if requested
            if include_details:
                query = query.options(joinedload(UserSideQuest.side_quest))
            
            # Order by status (active first) and then by recommended_at (newest first)
            query = query.order_by(
                # Available and accepted first, then completed, then skipped/expired
                case_expr := case(
                    (UserSideQuest.status == SideQuestStatus.AVAILABLE.value, 0),
                    (UserSideQuest.status == SideQuestStatus.ACCEPTED.value, 1),
                    (UserSideQuest.status == SideQuestStatus.COMPLETED.value, 2),
                    (UserSideQuest.status == SideQuestStatus.SKIPPED.value, 3),
                    (UserSideQuest.status == SideQuestStatus.EXPIRED.value, 4),
                    else_=5
                ),
                UserSideQuest.recommended_at.desc().nullslast()
            )
            
            user_side_quests = query.all()
            
            # Format the results
            results = []
            for user_quest in user_side_quests:
                result = user_quest.to_dict()
                
                if include_details and user_quest.side_quest:
                    result["side_quest"] = user_quest.side_quest.to_dict()
                
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error retrieving user side quests for user {user_id}: {str(e)}")
            return []
    
    async def recommend_side_quests(
        self,
        user_id: str,
        route: Route,
        current_location: Optional[Dict[str, float]] = None,
        user_interests: Optional[List[str]] = None,
        available_time: Optional[int] = None,  # minutes
        count: int = 3,
        trip_id: Optional[str] = None
    ) -> List[SideQuest]:
        """
        Generate side quest recommendations for a user.
        
        Args:
            user_id: ID of the user
            route: Route object with legs and steps
            current_location: Optional current location (lat/lng)
            user_interests: Optional list of user interests
            available_time: Optional available time in minutes
            count: Number of side quests to recommend
            trip_id: Optional trip ID for grouping
            
        Returns:
            List of recommended SideQuest objects
        """
        try:
            # Get user's side quest history to avoid repeating recommendations
            existing_quests = await self.get_user_side_quests(
                user_id=user_id,
                include_details=False,
                trip_id=trip_id
            )
            existing_quest_ids = [q["side_quest_id"] for q in existing_quests]
            
            # Calculate max detour time based on available time
            max_detour_time = None
            if available_time:
                # Use 40% of available time for detours as a reasonable default
                max_detour_time = int(available_time * 0.4)
            
            # Get side quests along the route
            route_quests = await self.get_side_quests_along_route(
                route=route,
                max_distance=5.0,  # 5km from route
                limit=50,  # Get more than we need for scoring
                max_detour_time=max_detour_time,
                min_uniqueness=60.0  # Focus on more unique experiences
            )
            
            # Filter out quests the user already has
            filtered_quests = [(q, d) for q, d in route_quests if q.id not in existing_quest_ids]
            
            # If we don't have enough after filtering, expand search radius
            if len(filtered_quests) < count * 2:
                expanded_quests = await self.get_side_quests_along_route(
                    route=route,
                    max_distance=10.0,  # 10km from route
                    limit=50,
                    max_detour_time=max_detour_time,
                    min_uniqueness=40.0  # Lower bar for uniqueness when expanding
                )
                expanded_filtered = [(q, d) for q, d in expanded_quests if q.id not in existing_quest_ids]
                filtered_quests.extend(expanded_filtered)
                # Remove duplicates
                quest_ids = set()
                unique_filtered_quests = []
                for q, d in filtered_quests:
                    if q.id not in quest_ids:
                        quest_ids.add(q.id)
                        unique_filtered_quests.append((q, d))
                filtered_quests = unique_filtered_quests
            
            # Score the quests based on various factors
            scored_quests = []
            for quest, distance_from_route in filtered_quests:
                score = 0
                
                # Base score from uniqueness
                if quest.uniqueness_score:
                    score += quest.uniqueness_score * 0.5
                
                # Distance factor - closer is better
                distance_score = 100 - (distance_from_route * 10)  # 0km=100, 10km=0
                score += min(max(0, distance_score), 100) * 0.2
                
                # Detour time factor - shorter is better
                if quest.detour_time:
                    detour_score = 100 - (quest.detour_time / 2)  # 0min=100, 200min=0
                    score += min(max(0, detour_score), 100) * 0.15
                
                # Interest matching
                if user_interests and quest.tags:
                    matches = sum(1 for interest in user_interests if interest.lower() in [t.lower() for t in quest.tags])
                    interest_score = min(matches * 20, 100)  # 5+ matches = 100
                    score += interest_score * 0.15
                
                # Verified content bonus
                if quest.is_verified:
                    score += 10
                
                # External rating bonus
                if quest.external_rating:
                    rating_score = quest.external_rating * 20  # 0-5 star rating to 0-100
                    score += rating_score * 0.1
                
                scored_quests.append((quest, score))
            
            # Sort by score (highest first)
            scored_quests.sort(key=lambda x: x[1], reverse=True)
            
            # Take the top N quests
            top_quests = [q for q, _ in scored_quests[:count]]
            
            # Create UserSideQuest records for recommendations
            now = datetime.utcnow()
            for quest in top_quests:
                # Check if this quest is already recommended
                existing = await self.get_user_side_quest(user_id, quest.id)
                if existing:
                    # Update if it's expired or skipped
                    if existing.status in [SideQuestStatus.EXPIRED.value, SideQuestStatus.SKIPPED.value]:
                        existing.status = SideQuestStatus.AVAILABLE.value
                        existing.recommended_at = now
                        existing.trip_id = trip_id
                        self.db.add(existing)
                else:
                    # Create new recommendation
                    user_quest = UserSideQuest(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        side_quest_id=quest.id,
                        status=SideQuestStatus.AVAILABLE.value,
                        progress=0,
                        trip_id=trip_id,
                        recommended_at=now
                    )
                    self.db.add(user_quest)
            
            self.db.commit()
            
            return top_quests
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recommending side quests: {str(e)}")
            return []
    
    async def update_user_side_quest_status(
        self,
        user_id: str,
        side_quest_id: str,
        status: str,
        progress: Optional[int] = None,
        feedback: Optional[str] = None,
        user_rating: Optional[int] = None
    ) -> Optional[UserSideQuest]:
        """
        Update the status of a user side quest.
        
        Args:
            user_id: ID of the user
            side_quest_id: ID of the side quest
            status: New status for the side quest
            progress: Optional progress percentage
            feedback: Optional user feedback
            user_rating: Optional user rating (1-5)
            
        Returns:
            Updated UserSideQuest object or None if not found
            
        Raises:
            HTTPException: If the update fails
        """
        try:
            # Get the user side quest
            user_side_quest = await self.get_user_side_quest(user_id, side_quest_id)
            if not user_side_quest:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Side quest not found for this user"
                )
            
            # Update the status
            user_side_quest.status = status
            
            # Set timestamps based on status
            now = datetime.utcnow()
            if status == SideQuestStatus.COMPLETED.value:
                user_side_quest.completed_at = now
                user_side_quest.progress = 100
            elif status == SideQuestStatus.SKIPPED.value:
                user_side_quest.skipped_at = now
            
            # Update other fields if provided
            if progress is not None:
                user_side_quest.progress = progress
            
            if feedback is not None:
                user_side_quest.feedback = feedback
                
            if user_rating is not None:
                user_side_quest.user_rating = user_rating
            
            self.db.add(user_side_quest)
            self.db.commit()
            self.db.refresh(user_side_quest)
            
            return user_side_quest
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user side quest status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update side quest status: {str(e)}"
            )
    
    async def create_side_quest(
        self,
        title: str,
        description: str,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None,
        address: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        estimated_duration: Optional[int] = None,
        distance_from_route: Optional[float] = None,
        detour_time: Optional[int] = None,
        uniqueness_score: Optional[float] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        external_id: Optional[str] = None,
        external_rating: Optional[float] = None,
        external_url: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None,
        rewards: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        operating_hours: Optional[Dict[str, Any]] = None,
        price_level: Optional[int] = None,
        is_verified: bool = False,
        is_user_generated: bool = False,
        is_active: bool = True,
        is_seasonal: bool = False,
        seasonal_start: Optional[datetime] = None,
        seasonal_end: Optional[datetime] = None,
        created_by: Optional[str] = None,
        source: Optional[str] = None
    ) -> SideQuest:
        """
        Create a new side quest.
        
        Args:
            title: Title of the side quest
            description: Description of the side quest
            latitude: Latitude of the location
            longitude: Longitude of the location
            location_name: Optional name of the location
            address: Optional address of the location
            category: Optional category ID
            difficulty: Optional difficulty level
            estimated_duration: Optional estimated duration in minutes
            distance_from_route: Optional distance from route in kilometers
            detour_time: Optional detour time in minutes
            uniqueness_score: Optional uniqueness score (0-100)
            image_url: Optional URL to an image
            thumbnail_url: Optional URL to a thumbnail
            external_id: Optional ID from an external system
            external_rating: Optional rating from an external system
            external_url: Optional URL to an external listing
            requirements: Optional requirements to complete the quest
            rewards: Optional rewards for completing the quest
            tags: Optional tags for filtering
            operating_hours: Optional operating hours
            price_level: Optional price level (1-4)
            is_verified: Whether the side quest is verified by an admin
            is_user_generated: Whether the side quest was generated by a user
            is_active: Whether the side quest is active
            is_seasonal: Whether the side quest is seasonal
            seasonal_start: Optional start date for seasonal side quests
            seasonal_end: Optional end date for seasonal side quests
            created_by: Optional ID of the user who created the side quest
            source: Optional source of the side quest
            
        Returns:
            Created SideQuest object
            
        Raises:
            HTTPException: If the creation fails
        """
        try:
            # Create the side quest
            side_quest = SideQuest(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                address=address,
                category=category,
                difficulty=difficulty,
                estimated_duration=estimated_duration,
                distance_from_route=distance_from_route,
                detour_time=detour_time,
                uniqueness_score=uniqueness_score,
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                external_id=external_id,
                external_rating=external_rating,
                external_url=external_url,
                requirements=requirements,
                rewards=rewards,
                tags=tags,
                operating_hours=operating_hours,
                price_level=price_level,
                is_verified=is_verified,
                is_user_generated=is_user_generated,
                is_active=is_active,
                is_seasonal=is_seasonal,
                seasonal_start=seasonal_start,
                seasonal_end=seasonal_end,
                created_by=created_by,
                source=source
            )
            
            self.db.add(side_quest)
            self.db.commit()
            self.db.refresh(side_quest)
            
            return side_quest
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating side quest: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create side quest: {str(e)}"
            )
    
    async def seed_side_quest_categories(self) -> List[SideQuestCategory]:
        """
        Seed the database with default side quest categories.
        
        Returns:
            List of created SideQuestCategory objects
        """
        try:
            # Define default categories
            default_categories = [
                {
                    "id": "historical",
                    "name": "Historical",
                    "description": "Historical sites, landmarks, and museums",
                    "icon_url": "https://example.com/icons/historical.png",
                    "color": "#007AFF"
                },
                {
                    "id": "natural",
                    "name": "Natural",
                    "description": "Natural wonders, parks, and scenic views",
                    "icon_url": "https://example.com/icons/natural.png",
                    "color": "#34C759"
                },
                {
                    "id": "cultural",
                    "name": "Cultural",
                    "description": "Cultural experiences, art, and local traditions",
                    "icon_url": "https://example.com/icons/cultural.png",
                    "color": "#AF52DE"
                },
                {
                    "id": "culinary",
                    "name": "Culinary",
                    "description": "Food, drinks, and culinary experiences",
                    "icon_url": "https://example.com/icons/culinary.png",
                    "color": "#FF9500"
                },
                {
                    "id": "adventure",
                    "name": "Adventure",
                    "description": "Outdoor activities and adventures",
                    "icon_url": "https://example.com/icons/adventure.png",
                    "color": "#FF3B30"
                },
                {
                    "id": "hidden_gem",
                    "name": "Hidden Gem",
                    "description": "Lesser-known but wonderful places",
                    "icon_url": "https://example.com/icons/hidden_gem.png",
                    "color": "#5856D6"
                },
                {
                    "id": "quirky",
                    "name": "Quirky",
                    "description": "Unusual, offbeat, and quirky attractions",
                    "icon_url": "https://example.com/icons/quirky.png",
                    "color": "#FF2D55"
                }
            ]
            
            # Create categories
            created_categories = []
            for category_data in default_categories:
                # Check if category already exists
                existing = self.db.query(SideQuestCategory).filter(
                    SideQuestCategory.id == category_data["id"]
                ).first()
                
                if not existing:
                    # Create new category
                    category = SideQuestCategory(
                        id=category_data["id"],
                        name=category_data["name"],
                        description=category_data["description"],
                        icon_url=category_data["icon_url"],
                        color=category_data["color"]
                    )
                    
                    self.db.add(category)
                    created_categories.append(category)
            
            if created_categories:
                self.db.commit()
                for category in created_categories:
                    self.db.refresh(category)
            
            # Return all categories, including those that already existed
            return self.db.query(SideQuestCategory).all()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error seeding side quest categories: {str(e)}")
            return []
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        
        Args:
            lat1: Latitude of the first point in degrees
            lon1: Longitude of the first point in degrees
            lat2: Latitude of the second point in degrees
            lon2: Longitude of the second point in degrees
            
        Returns:
            Distance between the points in kilometers
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        
        return c * r


def get_side_quest_generator(db: Session = Depends(get_db)) -> SideQuestGenerator:
    """
    Dependency to get the side quest generator.
    
    Args:
        db: Database session dependency
        
    Returns:
        SideQuestGenerator instance
    """
    return SideQuestGenerator(db)