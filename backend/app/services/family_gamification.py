from typing import Dict, List
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


class FamilyGamificationService:
    """Service for managing enhanced family gamification features."""

    CHALLENGE_CATEGORIES = {
        "educational": {
            "points_multiplier": 2.0,
            "min_age": 5,
            "description": (
                "Learn about places and culture"
            )
        },
        "physical": {
            "points_multiplier": 1.5,
            "min_age": 3,
            "description": "Stay active during the trip"
        },
        "creative": {
            "points_multiplier": 1.8,
            "min_age": 4,
            "description": (
                "Express yourself through art and stories"
            )
        },
        "exploration": {
            "points_multiplier": 1.7,
            "min_age": 3,
            "description": (
                "Discover new places and landmarks"
            )
        },
        "social": {
            "points_multiplier": 1.6,
            "min_age": 4,
            "description": "Connect with family and make memories"
        },
        "collection": {
            "points_multiplier": 1.4,
            "min_age": 3,
            "description": "Collect virtual items and badges"
        }
    }

    def __init__(self):
        self.active_sessions = {}

    async def get_family_challenges(
        self,
        trip_id: str,
        location: Dict[str, float],
        children_ages: List[int]
    ) -> List[Dict]:
        """Get age-appropriate challenges for the family."""
        try:
            challenges = []
            min_age = min(children_ages) if children_ages else 3

            # Educational challenges
            if min_age >= self.CHALLENGE_CATEGORIES["educational"]["min_age"]:
                challenges.extend([
                    {
                        "id": "state_facts",
                        "type": "educational",
                        "title": "State History Master",
                        "description": (
                            "Learn 5 facts about each state you visit"
                        ),
                        "points": 100,
                        "status": "active",
                        "progress": "2/5",
                        "rewards": ["History Badge", "Knowledge Points"]
                    },
                    {
                        "id": "nature_science",
                        "type": "educational",
                        "title": "Junior Scientist",
                        "description": "Identify 3 different ecosystems",
                        "points": 150,
                        "status": "available",
                        "rewards": ["Science Badge", "Nature Journal"]
                    }
                ])

            # Physical challenges
            challenges.extend([
                {
                    "id": "stretch_breaks",
                    "type": "physical",
                    "title": "Active Explorer",
                    "description": "Do 3 stretch breaks today",
                    "points": 50,
                    "status": "active",
                    "progress": "1/3",
                    "rewards": ["Energy Badge", "Bonus Points"]
                },
                {
                    "id": "playground_adventure",
                    "type": "physical",
                    "title": "Playground Champion",
                    "description": "Visit 3 different playgrounds",
                    "points": 75,
                    "status": "in_progress",
                    "progress": "1/3",
                    "rewards": ["Adventure Badge", "Special Sticker"]
                }
            ])

            # Creative challenges
            if min_age >= self.CHALLENGE_CATEGORIES["creative"]["min_age"]:
                challenges.extend([
                    {
                        "id": "travel_journal",
                        "type": "creative",
                        "title": "Travel Journalist",
                        "description": (
                            "Create a travel journal entry with drawings"
                        ),
                        "points": 120,
                        "status": "available",
                        "rewards": ["Creative Badge", "Special Markers"]
                    },
                    {
                        "id": "photo_story",
                        "type": "creative",
                        "title": "Family Photographer",
                        "description": "Create a photo story of your day",
                        "points": 100,
                        "status": "available",
                        "rewards": ["Photo Badge", "Digital Album"]
                    }
                ])

            # Exploration challenges
            challenges.extend([
                {
                    "id": "landmark_bingo",
                    "type": "exploration",
                    "title": "Landmark Explorer",
                    "description": (
                        "Find all items on your landmark bingo card"
                    ),
                    "points": 200,
                    "status": "active",
                    "progress": "4/9",
                    "rewards": ["Explorer Badge", "Mystery Prize"]
                },
                {
                    "id": "local_food",
                    "type": "exploration",
                    "title": "Food Adventurer",
                    "description": "Try 3 local specialty foods",
                    "points": 150,
                    "status": "available",
                    "rewards": ["Foodie Badge", "Recipe Book"]
                }
            ])

            # Social challenges
            if min_age >= self.CHALLENGE_CATEGORIES["social"]["min_age"]:
                challenges.extend([
                    {
                        "id": "family_karaoke",
                        "type": "social",
                        "title": "Road Trip Singers",
                        "description": "Have a family karaoke session",
                        "points": 80,
                        "status": "available",
                        "rewards": ["Music Badge", "Song Collection"]
                    },
                    {
                        "id": "story_time",
                        "type": "social",
                        "title": "Story Creators",
                        "description": "Make up a story about your trip",
                        "points": 90,
                        "status": "available",
                        "rewards": ["Story Badge", "Digital Book"]
                    }
                ])

            # Collection challenges
            if min_age >= self.CHALLENGE_CATEGORIES["collection"]["min_age"]:
                challenges.extend([
                    {
                        "id": "state_magnets",
                        "type": "collection",
                        "title": "Magnet Collector",
                        "description": "Collect magnets from 3 states",
                        "points": 60,
                        "status": "available",
                        "rewards": ["Collector Badge", "Display Case"]
                    },
                    {
                        "id": "rock_collection",
                        "type": "collection",
                        "title": "Rock Explorer",
                        "description": "Find unique rocks from 3 places",
                        "points": 70,
                        "status": "available",
                        "rewards": ["Rock Badge", "Collection Box"]
                    }
                ])

            return challenges

        except Exception as e:
            logger.error(f"Error getting family challenges: {str(e)}")
            return []

    async def get_collectibles(
        self,
        location: Dict[str, float],
        radius_km: float
    ) -> List[Dict]:
        """Get collectible items near the current location."""
        try:
            return [
                {
                    "id": "state_badge_tx",
                    "type": "badge",
                    "category": "achievement",
                    "title": "Texas Explorer",
                    "rarity": "common",
                    "location": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"]
                    },
                    "requirements": "Enter Texas",
                    "reward_points": 50,
                    "bonus_effects": ["Unlocks Texas trivia"]
                },
                {
                    "id": "historic_token",
                    "type": "token",
                    "category": "historical",
                    "title": "History Token",
                    "rarity": "rare",
                    "location": {
                        "latitude": location["latitude"] - 0.01,
                        "longitude": location["longitude"] - 0.01
                    },
                    "requirements": "Visit historic site",
                    "reward_points": 100,
                    "bonus_effects": ["Unlocks history facts"]
                },
                {
                    "id": "nature_gem",
                    "type": "gem",
                    "category": "nature",
                    "title": "Nature's Beauty",
                    "rarity": "epic",
                    "location": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"]
                    },
                    "requirements": "Find hidden nature spot",
                    "reward_points": 200,
                    "bonus_effects": ["Nature photo boost"]
                },
                {
                    "id": "food_token",
                    "type": "token",
                    "category": "cuisine",
                    "title": "Local Flavor",
                    "rarity": "uncommon",
                    "location": {
                        "latitude": location["latitude"] + 0.02,
                        "longitude": location["longitude"] + 0.02
                    },
                    "requirements": "Try local dish",
                    "reward_points": 75,
                    "bonus_effects": ["Restaurant discounts"]
                },
                {
                    "id": "music_note",
                    "type": "note",
                    "category": "entertainment",
                    "title": "Road Trip Melody",
                    "rarity": "rare",
                    "location": {
                        "latitude": location["latitude"] - 0.02,
                        "longitude": location["longitude"] - 0.02
                    },
                    "requirements": "Complete a car karaoke",
                    "reward_points": 85,
                    "bonus_effects": ["Music playlist unlock"]
                },
                {
                    "id": "story_scroll",
                    "type": "scroll",
                    "category": "creative",
                    "title": "Travel Tale",
                    "rarity": "epic",
                    "location": {
                        "latitude": location["latitude"] + 0.03,
                        "longitude": location["longitude"] + 0.03
                    },
                    "requirements": "Write a travel story",
                    "reward_points": 150,
                    "bonus_effects": ["Story mode unlock"]
                }
            ]

        except Exception as e:
            logger.error(f"Error getting collectibles: {str(e)}")
            return []

    async def update_family_progress(
        self,
        trip_id: str,
        update_type: str,
        data: Dict
    ) -> Dict:
        """Update family progress and check for milestones."""
        try:
            if trip_id not in self.active_sessions:
                self.active_sessions[trip_id] = {
                    "challenges_completed": [],
                    "collectibles_found": [],
                    "total_points": 0,
                    "current_streak": 0,
                    "milestones": [],
                    "achievements": [],
                    "inventory": [],
                    "badges": [],
                    "special_unlocks": []
                }

            progress = self.active_sessions[trip_id]

            if update_type == "challenge_complete":
                progress["challenges_completed"].append(data["challenge_id"])
                category = data.get("category", "general")
                points = data["points"] * self.CHALLENGE_CATEGORIES.get(
                    category, {"points_multiplier": 1.0}
                )["points_multiplier"]
                progress["total_points"] += points

            elif update_type == "collectible_found":
                progress["collectibles_found"].append(data["collectible_id"])
                progress["total_points"] += data["points"]
                progress["inventory"].append({
                    "id": data["collectible_id"],
                    "found_at": datetime.now().isoformat(),
                    "location": data.get("location", {})
                })

            # Check for family milestones
            new_milestones = self._check_family_milestones(progress)
            if new_milestones:
                progress["milestones"].extend(new_milestones)
                for milestone in new_milestones:
                    if "badge" in milestone["reward"]:
                        progress["badges"].append(milestone["reward"]["badge"])
                    if "unlock" in milestone["reward"]:
                        progress["special_unlocks"].append(
                            milestone["reward"]["unlock"]
                        )

            return {
                "updated_progress": progress,
                "new_milestones": new_milestones,
                "points_earned": points if "points" in locals() else 0
            }

        except Exception as e:
            logger.error(f"Error updating family progress: {str(e)}")
            return None

    def _check_family_milestones(self, progress: Dict) -> List[Dict]:
        """Check for newly achieved family milestones."""
        try:
            milestones = []
            
            # Check points milestones
            points_thresholds = {
                500: {
                    "title": "Road Trip Rookie",
                    "reward": {"badge": "bronze_traveler", "points": 100}
                },
                1000: {
                    "title": "Family Explorer",
                    "reward": {"badge": "silver_traveler", "points": 200}
                },
                2500: {
                    "title": "Adventure Master",
                    "reward": {
                        "badge": "gold_traveler",
                        "points": 500,
                        "unlock": "special_destinations"
                    }
                }
            }

            for threshold, milestone in points_thresholds.items():
                if (
                    progress["total_points"] >= threshold and
                    milestone["title"] not in progress["milestones"]
                ):
                    milestones.append(milestone)

            return milestones

        except Exception as e:
            logger.error(f"Error checking family milestones: {str(e)}")
            return []


# Global service instance
family_gamification = FamilyGamificationService() 