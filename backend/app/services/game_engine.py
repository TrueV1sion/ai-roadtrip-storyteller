"""
Game Engine for AI Road Trip Storyteller
Handles trivia, scavenger hunts, achievements, and family games
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random
import asyncio
from collections import defaultdict

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.core.unified_ai_client import UnifiedAIClient
from backend.app.services.location_service import get_nearby_places


class GameType(Enum):
    TRIVIA = "trivia"
    SCAVENGER_HUNT = "scavenger_hunt"
    PHOTO_CHALLENGE = "photo_challenge"
    RIDDLE = "riddle"
    STORY_COMPLETION = "story_completion"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class AchievementType(Enum):
    STREAK = "streak"
    EXPLORER = "explorer"
    SCHOLAR = "scholar"
    PHOTOGRAPHER = "photographer"
    SPEEDSTER = "speedster"
    COMPLETIONIST = "completionist"


@dataclass
class Player:
    id: str
    name: str
    age: int
    score: int = 0
    achievements: List[str] = field(default_factory=list)
    current_streak: int = 0
    games_played: int = 0


@dataclass
class Question:
    id: str
    text: str
    options: List[str]
    correct_answer: str
    difficulty: Difficulty
    category: str
    location_context: Optional[Dict] = None
    points: int = 10
    time_limit: int = 30  # seconds


@dataclass
class ScavengerItem:
    id: str
    name: str
    description: str
    hint: str
    points: int
    location_clue: Optional[str] = None
    photo_required: bool = False
    found: bool = False
    found_by: Optional[str] = None
    found_at: Optional[datetime] = None


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str
    type: AchievementType
    requirement: Dict[str, Any]
    points: int
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None


@dataclass
class GameSession:
    id: str
    type: GameType
    players: List[Player]
    started_at: datetime
    ended_at: Optional[datetime] = None
    location: Optional[Dict] = None
    current_question: Optional[Question] = None
    questions_answered: int = 0
    scavenger_items: List[ScavengerItem] = field(default_factory=list)
    leaderboard: Dict[str, int] = field(default_factory=dict)


class TriviaGameEngine:
    """Handles location-based trivia games"""
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        self.sessions: Dict[str, GameSession] = {}
        self.question_cache: Dict[str, List[Question]] = defaultdict(list)
    
    async def generate_location_questions(
        self,
        location: Dict,
        count: int = 10,
        difficulty: Difficulty = Difficulty.MEDIUM,
        age_range: Tuple[int, int] = (8, 80)
    ) -> List[Question]:
        """Generate trivia questions based on location"""
        cache_key = f"trivia:{location.get('lat')}:{location.get('lng')}:{difficulty.value}:{age_range}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached[:count]
        
        # Get nearby places and context
        nearby_places = await get_nearby_places(
            location['lat'],
            location['lng'],
            radius=5000
        )
        
        prompt = f"""Generate {count} trivia questions about this location:
        Location: {location.get('name', 'Unknown')}
        Coordinates: {location['lat']}, {location['lng']}
        Nearby landmarks: {', '.join([p['name'] for p in nearby_places[:5]])}
        
        Requirements:
        - Age appropriate for {age_range[0]}-{age_range[1]} years old
        - Difficulty: {difficulty.value}
        - Mix of history, geography, culture, and fun facts
        - Each question should have 4 options
        - Include educational context
        
        Format each question as:
        Q: [Question text]
        A: [Option 1]
        B: [Option 2]
        C: [Option 3]
        D: [Option 4]
        Correct: [Letter]
        Category: [history/geography/culture/nature/fun_fact]
        Context: [Educational explanation]
        """
        
        response = await self.ai_client.generate_content(prompt)
        questions = self._parse_questions(response, difficulty, location)
        
        await cache_manager.set(cache_key, questions, ttl=3600)
        return questions[:count]
    
    def _parse_questions(self, response: str, difficulty: Difficulty, location: Dict) -> List[Question]:
        """Parse AI response into Question objects"""
        questions = []
        question_blocks = response.strip().split('\n\n')
        
        for i, block in enumerate(question_blocks):
            try:
                lines = block.strip().split('\n')
                if len(lines) < 7:
                    continue
                
                q_text = lines[0].replace('Q:', '').strip()
                options = [
                    lines[1].replace('A:', '').strip(),
                    lines[2].replace('B:', '').strip(),
                    lines[3].replace('C:', '').strip(),
                    lines[4].replace('D:', '').strip()
                ]
                correct_letter = lines[5].replace('Correct:', '').strip()
                correct_idx = ord(correct_letter.upper()) - ord('A')
                correct_answer = options[correct_idx]
                category = lines[6].replace('Category:', '').strip()
                
                questions.append(Question(
                    id=f"q_{i}_{datetime.now().timestamp()}",
                    text=q_text,
                    options=options,
                    correct_answer=correct_answer,
                    difficulty=difficulty,
                    category=category,
                    location_context=location,
                    points=self._calculate_points(difficulty),
                    time_limit=self._get_time_limit(difficulty)
                ))
            except Exception as e:
                logger.error(f"Error parsing question: {e}")
                continue
        
        return questions
    
    def _calculate_points(self, difficulty: Difficulty) -> int:
        """Calculate points based on difficulty"""
        points_map = {
            Difficulty.EASY: 10,
            Difficulty.MEDIUM: 20,
            Difficulty.HARD: 30,
            Difficulty.EXPERT: 50
        }
        return points_map.get(difficulty, 10)
    
    def _get_time_limit(self, difficulty: Difficulty) -> int:
        """Get time limit based on difficulty"""
        time_map = {
            Difficulty.EASY: 30,
            Difficulty.MEDIUM: 25,
            Difficulty.HARD: 20,
            Difficulty.EXPERT: 15
        }
        return time_map.get(difficulty, 30)
    
    async def start_game(
        self,
        session_id: str,
        players: List[Player],
        location: Dict,
        difficulty: Difficulty = Difficulty.MEDIUM
    ) -> GameSession:
        """Start a new trivia game session"""
        session = GameSession(
            id=session_id,
            type=GameType.TRIVIA,
            players=players,
            started_at=datetime.now(),
            location=location,
            leaderboard={p.id: 0 for p in players}
        )
        
        self.sessions[session_id] = session
        
        # Generate initial questions
        ages = [p.age for p in players]
        questions = await self.generate_location_questions(
            location,
            count=20,
            difficulty=difficulty,
            age_range=(min(ages), max(ages))
        )
        
        self.question_cache[session_id] = questions
        return session
    
    async def get_next_question(self, session_id: str) -> Optional[Question]:
        """Get the next question for the session"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        questions = self.question_cache.get(session_id, [])
        if session.questions_answered >= len(questions):
            return None
        
        question = questions[session.questions_answered]
        session.current_question = question
        return question
    
    async def generate_question(
        self,
        topic: str,
        difficulty: Difficulty = Difficulty.MEDIUM,
        location: Optional[Dict] = None
    ) -> Question:
        """Generate a single question on demand"""
        prompt = f"""Generate 1 trivia question about: {topic}
        
        Requirements:
        - Difficulty: {difficulty.value}
        - Include 4 options (A, B, C, D)
        - Make it educational and fun
        {f"- Related to location: {location.get('name', 'Unknown')}" if location else ""}
        
        Format:
        Q: [Question text]
        A: [Option 1]
        B: [Option 2]
        C: [Option 3]
        D: [Option 4]
        Correct: [Letter]
        Category: [category]
        Context: [Educational explanation]
        """
        
        response = await self.ai_client.generate_content(prompt)
        questions = self._parse_questions(response, difficulty, location or {})
        
        if questions:
            return questions[0]
        
        # Fallback question if parsing fails
        return Question(
            id=f"q_fallback_{datetime.now().timestamp()}",
            text=f"What is the capital of the United States?",
            options=["New York", "Los Angeles", "Washington D.C.", "Chicago"],
            correct_answer="Washington D.C.",
            difficulty=difficulty,
            category="geography",
            location_context=location,
            points=self._calculate_points(difficulty),
            time_limit=self._get_time_limit(difficulty)
        )
    
    async def submit_answer(
        self,
        session_id: str,
        player_id: str,
        answer: str,
        time_taken: float
    ) -> Dict[str, Any]:
        """Submit an answer and calculate score"""
        session = self.sessions.get(session_id)
        if not session or not session.current_question:
            return {"error": "Invalid session or no active question"}
        
        question = session.current_question
        player = next((p for p in session.players if p.id == player_id), None)
        if not player:
            return {"error": "Player not found"}
        
        correct = answer == question.correct_answer
        points = 0
        
        if correct:
            # Calculate points with time bonus
            base_points = question.points
            time_bonus = max(0, int((question.time_limit - time_taken) / 2))
            points = base_points + time_bonus
            
            player.score += points
            session.leaderboard[player_id] += points
            player.current_streak += 1
        else:
            player.current_streak = 0
        
        session.questions_answered += 1
        
        return {
            "correct": correct,
            "points_earned": points,
            "correct_answer": question.correct_answer,
            "player_score": player.score,
            "current_streak": player.current_streak,
            "leaderboard": sorted(
                [(pid, score) for pid, score in session.leaderboard.items()],
                key=lambda x: x[1],
                reverse=True
            )
        }


class ScavengerHuntEngine:
    """Handles exploration-based scavenger hunts"""
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        self.hunts: Dict[str, List[ScavengerItem]] = {}
    
    async def generate_hunt_items(
        self,
        location: Dict,
        radius: int = 5000,
        count: int = 10,
        theme: Optional[str] = None
    ) -> List[ScavengerItem]:
        """Generate scavenger hunt items based on location"""
        nearby_places = await get_nearby_places(
            location['lat'],
            location['lng'],
            radius=radius
        )
        
        prompt = f"""Create a scavenger hunt with {count} items near:
        Location: {location.get('name', 'Unknown')}
        Theme: {theme or 'General exploration'}
        Nearby places: {', '.join([p['name'] for p in nearby_places[:10]])}
        
        For each item, provide:
        - Name: What to find
        - Description: Detailed description
        - Hint: Clue to help find it
        - Points: 10-50 based on difficulty
        - Location clue: Vague direction/area hint
        - Photo required: true/false
        
        Mix of:
        - Physical landmarks
        - Nature elements
        - Architectural features
        - Cultural items
        - Fun challenges
        """
        
        response = await self.ai_client.generate_content(prompt)
        return self._parse_hunt_items(response)
    
    def _parse_hunt_items(self, response: str) -> List[ScavengerItem]:
        """Parse AI response into ScavengerItem objects"""
        items = []
        item_blocks = response.strip().split('\n\n')
        
        for i, block in enumerate(item_blocks):
            try:
                lines = block.strip().split('\n')
                if len(lines) < 6:
                    continue
                
                items.append(ScavengerItem(
                    id=f"item_{i}_{datetime.now().timestamp()}",
                    name=lines[0].replace('Name:', '').strip(),
                    description=lines[1].replace('Description:', '').strip(),
                    hint=lines[2].replace('Hint:', '').strip(),
                    points=int(lines[3].replace('Points:', '').strip()),
                    location_clue=lines[4].replace('Location clue:', '').strip(),
                    photo_required=lines[5].replace('Photo required:', '').strip().lower() == 'true'
                ))
            except Exception as e:
                logger.error(f"Error parsing hunt item: {e}")
                continue
        
        return items
    
    async def mark_item_found(
        self,
        hunt_id: str,
        item_id: str,
        player_id: str,
        photo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark an item as found"""
        items = self.hunts.get(hunt_id, [])
        item = next((i for i in items if i.id == item_id), None)
        
        if not item:
            return {"error": "Item not found"}
        
        if item.found:
            return {"error": "Item already found", "found_by": item.found_by}
        
        if item.photo_required and not photo_url:
            return {"error": "Photo required for this item"}
        
        item.found = True
        item.found_by = player_id
        item.found_at = datetime.now()
        
        return {
            "success": True,
            "points_earned": item.points,
            "item": item.name,
            "total_found": sum(1 for i in items if i.found),
            "total_items": len(items)
        }


class AchievementSystem:
    """Tracks and awards player achievements"""
    
    def __init__(self):
        self.achievements = self._initialize_achievements()
        self.player_achievements: Dict[str, List[str]] = defaultdict(list)
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize all available achievements"""
        return {
            "first_game": Achievement(
                id="first_game",
                name="Welcome Traveler",
                description="Play your first game",
                icon="🎮",
                type=AchievementType.COMPLETIONIST,
                requirement={"games_played": 1},
                points=10
            ),
            "trivia_streak_5": Achievement(
                id="trivia_streak_5",
                name="Quick Thinker",
                description="Answer 5 trivia questions correctly in a row",
                icon="🧠",
                type=AchievementType.STREAK,
                requirement={"streak": 5},
                points=25
            ),
            "trivia_streak_10": Achievement(
                id="trivia_streak_10",
                name="Trivia Master",
                description="Answer 10 trivia questions correctly in a row",
                icon="🏆",
                type=AchievementType.STREAK,
                requirement={"streak": 10},
                points=50
            ),
            "explorer_10": Achievement(
                id="explorer_10",
                name="Curious Explorer",
                description="Find 10 scavenger hunt items",
                icon="🔍",
                type=AchievementType.EXPLORER,
                requirement={"items_found": 10},
                points=30
            ),
            "explorer_50": Achievement(
                id="explorer_50",
                name="Master Explorer",
                description="Find 50 scavenger hunt items",
                icon="🗺️",
                type=AchievementType.EXPLORER,
                requirement={"items_found": 50},
                points=100
            ),
            "photographer_5": Achievement(
                id="photographer_5",
                name="Shutterbug",
                description="Take 5 photos for scavenger hunts",
                icon="📸",
                type=AchievementType.PHOTOGRAPHER,
                requirement={"photos_taken": 5},
                points=20
            ),
            "speed_demon": Achievement(
                id="speed_demon",
                name="Speed Demon",
                description="Answer a hard question in under 5 seconds",
                icon="⚡",
                type=AchievementType.SPEEDSTER,
                requirement={"time": 5, "difficulty": "hard"},
                points=40
            ),
            "scholar": Achievement(
                id="scholar",
                name="Road Scholar",
                description="Score 500 total points",
                icon="🎓",
                type=AchievementType.SCHOLAR,
                requirement={"total_score": 500},
                points=75
            ),
            "perfect_game": Achievement(
                id="perfect_game",
                name="Perfectionist",
                description="Complete a trivia game with 100% accuracy",
                icon="💯",
                type=AchievementType.COMPLETIONIST,
                requirement={"accuracy": 100},
                points=60
            ),
            "night_owl": Achievement(
                id="night_owl",
                name="Night Owl",
                description="Play a game after 10 PM",
                icon="🦉",
                type=AchievementType.COMPLETIONIST,
                requirement={"time_after": 22},
                points=15
            )
        }
    
    async def check_achievements(
        self,
        player: Player,
        game_stats: Dict[str, Any]
    ) -> List[Achievement]:
        """Check if player has earned any new achievements"""
        new_achievements = []
        
        for achievement_id, achievement in self.achievements.items():
            if achievement_id in self.player_achievements[player.id]:
                continue
            
            if self._check_requirement(achievement, player, game_stats):
                achievement.unlocked = True
                achievement.unlocked_at = datetime.now()
                self.player_achievements[player.id].append(achievement_id)
                player.achievements.append(achievement_id)
                new_achievements.append(achievement)
        
        return new_achievements
    
    def _check_requirement(
        self,
        achievement: Achievement,
        player: Player,
        stats: Dict[str, Any]
    ) -> bool:
        """Check if achievement requirement is met"""
        req = achievement.requirement
        
        if achievement.type == AchievementType.STREAK:
            return player.current_streak >= req.get("streak", 0)
        
        elif achievement.type == AchievementType.EXPLORER:
            return stats.get("total_items_found", 0) >= req.get("items_found", 0)
        
        elif achievement.type == AchievementType.SCHOLAR:
            return player.score >= req.get("total_score", 0)
        
        elif achievement.type == AchievementType.SPEEDSTER:
            return (stats.get("answer_time", float('inf')) <= req.get("time", 0) and
                   stats.get("difficulty", "") == req.get("difficulty", ""))
        
        elif achievement.type == AchievementType.PHOTOGRAPHER:
            return stats.get("photos_taken", 0) >= req.get("photos_taken", 0)
        
        elif achievement.type == AchievementType.COMPLETIONIST:
            if "games_played" in req:
                return player.games_played >= req["games_played"]
            elif "accuracy" in req:
                return stats.get("accuracy", 0) >= req["accuracy"]
            elif "time_after" in req:
                return datetime.now().hour >= req["time_after"]
        
        return False


class FamilyGameCoordinator:
    """Coordinates multi-player family games"""
    
    def __init__(self, trivia_engine: TriviaGameEngine, scavenger_engine: ScavengerHuntEngine):
        self.trivia_engine = trivia_engine
        self.scavenger_engine = scavenger_engine
        self.achievement_system = AchievementSystem()
        self.active_sessions: Dict[str, GameSession] = {}
    
    async def create_family_session(
        self,
        family_id: str,
        players: List[Dict[str, Any]],
        location: Dict,
        game_type: GameType = GameType.TRIVIA
    ) -> GameSession:
        """Create a new family game session"""
        player_objects = [
            Player(
                id=p["id"],
                name=p["name"],
                age=p["age"],
                score=p.get("score", 0),
                achievements=p.get("achievements", [])
            )
            for p in players
        ]
        
        session_id = f"{family_id}_{datetime.now().timestamp()}"
        
        if game_type == GameType.TRIVIA:
            # Adjust difficulty based on youngest player
            min_age = min(p.age for p in player_objects)
            difficulty = Difficulty.EASY if min_age < 10 else Difficulty.MEDIUM
            
            session = await self.trivia_engine.start_game(
                session_id,
                player_objects,
                location,
                difficulty
            )
        
        elif game_type == GameType.SCAVENGER_HUNT:
            session = GameSession(
                id=session_id,
                type=GameType.SCAVENGER_HUNT,
                players=player_objects,
                started_at=datetime.now(),
                location=location,
                leaderboard={p.id: 0 for p in player_objects}
            )
            
            # Generate hunt items
            items = await self.scavenger_engine.generate_hunt_items(
                location,
                radius=3000,
                count=15
            )
            session.scavenger_items = items
            self.scavenger_engine.hunts[session_id] = items
        
        self.active_sessions[session_id] = session
        return session
    
    async def update_game_state(
        self,
        session_id: str,
        action: str,
        player_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update game state based on player action"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        player = next((p for p in session.players if p.id == player_id), None)
        if not player:
            return {"error": "Player not found"}
        
        result = {}
        
        if session.type == GameType.TRIVIA:
            if action == "get_question":
                question = await self.trivia_engine.get_next_question(session_id)
                if question:
                    result = {
                        "question": {
                            "id": question.id,
                            "text": question.text,
                            "options": question.options,
                            "time_limit": question.time_limit,
                            "category": question.category
                        }
                    }
                else:
                    result = {"game_over": True}
            
            elif action == "submit_answer":
                answer_result = await self.trivia_engine.submit_answer(
                    session_id,
                    player_id,
                    data["answer"],
                    data["time_taken"]
                )
                result.update(answer_result)
                
                # Check achievements
                game_stats = {
                    "answer_time": data["time_taken"],
                    "difficulty": session.current_question.difficulty.value if session.current_question else None,
                    "accuracy": (player.score / (session.questions_answered * 10)) * 100 if session.questions_answered > 0 else 0
                }
                
                new_achievements = await self.achievement_system.check_achievements(
                    player,
                    game_stats
                )
                
                if new_achievements:
                    result["new_achievements"] = [
                        {
                            "name": a.name,
                            "description": a.description,
                            "icon": a.icon,
                            "points": a.points
                        }
                        for a in new_achievements
                    ]
        
        elif session.type == GameType.SCAVENGER_HUNT:
            if action == "mark_found":
                found_result = await self.scavenger_engine.mark_item_found(
                    session_id,
                    data["item_id"],
                    player_id,
                    data.get("photo_url")
                )
                result.update(found_result)
                
                if "points_earned" in found_result:
                    player.score += found_result["points_earned"]
                    session.leaderboard[player_id] += found_result["points_earned"]
                    
                    # Check explorer achievements
                    total_found = sum(1 for item in session.scavenger_items if item.found_by == player_id)
                    game_stats = {
                        "total_items_found": total_found,
                        "photos_taken": sum(1 for item in session.scavenger_items if item.found_by == player_id and item.photo_required)
                    }
                    
                    new_achievements = await self.achievement_system.check_achievements(
                        player,
                        game_stats
                    )
                    
                    if new_achievements:
                        result["new_achievements"] = [
                            {
                                "name": a.name,
                                "description": a.description,
                                "icon": a.icon,
                                "points": a.points
                            }
                            for a in new_achievements
                        ]
        
        # Update player stats
        player.games_played += 1
        
        # Add current game state to result
        result["game_state"] = {
            "leaderboard": sorted(
                [(pid, score) for pid, score in session.leaderboard.items()],
                key=lambda x: x[1],
                reverse=True
            ),
            "player_score": player.score,
            "session_progress": {
                "questions_answered": session.questions_answered if session.type == GameType.TRIVIA else None,
                "items_found": sum(1 for item in session.scavenger_items if item.found) if session.type == GameType.SCAVENGER_HUNT else None,
                "total_items": len(session.scavenger_items) if session.type == GameType.SCAVENGER_HUNT else None
            }
        }
        
        return result
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a game session and calculate final scores"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        session.ended_at = datetime.now()
        duration = (session.ended_at - session.started_at).total_seconds()
        
        # Calculate final standings
        final_standings = sorted(
            [(p, session.leaderboard[p.id]) for p in session.players],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Award completion achievements
        for player, score in final_standings:
            if session.type == GameType.TRIVIA and session.questions_answered > 0:
                accuracy = (score / (session.questions_answered * 10)) * 100
                if accuracy == 100:
                    game_stats = {"accuracy": 100}
                    await self.achievement_system.check_achievements(player, game_stats)
        
        result = {
            "session_summary": {
                "duration_minutes": int(duration / 60),
                "game_type": session.type.value,
                "final_standings": [
                    {
                        "player": p.name,
                        "score": score,
                        "achievements_earned": len([a for a in p.achievements if a not in session.players[0].achievements])
                    }
                    for p, score in final_standings
                ],
                "mvp": final_standings[0][0].name if final_standings else None
            }
        }
        
        # Clean up session
        del self.active_sessions[session_id]
        if session_id in self.trivia_engine.sessions:
            del self.trivia_engine.sessions[session_id]
        if session_id in self.scavenger_engine.hunts:
            del self.scavenger_engine.hunts[session_id]
        
        return result


# Singleton instances
ai_client = UnifiedAIClient()
trivia_engine = TriviaGameEngine(ai_client)
scavenger_engine = ScavengerHuntEngine(ai_client)
game_coordinator = FamilyGameCoordinator(trivia_engine, scavenger_engine)