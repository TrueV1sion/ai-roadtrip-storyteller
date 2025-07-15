from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, func, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class Theme(Base):
    """Theme model for customized storytelling experiences."""
    __tablename__ = "themes"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    
    # Theme attributes
    prompt_template = Column(Text, nullable=False)  # Base prompt template for this theme
    style_guide = Column(JSON, nullable=False)  # Style guidelines for stories
    recommended_interests = Column(JSON, nullable=True)  # Interests that work well with this theme
    music_genres = Column(JSON, nullable=True)  # Music genres that match this theme
    
    # Theme categorization
    category = Column(String, nullable=True)  # e.g., "historical", "adventure", "haunted"
    tags = Column(JSON, nullable=True)  # Tags for searching and filtering
    
    # Availability
    is_seasonal = Column(Boolean, default=False)  # Whether theme is seasonal
    available_from = Column(DateTime, nullable=True)  # Start date if seasonal
    available_until = Column(DateTime, nullable=True)  # End date if seasonal
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Featured themes get priority
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    stories = relationship("Story", back_populates="theme")
    
    def __repr__(self):
        return f"<Theme {self.name}>"
    
    def to_dict(self):
        """Convert theme to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "category": self.category,
            "tags": self.tags,
            "is_seasonal": self.is_seasonal,
            "available_from": self.available_from.isoformat() if self.available_from else None,
            "available_until": self.available_until.isoformat() if self.available_until else None,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserThemePreference(Base):
    """User preferences for themes."""
    __tablename__ = "user_theme_preferences"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    theme_id = Column(String, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)
    
    # Preference details
    is_favorite = Column(Boolean, default=False)
    preference_level = Column(String, nullable=True)  # "love", "like", "dislike"
    last_used = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="theme_preferences")
    theme = relationship("Theme")
    
    def __repr__(self):
        return f"<UserThemePreference {self.user_id} - {self.theme_id}>"