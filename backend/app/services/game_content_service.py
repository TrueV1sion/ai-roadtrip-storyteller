"""
Game Content Service
Manages trivia database, dynamic question generation, and difficulty adjustment
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import asyncio
from enum import Enum
from dataclasses import dataclass
import random

from app.core.logger import logger
from app.core.cache import cache_manager
from app.core.unified_ai_client import UnifiedAIClient
from app.models.story import Location
from app.services.factVerificationService import FactVerificationService


class ContentCategory(Enum):
    HISTORY = "history"
    GEOGRAPHY = "geography"
    CULTURE = "culture"
    NATURE = "nature"
    SCIENCE = "science"
    ART = "art"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    LOCAL_TRIVIA = "local_trivia"
    FUN_FACTS = "fun_facts"


@dataclass
class TriviaContent:
    question: str
    correct_answer: str
    incorrect_answers: List[str]
    category: ContentCategory
    difficulty_score: float  # 0.0 to 1.0
    age_min: int
    age_max: int
    location_relevant: bool = False
    location_data: Optional[Dict] = None
    educational_context: Optional[str] = None
    fun_fact: Optional[str] = None
    source: Optional[str] = None


class DifficultyAdjuster:
    """Adjusts question difficulty based on player age and performance"""
    
    def __init__(self):
        self.performance_history: Dict[str, List[float]] = {}
        self.difficulty_multipliers = {
            "age": {
                (0, 8): 0.5,
                (8, 12): 0.7,
                (12, 16): 0.85,
                (16, 99): 1.0
            },
            "streak": {
                (0, 3): 1.0,
                (3, 5): 1.1,
                (5, 10): 1.2,
                (10, 999): 1.3
            }
        }
    
    def calculate_difficulty(
        self,
        base_difficulty: float,
        player_age: int,
        current_streak: int,
        performance_history: List[float]
    ) -> float:
        """Calculate adjusted difficulty for a player"""
        # Age adjustment
        age_multiplier = 1.0
        for age_range, multiplier in self.difficulty_multipliers["age"].items():
            if age_range[0] <= player_age < age_range[1]:
                age_multiplier = multiplier
                break
        
        # Streak adjustment
        streak_multiplier = 1.0
        for streak_range, multiplier in self.difficulty_multipliers["streak"].items():
            if streak_range[0] <= current_streak < streak_range[1]:
                streak_multiplier = multiplier
                break
        
        # Performance adjustment
        if performance_history:
            recent_performance = sum(performance_history[-5:]) / len(performance_history[-5:])
            if recent_performance > 0.8:
                performance_multiplier = 1.1
            elif recent_performance < 0.5:
                performance_multiplier = 0.9
            else:
                performance_multiplier = 1.0
        else:
            performance_multiplier = 1.0
        
        # Calculate final difficulty
        adjusted_difficulty = base_difficulty * age_multiplier * streak_multiplier * performance_multiplier
        return max(0.1, min(1.0, adjusted_difficulty))


class GameContentService:
    """Manages game content generation and retrieval"""
    
    def __init__(self):
        self.ai_client = UnifiedAIClient()
        self.fact_verifier = FactVerificationService()
        self.difficulty_adjuster = DifficultyAdjuster()
        self.content_cache: Dict[str, List[TriviaContent]] = {}
        self.pre_generated_questions = self._load_base_questions()
    
    def _load_base_questions(self) -> List[TriviaContent]:
        """Load pre-generated base questions"""
        # In production, this would load from a database
        # For now, we'll create some sample questions
        return [
            TriviaContent(
                question="What is the capital of the United States?",
                correct_answer="Washington, D.C.",
                incorrect_answers=["New York City", "Los Angeles", "Chicago"],
                category=ContentCategory.GEOGRAPHY,
                difficulty_score=0.2,
                age_min=8,
                age_max=99,
                educational_context="Washington, D.C. was established as the capital in 1790."
            ),
            TriviaContent(
                question="Which planet is known as the Red Planet?",
                correct_answer="Mars",
                incorrect_answers=["Venus", "Jupiter", "Saturn"],
                category=ContentCategory.SCIENCE,
                difficulty_score=0.3,
                age_min=8,
                age_max=99,
                fun_fact="Mars appears red due to iron oxide on its surface."
            ),
            # Add more base questions...
        ]
    
    async def generate_location_specific_content(
        self,
        location: Dict,
        count: int = 20,
        categories: Optional[List[ContentCategory]] = None
    ) -> List[TriviaContent]:
        """Generate location-specific trivia content"""
        cache_key = f"trivia_content:{location.get('lat')}:{location.get('lng')}"
        
        # Check cache
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached[:count]
        
        if not categories:
            categories = [
                ContentCategory.HISTORY,
                ContentCategory.GEOGRAPHY,
                ContentCategory.CULTURE,
                ContentCategory.LOCAL_TRIVIA,
                ContentCategory.FUN_FACTS
            ]
        
        prompt = f"""Generate {count} trivia questions about this location:
        Location: {location.get('name', 'Unknown')}
        Coordinates: {location['lat']}, {location['lng']}
        State/Region: {location.get('state', 'Unknown')}
        
        Categories to cover: {', '.join([c.value for c in categories])}
        
        For each question, provide:
        1. Question text
        2. Correct answer
        3. Three plausible incorrect answers
        4. Category
        5. Difficulty (0.1-1.0 scale)
        6. Age range (min-max)
        7. Educational context
        8. Fun fact (optional)
        
        Ensure questions are:
        - Factually accurate
        - Age-appropriate
        - Locally relevant when possible
        - Educational and engaging
        
        Format as JSON array.
        """
        
        response = await self.ai_client.generate_content(prompt)
        questions = await self._parse_and_verify_questions(response, location)
        
        # Cache the results
        await cache_manager.set(cache_key, questions, ttl=3600)
        
        return questions[:count]
    
    async def _parse_and_verify_questions(
        self,
        response: str,
        location: Dict
    ) -> List[TriviaContent]:
        """Parse AI response and verify facts"""
        questions = []
        
        try:
            # Parse JSON response
            question_data = json.loads(response)
            
            for q_data in question_data:
                # Verify the fact if it's historical or scientific
                if q_data.get('category') in ['history', 'science', 'geography']:
                    verification = await self.fact_verifier.verify_fact(
                        q_data['question'] + " Answer: " + q_data['correct_answer']
                    )
                    
                    if not verification['is_verified']:
                        logger.warning(f"Skipping unverified question: {q_data['question']}")
                        continue
                
                questions.append(TriviaContent(
                    question=q_data['question'],
                    correct_answer=q_data['correct_answer'],
                    incorrect_answers=q_data['incorrect_answers'],
                    category=ContentCategory(q_data['category']),
                    difficulty_score=float(q_data['difficulty']),
                    age_min=q_data['age_range']['min'],
                    age_max=q_data['age_range']['max'],
                    location_relevant=True,
                    location_data=location,
                    educational_context=q_data.get('educational_context'),
                    fun_fact=q_data.get('fun_fact'),
                    source="AI Generated"
                ))
        
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON")
            # Fallback to text parsing
            questions = self._parse_text_response(response, location)
        
        return questions
    
    def _parse_text_response(self, response: str, location: Dict) -> List[TriviaContent]:
        """Fallback text parsing method"""
        questions = []
        # Implementation for parsing non-JSON responses
        # This would parse structured text responses
        return questions
    
    async def get_questions_for_game(
        self,
        location: Dict,
        player_ages: List[int],
        count: int = 10,
        categories: Optional[List[ContentCategory]] = None,
        difficulty_range: Tuple[float, float] = (0.0, 1.0)
    ) -> List[TriviaContent]:
        """Get appropriate questions for a game session"""
        min_age = min(player_ages)
        max_age = max(player_ages)
        
        # Get location-specific questions
        location_questions = await self.generate_location_specific_content(
            location,
            count=count * 2,  # Generate extra for filtering
            categories=categories
        )
        
        # Filter by age and difficulty
        suitable_questions = [
            q for q in location_questions
            if (q.age_min <= min_age and q.age_max >= max_age and
                difficulty_range[0] <= q.difficulty_score <= difficulty_range[1])
        ]
        
        # Add some general questions if needed
        if len(suitable_questions) < count:
            general_questions = [
                q for q in self.pre_generated_questions
                if (q.age_min <= min_age and q.age_max >= max_age and
                    difficulty_range[0] <= q.difficulty_score <= difficulty_range[1])
            ]
            suitable_questions.extend(general_questions)
        
        # Shuffle and return requested count
        random.shuffle(suitable_questions)
        return suitable_questions[:count]
    
    async def generate_dynamic_question(
        self,
        topic: str,
        difficulty: float,
        age_range: Tuple[int, int],
        category: ContentCategory
    ) -> Optional[TriviaContent]:
        """Generate a single dynamic question on demand"""
        prompt = f"""Generate a single trivia question:
        Topic: {topic}
        Category: {category.value}
        Difficulty: {difficulty} (0.0-1.0 scale)
        Age range: {age_range[0]}-{age_range[1]} years old
        
        Provide:
        - Question
        - Correct answer
        - 3 incorrect answers
        - Educational context
        - Fun fact
        
        Make it engaging and educational.
        """
        
        response = await self.ai_client.generate_content(prompt)
        
        # Parse response and create TriviaContent
        # Implementation depends on response format
        return None  # Placeholder
    
    def adjust_question_difficulty(
        self,
        question: TriviaContent,
        player_age: int,
        performance: List[float]
    ) -> TriviaContent:
        """Adjust question presentation based on player"""
        # For younger players, simplify language
        if player_age < 10:
            # Could use AI to rephrase question for younger audience
            pass
        
        # Adjust time limits or hints based on performance
        # This would be used by the game engine
        
        return question
    
    async def get_educational_content(
        self,
        question: TriviaContent,
        include_extended: bool = False
    ) -> Dict[str, str]:
        """Get educational content related to a question"""
        content = {
            "context": question.educational_context or "No additional context available.",
            "fun_fact": question.fun_fact or ""
        }
        
        if include_extended and question.location_relevant:
            # Generate extended educational content
            prompt = f"""Provide educational information about:
            Question: {question.question}
            Answer: {question.correct_answer}
            Location: {question.location_data.get('name') if question.location_data else 'General'}
            
            Include:
            - Historical significance
            - Interesting facts
            - Related topics to explore
            
            Keep it concise and age-appropriate.
            """
            
            extended = await self.ai_client.generate_content(prompt)
            content["extended"] = extended
        
        return content
    
    async def create_themed_quiz(
        self,
        theme: str,
        location: Dict,
        question_count: int = 15,
        age_range: Tuple[int, int] = (8, 80)
    ) -> List[TriviaContent]:
        """Create a themed quiz (e.g., "Presidential History", "State Birds")"""
        prompt = f"""Create a themed trivia quiz:
        Theme: {theme}
        Location context: {location.get('name', 'General')}
        Number of questions: {question_count}
        Age range: {age_range[0]}-{age_range[1]}
        
        Create diverse questions within the theme.
        Include local connections where relevant.
        
        Format as JSON with same structure as before.
        """
        
        response = await self.ai_client.generate_content(prompt)
        questions = await self._parse_and_verify_questions(response, location)
        
        return questions
    
    def get_hint_for_question(
        self,
        question: TriviaContent,
        hint_level: int = 1
    ) -> str:
        """Generate hints for questions"""
        hints = []
        
        # Level 1: Category hint
        if hint_level >= 1:
            hints.append(f"This is a {question.category.value} question.")
        
        # Level 2: First letter
        if hint_level >= 2:
            hints.append(f"The answer starts with '{question.correct_answer[0]}'")
        
        # Level 3: Word count
        if hint_level >= 3:
            word_count = len(question.correct_answer.split())
            hints.append(f"The answer has {word_count} word{'s' if word_count > 1 else ''}")
        
        return " ".join(hints)


# Singleton instance
game_content_service = GameContentService()