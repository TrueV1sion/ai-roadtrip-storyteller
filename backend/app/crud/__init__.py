# CRUD module initialization
# Import all CRUD functions for easier access

# User CRUD operations
from .crud_user import (
    get_user, get_user_by_email, get_user_by_username, get_users,
    create_user, update_user, delete_user, activate_user, deactivate_user,
    authenticate_user, update_user_last_login, update_user_settings,
    get_user_stats, search_users
)

# Preferences CRUD operations
from .crud_preferences import get_preferences_dict

# Story CRUD operations
from .crud_story import (
    get_story, get_stories_by_user, create_story, update_story_rating,
    update_story_metadata, increment_story_play_count, update_story_completion_rate,
    toggle_story_favorite, get_average_rating, delete_story, get_stories_by_location
)

# Experience CRUD operations
from .crud_experience import (
    get_experience, get_experiences, get_experiences_by_user, create_experience,
    update_experience, delete_experience, update_experience_status,
    get_experiences_by_location, get_experiences_by_date_range, get_active_experiences,
    get_experience_statistics, search_experiences, get_popular_experiences,
    update_experience_metadata, get_experiences_requiring_action,
    user_saved_experience_crud
)

# Theme CRUD operations
from .crud_theme import (
    get_theme, get_theme_by_name, get_themes, create_theme, update_theme,
    delete_theme, activate_theme, deactivate_theme, get_themes_by_category,
    get_active_themes, search_themes, get_theme_statistics, get_popular_themes,
    get_user_theme_preferences, get_user_theme_preference, create_user_theme_preference,
    update_user_theme_preference, delete_user_theme_preference,
    get_recommended_themes_for_user, get_user_theme_statistics
)

# Side Quest CRUD operations
from .crud_side_quest import (
    get_side_quest, get_side_quests, get_side_quests_by_user, create_side_quest,
    update_side_quest, delete_side_quest, update_side_quest_status,
    get_side_quests_by_location, get_available_side_quests, get_active_side_quests,
    get_completed_side_quests, get_side_quest_statistics, search_side_quests,
    get_side_quests_by_category, get_side_quests_by_difficulty,
    get_recommended_side_quests, update_side_quest_progress,
    get_side_quests_by_date_range, get_overdue_side_quests
)

# Reservation CRUD operations
from .crud_reservation import (
    get_reservation, get_reservations, get_reservations_by_user, create_reservation,
    update_reservation, delete_reservation, update_reservation_status,
    get_reservations_by_date_range, get_upcoming_reservations, get_active_reservations,
    get_reservations_by_location, get_reservation_statistics, search_reservations,
    get_reservations_by_type, get_reservations_requiring_action, get_expired_reservations,
    cancel_reservation, confirm_reservation, complete_reservation,
    get_reservation_reminders, update_reservation_metadata
)