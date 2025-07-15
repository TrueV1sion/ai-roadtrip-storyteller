"""
Trivia Game Engine for Voice-Driven Gameplay
Implements location-aware trivia with AI-generated questions
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import asyncio
import logging

from .game_engine_base import (
    BaseGameEngine,
    GameSession,
    GameAction,
    GameEvent,
    Player,
    GameState,
    DifficultyLevel
)
from ...core.enhanced_ai_client import EnhancedAIClient
from ...services.location_service import get_nearby_places
from ...services.voice_character_system import VoiceCharacterSystem

logger = logging.getLogger(__name__)


@dataclass
class TriviaQuestion:
    """Trivia question data"""
    id: str
    question: str
    options: List[str]
    correct_answer: str
    category: str
    difficulty: DifficultyLevel
    points: int
    time_limit: int
    location_context: Optional[Dict[str, Any]] = None
    fun_fact: Optional[str] = None
    image_url: Optional[str] = None
    audio_hint_url: Optional[str] = None


@dataclass
class TriviaRound:
    """Trivia round information"""
    round_number: int
    theme: str
    questions: List[TriviaQuestion]
    bonus_multiplier: float = 1.0
    time_bonus_enabled: bool = True


class TriviaGameEngine(BaseGameEngine):
    """
    Trivia game implementation with voice-driven interaction
    Supports location-based questions, multiplayer, and adaptive difficulty
    """
    
    def __init__(self, ai_client: EnhancedAIClient, voice_system: VoiceCharacterSystem):
        super().__init__("trivia")
        self.ai_client = ai_client
        self.voice_system = voice_system
        
        # Game-specific configuration
        self.questions_per_round = 5
        self.max_rounds = 4
        self.base_points = {}
        self.time_bonus_factor = 0.5
        self.streak_bonus = 10
        self.perfect_round_bonus = 50
        
        # Categories and themes
        self.categories = [
            "History", "Geography", "Science", "Culture",
            "Nature", "Technology", "Entertainment", "Sports"
        ]
        
        self.location_themes = [
            "Local History", "Regional Culture", "Nearby Landmarks",
            "State Facts", "Natural Wonders", "Famous People"
        ]
    
    def _initialize_game(self):
        """Initialize trivia-specific components"""
        # Points by difficulty
        self.base_points = {
            DifficultyLevel.EASY: 10,
            DifficultyLevel.MEDIUM: 20,
            DifficultyLevel.HARD: 30,
            DifficultyLevel.EXPERT: 50,
            DifficultyLevel.ADAPTIVE: 25
        }
        
        # Register voice commands
        self.register_voice_command("repeat question", self._handle_repeat_question)
        self.register_voice_command("hint please", self._handle_hint_request)
        self.register_voice_command("skip question", self._handle_skip_question)
        self.register_voice_command("my score", self._handle_score_request)
        
        # Voice patterns for answers
        self.answer_patterns = [
            r"(?:the answer is|my answer is|i think it's|it's) (.+)",
            r"(?:option|choice|letter) ([a-d])",
            r"^([a-d])$",
            r"^(.+)$"  # Catch-all for direct answers
        ]
    
    async def process_game_action(
        self,
        session: GameSession,
        action: GameAction
    ) -> Dict[str, Any]:
        """Process trivia-specific actions"""
        
        if action.action_type == "get_question":
            return await self._get_next_question(session, action)
        
        elif action.action_type == "submit_answer":
            return await self._process_answer(session, action)
        
        elif action.action_type == "request_hint":
            return await self._provide_hint(session, action)
        
        elif action.action_type == "skip_question":
            return await self._skip_question(session, action)
        
        return {"error": "Unknown action type"}
    
    async def generate_game_content(
        self,
        session: GameSession,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trivia questions based on location and context"""
        location = context.get("location", {})
        difficulty = DifficultyLevel(context.get("difficulty", DifficultyLevel.MEDIUM.value))
        num_players = context.get("players", 1)
        
        # Generate rounds with different themes
        rounds = []
        for i in range(self.max_rounds):
            theme = self._select_round_theme(i, location)
            questions = await self._generate_questions(
                location=location,
                theme=theme,
                count=self.questions_per_round,
                difficulty=difficulty,
                round_number=i + 1
            )
            
            rounds.append(TriviaRound(
                round_number=i + 1,
                theme=theme,
                questions=questions,
                bonus_multiplier=1.0 + (i * 0.25),  # Increasing difficulty
                time_bonus_enabled=True
            ))
        
        return {
            "rounds": rounds,
            "total_questions": len(rounds) * self.questions_per_round,
            "categories": self.categories,
            "location_context": location
        }
    
    def _select_round_theme(self, round_index: int, location: Dict[str, Any]) -> str:
        """Select theme for a round based on location and progression"""
        if round_index == 0 and location:
            # First round is always location-based
            return random.choice(self.location_themes)
        elif round_index == 1:
            # Second round is general knowledge
            return "General Knowledge"
        elif round_index == 2:
            # Third round is category-specific
            return random.choice(self.categories)
        else:
            # Final round is mixed/challenge
            return "Lightning Round"
    
    async def _generate_questions(
        self,
        location: Dict[str, Any],
        theme: str,
        count: int,
        difficulty: DifficultyLevel,
        round_number: int
    ) -> List[TriviaQuestion]:
        """Generate trivia questions using AI"""
        
        # Get location context
        nearby_places = []
        if location and "lat" in location and "lng" in location:
            nearby_places = await get_nearby_places(
                location["lat"],
                location["lng"],
                radius=10000
            )
        
        prompt = f"""
        Generate {count} trivia questions for a voice-driven game.
        
        Theme: {theme}
        Difficulty: {difficulty.value}
        Round: {round_number} of {self.max_rounds}
        Location: {location.get('name', 'Unknown')}
        Nearby landmarks: {', '.join([p['name'] for p in nearby_places[:5]])}
        
        Requirements:
        1. Questions must be clear when spoken aloud
        2. Options should be distinct and not easily confused
        3. Include a mix of question types
        4. Add a fun fact for each question
        5. Questions should be engaging and educational
        
        Format each question as:
        Q: [Question text]
        A: [Option A]
        B: [Option B]
        C: [Option C]
        D: [Option D]
        Correct: [Letter]
        Category: [Category]
        Fun Fact: [Interesting related fact]
        """
        
        response = await self.ai_client.generate_content(prompt)
        questions = self._parse_questions(response, difficulty, round_number)
        
        # Add location context to questions
        for question in questions:
            question.location_context = location
        
        return questions
    
    def _parse_questions(self, response: str, difficulty: DifficultyLevel, round_number: int) -> List[TriviaQuestion]:
        """Parse AI response into TriviaQuestion objects"""
        questions = []
        blocks = response.strip().split('\n\n')
        
        for i, block in enumerate(blocks):
            try:
                lines = block.strip().split('\n')
                if len(lines) < 8:
                    continue
                
                # Extract question components
                q_text = lines[0].replace('Q:', '').strip()
                options = [
                    lines[1].replace('A:', '').strip(),
                    lines[2].replace('B:', '').strip(),
                    lines[3].replace('C:', '').strip(),
                    lines[4].replace('D:', '').strip()
                ]
                
                correct_letter = lines[5].replace('Correct:', '').strip().upper()
                correct_idx = ord(correct_letter) - ord('A')
                correct_answer = options[correct_idx]
                
                category = lines[6].replace('Category:', '').strip()
                fun_fact = lines[7].replace('Fun Fact:', '').strip() if len(lines) > 7 else ""
                
                # Calculate points and time limit
                base_points = self.base_points[difficulty]
                points = int(base_points * (1 + (round_number - 1) * 0.25))
                
                time_limit = {
                    DifficultyLevel.EASY: 30,
                    DifficultyLevel.MEDIUM: 25,
                    DifficultyLevel.HARD: 20,
                    DifficultyLevel.EXPERT: 15,
                    DifficultyLevel.ADAPTIVE: 25
                }[difficulty]
                
                questions.append(TriviaQuestion(
                    id=f"q_{round_number}_{i}_{datetime.now().timestamp()}",
                    question=q_text,
                    options=options,
                    correct_answer=correct_answer,
                    category=category,
                    difficulty=difficulty,
                    points=points,
                    time_limit=time_limit,
                    fun_fact=fun_fact
                ))
                
            except Exception as e:
                logger.error(f"Error parsing question: {e}")
                continue
        
        return questions
    
    async def _get_next_question(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Get the next trivia question"""
        content = session.metadata.get("game_content", {})
        rounds = content.get("rounds", [])
        
        if not rounds:
            return {"error": "No questions available"}
        
        # Determine current round and question
        current_round_idx = session.current_round - 1
        if current_round_idx >= len(rounds):
            return {"game_complete": True}
        
        current_round = rounds[current_round_idx]
        question_idx = session.metadata.get("current_question_idx", 0)
        
        if question_idx >= len(current_round.questions):
            # Move to next round
            session.current_round += 1
            session.metadata["current_question_idx"] = 0
            return await self._get_next_question(session, action)
        
        question = current_round.questions[question_idx]
        session.metadata["current_question"] = question
        session.metadata["question_start_time"] = datetime.now()
        
        # Generate voice narrative
        narrative = await self._generate_question_narrative(
            question,
            session,
            current_round
        )
        
        return {
            "question": {
                "id": question.id,
                "text": question.question,
                "options": question.options,
                "category": question.category,
                "time_limit": question.time_limit,
                "points": question.points,
                "round": current_round.round_number,
                "theme": current_round.theme
            },
            "voice_narrative": narrative,
            "audio_cue": "question_start"
        }
    
    async def _process_answer(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Process a player's answer"""
        player = session.players.get(action.player_id)
        if not player:
            return {"error": "Player not found"}
        
        question = session.metadata.get("current_question")
        if not question:
            return {"error": "No active question"}
        
        # Extract answer from voice input
        answer = action.data.get("answer", "")
        if action.data.get("raw_command"):
            answer = self._extract_answer_from_voice(action.data["raw_command"])
        
        # Check if correct
        correct = self._check_answer(answer, question)
        
        # Calculate score
        points_earned = 0
        if correct:
            # Base points
            points_earned = question.points
            
            # Time bonus
            time_taken = (datetime.now() - session.metadata["question_start_time"]).total_seconds()
            if time_taken < question.time_limit:
                time_bonus = int((question.time_limit - time_taken) * self.time_bonus_factor)
                points_earned += time_bonus
            
            # Streak bonus
            player.streak += 1
            if player.streak > 1:
                points_earned += self.streak_bonus * (player.streak - 1)
            
            player.score += points_earned
            player.correct_answers += 1
        else:
            player.streak = 0
        
        player.total_answers += 1
        
        # Update metadata
        session.metadata["current_question_idx"] = session.metadata.get("current_question_idx", 0) + 1
        
        # Generate response narrative
        narrative = await self._generate_answer_narrative(
            correct,
            question,
            player,
            points_earned
        )
        
        return {
            "correct": correct,
            "correct_answer": question.correct_answer,
            "points_earned": points_earned,
            "player_score": player.score,
            "streak": player.streak,
            "fun_fact": question.fun_fact,
            "voice_narrative": narrative,
            "audio_cue": "answer_correct" if correct else "answer_incorrect"
        }
    
    def _extract_answer_from_voice(self, voice_input: str) -> str:
        """Extract answer from voice input"""
        import re
        
        voice_lower = voice_input.lower().strip()
        
        # Try each pattern
        for pattern_str in self.answer_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(voice_lower)
            if match:
                answer = match.group(1) if match.groups() else match.group(0)
                
                # Convert letter to full answer if needed
                if len(answer) == 1 and answer in 'abcd':
                    question = self.sessions[session_id].metadata.get("current_question")
                    if question:
                        idx = ord(answer.lower()) - ord('a')
                        if 0 <= idx < len(question.options):
                            return question.options[idx]
                
                return answer.strip()
        
        # Default to the full input
        return voice_input
    
    def _check_answer(self, answer: str, question: TriviaQuestion) -> bool:
        """Check if answer is correct"""
        # Normalize answers for comparison
        answer_lower = answer.lower().strip()
        correct_lower = question.correct_answer.lower().strip()
        
        # Direct match
        if answer_lower == correct_lower:
            return True
        
        # Check if answer matches any option text
        for i, option in enumerate(question.options):
            if answer_lower == option.lower().strip():
                return option == question.correct_answer
        
        # Check single letter answers
        if len(answer_lower) == 1 and answer_lower in 'abcd':
            idx = ord(answer_lower) - ord('a')
            if 0 <= idx < len(question.options):
                return question.options[idx] == question.correct_answer
        
        return False
    
    async def _provide_hint(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Provide a hint for the current question"""
        question = session.metadata.get("current_question")
        if not question:
            return {"error": "No active question"}
        
        hint_level = session.metadata.get("hint_level", 0) + 1
        session.metadata["hint_level"] = hint_level
        
        hints = [
            f"This is a {question.category} question.",
            f"The answer starts with '{question.correct_answer[0]}'.",
            f"The answer has {len(question.correct_answer.split())} words."
        ]
        
        hint = hints[min(hint_level - 1, len(hints) - 1)]
        
        # Reduce potential points for using hints
        penalty = int(question.points * 0.2 * hint_level)
        session.metadata["hint_penalty"] = session.metadata.get("hint_penalty", 0) + penalty
        
        return {
            "hint": hint,
            "hint_level": hint_level,
            "points_penalty": penalty,
            "voice_response": f"Here's a hint: {hint}"
        }
    
    async def _skip_question(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Skip the current question"""
        question = session.metadata.get("current_question")
        if not question:
            return {"error": "No active question"}
        
        # Mark as skipped
        session.metadata["current_question_idx"] = session.metadata.get("current_question_idx", 0) + 1
        
        # Reset streak for skipping player
        player = session.players.get(action.player_id)
        if player:
            player.streak = 0
        
        return {
            "skipped": True,
            "correct_answer": question.correct_answer,
            "voice_response": f"Question skipped. The answer was {question.correct_answer}."
        }
    
    async def _generate_question_narrative(
        self,
        question: TriviaQuestion,
        session: GameSession,
        round_info: TriviaRound
    ) -> str:
        """Generate engaging narrative for question presentation"""
        
        # Get current leader
        scores = [(p.name, p.score) for p in session.players.values()]
        scores.sort(key=lambda x: x[1], reverse=True)
        leader = scores[0] if scores else None
        
        narrative_parts = []
        
        # Round introduction (first question of round)
        if session.metadata.get("current_question_idx", 0) == 0:
            narrative_parts.append(f"Welcome to round {round_info.round_number}! The theme is {round_info.theme}.")
            if round_info.bonus_multiplier > 1:
                narrative_parts.append(f"Points are worth {round_info.bonus_multiplier}x in this round!")
        
        # Question setup
        narrative_parts.append(f"Question {session.metadata.get('current_question_idx', 0) + 1} from the {question.category} category:")
        narrative_parts.append(question.question)
        
        # Options
        option_letters = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question.options):
            narrative_parts.append(f"{option_letters[i]}: {option}")
        
        # Time reminder
        narrative_parts.append(f"You have {question.time_limit} seconds. Good luck!")
        
        return " ".join(narrative_parts)
    
    async def _generate_answer_narrative(
        self,
        correct: bool,
        question: TriviaQuestion,
        player: Player,
        points_earned: int
    ) -> str:
        """Generate narrative for answer result"""
        
        parts = []
        
        if correct:
            exclamations = [
                "Correct!", "That's right!", "Well done!",
                "Excellent!", "Spot on!", "Brilliant!"
            ]
            parts.append(random.choice(exclamations))
            
            if points_earned > question.points:
                parts.append(f"You earned {points_earned} points with time bonus!")
            else:
                parts.append(f"You earned {points_earned} points!")
            
            if player.streak > 1:
                parts.append(f"You're on a {player.streak} answer streak!")
        else:
            parts.append(f"Sorry, that's not correct. The answer was {question.correct_answer}.")
            if player.streak > 3:
                parts.append(f"Your {player.streak} answer streak has ended.")
        
        # Add fun fact
        if question.fun_fact:
            parts.append(f"Fun fact: {question.fun_fact}")
        
        return " ".join(parts)
    
    # Voice command handlers
    
    async def _handle_repeat_question(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle request to repeat question"""
        return {
            "type": "repeat_question",
            "data": {"action": "repeat"}
        }
    
    async def _handle_hint_request(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle hint request"""
        return {
            "type": "request_hint",
            "data": {}
        }
    
    async def _handle_skip_question(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle skip request"""
        return {
            "type": "skip_question",
            "data": {}
        }
    
    async def _handle_score_request(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle score inquiry"""
        return {
            "type": "check_score",
            "data": {}
        }
