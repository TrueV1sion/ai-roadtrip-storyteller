from datetime import datetime
import json
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.database import get_db
from app.models.theme import Theme, UserThemePreference
from app.models.user import User

logger = get_logger(__name__)


class ThemeEngine:
    """Service for managing themes and themed content generation."""
    
    def __init__(self, db: Session):
        """Initialize the theme engine with database session."""
        self.db = db
        self.theme_cache = {}  # In-memory cache of themes
    
    async def get_all_themes(
        self, 
        active_only: bool = True,
        seasonal_check: bool = True,
        include_metadata: bool = False
    ) -> List[Theme]:
        """
        Get all themes, optionally filtering by active status and seasonality.
        
        Args:
            active_only: If True, only return active themes
            seasonal_check: If True, filter seasonal themes by current date
            include_metadata: If True, include full metadata like prompt templates
            
        Returns:
            List of Theme objects
        """
        try:
            query = self.db.query(Theme)
            
            if active_only:
                query = query.filter(Theme.is_active == True)
                
            if seasonal_check:
                current_date = datetime.utcnow()
                # Include non-seasonal themes, or seasonal themes that are currently available
                query = query.filter(
                    or_(
                        Theme.is_seasonal == False,
                        and_(
                            Theme.is_seasonal == True,
                            or_(
                                Theme.available_from == None,
                                Theme.available_from <= current_date
                            ),
                            or_(
                                Theme.available_until == None,
                                Theme.available_until >= current_date
                            )
                        )
                    )
                )
            
            # Order by featured status (featured first) and then by name
            query = query.order_by(Theme.is_featured.desc(), Theme.name)
            
            themes = query.all()
            
            # If metadata is not needed, remove sensitive fields like prompt templates
            if not include_metadata:
                for theme in themes:
                    # Clear fields that shouldn't be exposed to regular users
                    theme.prompt_template = None
                    theme.style_guide = None
            
            return themes
        except Exception as e:
            logger.error(f"Error retrieving themes: {str(e)}")
            return []
    
    async def get_theme(
        self, 
        theme_id: str,
        include_metadata: bool = False
    ) -> Optional[Theme]:
        """
        Get a specific theme by ID.
        
        Args:
            theme_id: ID of the theme to retrieve
            include_metadata: If True, include full metadata like prompt templates
            
        Returns:
            Theme object or None if not found
        """
        try:
            # Check cache first
            if theme_id in self.theme_cache:
                return self.theme_cache[theme_id]
            
            theme = self.db.query(Theme).filter(Theme.id == theme_id).first()
            
            if theme and not include_metadata:
                # Clear fields that shouldn't be exposed to regular users
                theme.prompt_template = None
                theme.style_guide = None
            
            # Cache the theme for future requests
            if theme:
                self.theme_cache[theme_id] = theme
                
            return theme
        except Exception as e:
            logger.error(f"Error retrieving theme {theme_id}: {str(e)}")
            return None
    
    async def create_theme(self, theme_data: Dict[str, Any]) -> Theme:
        """
        Create a new theme.
        
        Args:
            theme_data: Dictionary with theme data
            
        Returns:
            Created Theme object
            
        Raises:
            HTTPException: If theme creation fails
        """
        try:
            # Create new theme
            theme = Theme(
                id=str(uuid.uuid4()),
                name=theme_data["name"],
                description=theme_data["description"],
                image_url=theme_data.get("image_url"),
                prompt_template=theme_data["prompt_template"],
                style_guide=theme_data["style_guide"],
                recommended_interests=theme_data.get("recommended_interests"),
                music_genres=theme_data.get("music_genres"),
                category=theme_data.get("category"),
                tags=theme_data.get("tags"),
                is_seasonal=theme_data.get("is_seasonal", False),
                available_from=theme_data.get("available_from"),
                available_until=theme_data.get("available_until"),
                is_active=theme_data.get("is_active", True),
                is_featured=theme_data.get("is_featured", False),
            )
            
            self.db.add(theme)
            self.db.commit()
            self.db.refresh(theme)
            
            logger.info(f"Created new theme: {theme.name} (ID: {theme.id})")
            return theme
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating theme: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create theme: {str(e)}"
            )
    
    async def update_theme(self, theme_id: str, theme_data: Dict[str, Any]) -> Optional[Theme]:
        """
        Update an existing theme.
        
        Args:
            theme_id: ID of the theme to update
            theme_data: Dictionary with updated theme data
            
        Returns:
            Updated Theme object or None if not found
            
        Raises:
            HTTPException: If theme update fails
        """
        try:
            theme = await self.get_theme(theme_id, include_metadata=True)
            if not theme:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Theme with ID {theme_id} not found"
                )
            
            # Update fields
            for key, value in theme_data.items():
                if hasattr(theme, key):
                    setattr(theme, key, value)
            
            self.db.commit()
            self.db.refresh(theme)
            
            # Clear from cache since it was updated
            if theme_id in self.theme_cache:
                del self.theme_cache[theme_id]
            
            logger.info(f"Updated theme: {theme.name} (ID: {theme.id})")
            return theme
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating theme {theme_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update theme: {str(e)}"
            )
    
    async def delete_theme(self, theme_id: str) -> bool:
        """
        Delete a theme.
        
        Args:
            theme_id: ID of the theme to delete
            
        Returns:
            Boolean indicating success
            
        Raises:
            HTTPException: If theme deletion fails
        """
        try:
            theme = await self.get_theme(theme_id)
            if not theme:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Theme with ID {theme_id} not found"
                )
            
            # Delete the theme
            self.db.delete(theme)
            self.db.commit()
            
            # Clear from cache
            if theme_id in self.theme_cache:
                del self.theme_cache[theme_id]
            
            logger.info(f"Deleted theme: {theme.name} (ID: {theme.id})")
            return True
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting theme {theme_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete theme: {str(e)}"
            )
    
    async def get_user_theme_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's theme preferences.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with theme preferences
        """
        try:
            preferences = self.db.query(UserThemePreference).filter(
                UserThemePreference.user_id == user_id
            ).all()
            
            # Get all theme IDs from preferences
            theme_ids = [pref.theme_id for pref in preferences]
            
            # Get theme details for those IDs
            themes = self.db.query(Theme).filter(Theme.id.in_(theme_ids)).all()
            theme_map = {theme.id: theme for theme in themes}
            
            result = {
                "favorites": [],
                "preferences": []
            }
            
            for pref in preferences:
                theme = theme_map.get(pref.theme_id)
                if not theme:
                    continue
                
                theme_data = {
                    "id": theme.id,
                    "name": theme.name,
                    "description": theme.description,
                    "image_url": theme.image_url,
                    "category": theme.category,
                    "preference_level": pref.preference_level,
                    "last_used": pref.last_used.isoformat() if pref.last_used else None
                }
                
                if pref.is_favorite:
                    result["favorites"].append(theme_data)
                else:
                    result["preferences"].append(theme_data)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving theme preferences for user {user_id}: {str(e)}")
            return {"favorites": [], "preferences": []}
    
    async def set_user_theme_preference(
        self, 
        user_id: str,
        theme_id: str,
        is_favorite: Optional[bool] = None,
        preference_level: Optional[str] = None
    ) -> UserThemePreference:
        """
        Set a user's preference for a theme.
        
        Args:
            user_id: ID of the user
            theme_id: ID of the theme
            is_favorite: Whether the theme is a favorite
            preference_level: User's preference level (love, like, dislike)
            
        Returns:
            Updated UserThemePreference object
            
        Raises:
            HTTPException: If setting preference fails
        """
        try:
            # Check if user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )
            
            # Check if theme exists
            theme = await self.get_theme(theme_id)
            if not theme:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Theme with ID {theme_id} not found"
                )
            
            # Check if preference already exists
            preference = self.db.query(UserThemePreference).filter(
                UserThemePreference.user_id == user_id,
                UserThemePreference.theme_id == theme_id
            ).first()
            
            # Create or update preference
            if not preference:
                preference = UserThemePreference(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    theme_id=theme_id,
                    is_favorite=is_favorite if is_favorite is not None else False,
                    preference_level=preference_level
                )
                self.db.add(preference)
            else:
                if is_favorite is not None:
                    preference.is_favorite = is_favorite
                if preference_level is not None:
                    preference.preference_level = preference_level
                preference.updated_at = func.now()
            
            self.db.commit()
            self.db.refresh(preference)
            
            logger.info(f"Set theme preference for user {user_id} on theme {theme_id}")
            return preference
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting theme preference: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set theme preference: {str(e)}"
            )
    
    async def generate_themed_prompt(
        self,
        theme_id: str,
        base_prompt: str,
        location: Dict[str, Any],
        interests: List[str],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a themed prompt by enhancing the base prompt with theme-specific elements.
        
        Args:
            theme_id: ID of the theme to use
            base_prompt: Base prompt to enhance
            location: Dictionary with location information
            interests: List of user interests
            context: Additional context information
            
        Returns:
            Enhanced themed prompt
            
        Raises:
            HTTPException: If prompt generation fails
        """
        try:
            theme = await self.get_theme(theme_id, include_metadata=True)
            if not theme:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Theme with ID {theme_id} not found"
                )
            
            # Get the theme's prompt template
            template = theme.prompt_template
            
            # Replace placeholders in the template
            prompt = template.replace("{base_prompt}", base_prompt)
            
            # Replace location placeholders
            if "{location_name}" in prompt and location.get("name"):
                prompt = prompt.replace("{location_name}", location["name"])
            
            if "{latitude}" in prompt and location.get("latitude"):
                prompt = prompt.replace("{latitude}", str(location["latitude"]))
                
            if "{longitude}" in prompt and location.get("longitude"):
                prompt = prompt.replace("{longitude}", str(location["longitude"]))
            
            # Replace interests placeholder
            if "{interests}" in prompt and interests:
                interests_str = ", ".join(interests)
                prompt = prompt.replace("{interests}", interests_str)
            
            # Replace context placeholders
            for key, value in context.items():
                placeholder = "{" + key + "}"
                if placeholder in prompt:
                    prompt = prompt.replace(placeholder, str(value))
            
            # Apply style guide
            if theme.style_guide:
                style = theme.style_guide
                
                # Add tone guidelines
                if "tone" in style and "{style_tone}" in prompt:
                    prompt = prompt.replace("{style_tone}", style["tone"])
                
                # Add language guidelines
                if "language" in style and "{style_language}" in prompt:
                    prompt = prompt.replace("{style_language}", style["language"])
                
                # Add narrative style guidelines
                if "narrative_style" in style and "{narrative_style}" in prompt:
                    prompt = prompt.replace("{narrative_style}", style["narrative_style"])
            
            logger.info(f"Generated themed prompt using theme: {theme.name} (ID: {theme.id})")
            return prompt
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating themed prompt: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate themed prompt: {str(e)}"
            )
    
    async def recommend_themes(
        self,
        location: Dict[str, Any],
        interests: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Theme]:
        """
        Recommend themes based on location, interests, and optionally user history.
        
        Args:
            location: Dictionary with location information
            interests: List of user interests
            user_id: Optional user ID for personalized recommendations
            limit: Maximum number of themes to recommend
            
        Returns:
            List of recommended Theme objects
        """
        try:
            # Get all active and in-season themes
            all_themes = await self.get_all_themes(active_only=True, seasonal_check=True)
            
            # Score each theme based on relevance
            scored_themes = []
            
            for theme in all_themes:
                score = 0
                
                # Increase score for featured themes
                if theme.is_featured:
                    score += 10
                
                # Check for location relevance (category match)
                if theme.category:
                    location_type = location.get("type", "").lower()
                    if location_type and theme.category.lower() in location_type:
                        score += 5
                
                # Check for interest matches
                if interests and theme.recommended_interests:
                    for interest in interests:
                        if interest.lower() in [i.lower() for i in theme.recommended_interests]:
                            score += 3
                
                # Check user preference history if available
                if user_id:
                    preference = self.db.query(UserThemePreference).filter(
                        UserThemePreference.user_id == user_id,
                        UserThemePreference.theme_id == theme.id
                    ).first()
                    
                    if preference:
                        if preference.is_favorite:
                            score += 8
                        
                        if preference.preference_level == "love":
                            score += 5
                        elif preference.preference_level == "like":
                            score += 3
                        elif preference.preference_level == "dislike":
                            score -= 10
                
                scored_themes.append((theme, score))
            
            # Sort by score (highest first) and take top themes
            scored_themes.sort(key=lambda x: x[1], reverse=True)
            recommended_themes = [theme for theme, score in scored_themes[:limit]]
            
            return recommended_themes
        except Exception as e:
            logger.error(f"Error recommending themes: {str(e)}")
            return []


def get_theme_engine(db: Session = Depends(get_db)) -> ThemeEngine:
    """
    Dependency to get the theme engine.
    
    Args:
        db: Database session dependency
        
    Returns:
        ThemeEngine instance
    """
    return ThemeEngine(db)