from typing import Dict, List
from datetime import datetime
import random

from app.core.logger import get_logger

logger = get_logger(__name__)


class FamilyExperienceService:
    """Service for managing family-specific journey features."""

    def __init__(self):
        self.active_sessions = {}
        self.achievement_templates = {
            "distance": [
                {"name": "First 50 Miles", "points": 50},
                {"name": "Century Rider", "points": 100},
                {"name": "Road Warrior", "points": 500}
            ],
            "trivia": [
                {"name": "Quiz Master", "points": 100},
                {"name": "History Buff", "points": 150},
                {"name": "Nature Expert", "points": 150}
            ],
            "stops": [
                {"name": "Explorer", "points": 50},
                {"name": "Adventure Seeker", "points": 100},
                {"name": "Landmark Spotter", "points": 150}
            ]
        }

    async def start_session(self, trip_id: str, preferences: Dict) -> Dict:
        """Initialize a new family journey session."""
        try:
            session = {
                "trip_id": trip_id,
                "start_time": datetime.now(),
                "preferences": preferences,
                "points": 0,
                "achievements": [],
                "current_streak": 0,
                "trivia_answered": 0,
                "stops_visited": [],
                "distance_covered": 0
            }
            
            self.active_sessions[trip_id] = session
            return session
            
        except Exception as e:
            logger.error(f"Error starting family session: {str(e)}")
            return None

    async def update_progress(
        self,
        trip_id: str,
        distance: float,
        trivia_correct: bool = False,
        stop_visited: str = None
    ) -> Dict:
        """Update journey progress and check for achievements."""
        try:
            if trip_id not in self.active_sessions:
                return None
                
            session = self.active_sessions[trip_id]
            
            # Update metrics
            session["distance_covered"] += distance
            if trivia_correct:
                session["trivia_answered"] += 1
                session["current_streak"] += 1
                session["points"] += 10 * session["current_streak"]
            else:
                session["current_streak"] = 0
                
            if stop_visited:
                session["stops_visited"].append(stop_visited)
                session["points"] += 50
            
            # Check for new achievements
            new_achievements = self._check_achievements(session)
            if new_achievements:
                session["achievements"].extend(new_achievements)
                session["points"] += sum(
                    a["points"] for a in new_achievements
                )
            
            return {
                "points": session["points"],
                "new_achievements": new_achievements,
                "streak": session["current_streak"],
                "total_distance": session["distance_covered"]
            }
            
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")
            return None

    def get_age_appropriate_content(
        self,
        content_type: str,
        ages: List[int]
    ) -> Dict:
        """Get age-appropriate content for activities."""
        try:
            avg_age = sum(ages) / len(ages)
            
            if content_type == "trivia":
                if avg_age < 6:
                    return self._get_young_child_trivia()
                elif avg_age < 10:
                    return self._get_older_child_trivia()
                else:
                    return self._get_teen_trivia()
                    
            elif content_type == "activities":
                return self._get_age_appropriate_activities(avg_age)
                
            return None
            
        except Exception as e:
            logger.error(
                f"Error getting age-appropriate content: {str(e)}"
            )
            return None

    def _check_achievements(self, session: Dict) -> List[Dict]:
        """Check for newly unlocked achievements."""
        new_achievements = []
        
        # Check distance achievements
        for achievement in self.achievement_templates["distance"]:
            if (
                achievement["name"] not in session["achievements"] and
                session["distance_covered"] >= achievement["points"]
            ):
                new_achievements.append(achievement)
        
        # Check trivia achievements
        for achievement in self.achievement_templates["trivia"]:
            if (
                achievement["name"] not in session["achievements"] and
                session["trivia_answered"] >= achievement["points"] / 10
            ):
                new_achievements.append(achievement)
        
        # Check stops achievements
        for achievement in self.achievement_templates["stops"]:
            if (
                achievement["name"] not in session["achievements"] and
                len(session["stops_visited"]) >= achievement["points"] / 50
            ):
                new_achievements.append(achievement)
        
        return new_achievements

    def _get_young_child_trivia(self) -> Dict:
        """Get trivia suitable for young children (5-6)."""
        questions = [
            {
                "question": "What color is the sky?",
                "options": ["Blue", "Green", "Purple"],
                "correct": "Blue",
                "fun_fact": "The sky looks blue because of sunlight!"
            },
            {
                "question": "What sound does a cow make?",
                "options": ["Moo", "Meow", "Woof"],
                "correct": "Moo",
                "fun_fact": "Cows have best friends in their herd!"
            }
        ]
        return random.choice(questions)

    def _get_older_child_trivia(self) -> Dict:
        """Get trivia suitable for older children (7-10)."""
        questions = [
            {
                "question": "Which is the largest planet?",
                "options": ["Jupiter", "Saturn", "Earth"],
                "correct": "Jupiter",
                "fun_fact": "Jupiter has a giant red spot storm!"
            },
            {
                "question": "What do plants need to grow?",
                "options": [
                    "Sunlight and water",
                    "Pizza",
                    "Television"
                ],
                "correct": "Sunlight and water",
                "fun_fact": "Plants make their own food using sunlight!"
            }
        ]
        return random.choice(questions)

    def _get_teen_trivia(self) -> Dict:
        """Get trivia suitable for teens (11+)."""
        questions = [
            {
                "question": "What causes the seasons?",
                "options": [
                    "Earth's tilt",
                    "Distance from sun",
                    "Wind patterns"
                ],
                "correct": "Earth's tilt",
                "fun_fact": "Earth is tilted at 23.5 degrees!"
            },
            {
                "question": "Which element is most abundant?",
                "options": ["Hydrogen", "Oxygen", "Carbon"],
                "correct": "Hydrogen",
                "fun_fact": "Stars are mostly made of hydrogen!"
            }
        ]
        return random.choice(questions)

    def _get_age_appropriate_activities(self, avg_age: float) -> List[Dict]:
        """Get age-appropriate activity suggestions."""
        activities = []
        
        if avg_age < 6:
            activities.extend([
                {"type": "I Spy", "duration": "5-10 min"},
                {"type": "Color Hunt", "duration": "5-10 min"},
                {"type": "Animal Spotting", "duration": "10-15 min"}
            ])
        elif avg_age < 10:
            activities.extend([
                {"type": "License Plate Game", "duration": "15-20 min"},
                {"type": "Road Trip Bingo", "duration": "20-30 min"},
                {"type": "State Facts Quiz", "duration": "10-15 min"}
            ])
        else:
            activities.extend([
                {"type": "Photography Challenge", "duration": "30 min"},
                {"type": "Travel Journal", "duration": "15-20 min"},
                {"type": "Local History Quest", "duration": "20-30 min"}
            ])
        
        return activities


# Global service instance
family_experience = FamilyExperienceService() 