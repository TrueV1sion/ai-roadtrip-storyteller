from enum import Enum


class BookingType(str, Enum):
    """Types of bookings available."""
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    ACCOMMODATION = "accommodation"
    ACTIVITY = "activity"
    TRANSPORTATION = "transportation"


class UserRole(str, Enum):
    """User role enumeration for role-based access control."""
    ADMIN = "admin"
    PREMIUM = "premium"
    STANDARD = "standard"
    GUEST = "guest"


class ResourceType(str, Enum):
    """Resource types for permission management."""
    STORY = "story"
    EXPERIENCE = "experience"
    PREFERENCES = "preferences"
    USER = "user"
    ADMIN = "admin"
    ITINERARY = "itinerary"
    GAME = "game"
    SYSTEM = "system"
    ANY = "any"


class Action(str, Enum):
    """Actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    MANAGE = "manage"
    ANY = "any"