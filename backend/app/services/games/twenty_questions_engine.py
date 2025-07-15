"""
20 Questions Game Engine for Voice-Driven Gameplay
AI thinks of something and players ask yes/no questions to guess it
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import asyncio
import logging
from enum import Enum

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
from ...services.voice_character_system import VoiceCharacterSystem

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of questions in 20 Questions"""
    YES_NO = "yes_no"
    GUESS = "guess"
    HINT = "hint"
    GIVE_UP = "give_up"


@dataclass
class SecretItem:
    """The secret item players are trying to guess"""
    name: str
    category: str
    description: str
    hints: List[str]
    key_attributes: Dict[str, Any]
    difficulty: DifficultyLevel
    location_relevant: bool = False
    fun_facts: List[str] = field(default_factory=list)


@dataclass
class Question:
    """A question asked by a player"""
    id: str
    player_id: str
    question_text: str
    question_type: QuestionType
    answer: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    was_helpful: bool = False


@dataclass
class GameProgress:
    """Track game progress"""
    questions_asked: int = 0
    questions_remaining: int = 20
    hints_used: int = 0
    guesses_made: int = 0
    is_solved: bool = False
    solved_by: Optional[str] = None
    solve_time: Optional[float] = None


class TwentyQuestionsEngine(BaseGameEngine):
    """
    20 Questions game implementation where AI thinks of something
    and players ask yes/no questions to guess it
    """
    
    def __init__(self, ai_client: EnhancedAIClient, voice_system: VoiceCharacterSystem):
        super().__init__("20_questions")
        self.ai_client = ai_client
        self.voice_system = voice_system
        
        # Game configuration
        self.max_questions = 20
        self.max_guesses = 3
        self.hint_cost = 2  # Questions cost for a hint
        self.categories = [
            "Animal", "Place", "Person", "Object", "Food",
            "Movie/TV", "Book", "Historical Event", "Landmark", "Vehicle"
        ]
        
        # Scoring
        self.base_score = 100
        self.question_penalty = 3
        self.hint_penalty = 10
        self.time_bonus_factor = 0.1
    
    def _initialize_game(self):
        """Initialize 20 Questions specific components"""
        # Register voice command patterns
        self.register_voice_command("is it", self._handle_yes_no_question)
        self.register_voice_command("does it", self._handle_yes_no_question)
        self.register_voice_command("can it", self._handle_yes_no_question)
        self.register_voice_command("was it", self._handle_yes_no_question)
        self.register_voice_command("i think it's", self._handle_guess)
        self.register_voice_command("is the answer", self._handle_guess)
        self.register_voice_command("hint please", self._handle_hint_request)
        self.register_voice_command("i give up", self._handle_give_up)
        self.register_voice_command("how many questions", self._handle_status_request)
    
    async def process_game_action(
        self,
        session: GameSession,
        action: GameAction
    ) -> Dict[str, Any]:
        """Process 20 Questions specific actions"""
        
        if action.action_type == "ask_question":
            return await self._process_question(session, action)
        
        elif action.action_type == "make_guess":
            return await self._process_guess(session, action)
        
        elif action.action_type == "request_hint":
            return await self._provide_hint(session, action)
        
        elif action.action_type == "give_up":
            return await self._handle_give_up_action(session, action)
        
        elif action.action_type == "get_status":
            return await self._get_game_status(session, action)
        
        return {"error": "Unknown action type"}
    
    async def generate_game_content(
        self,
        session: GameSession,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate secret items for the game"""
        location = context.get("location", {})
        difficulty = DifficultyLevel(context.get("difficulty", DifficultyLevel.MEDIUM.value))
        
        # Generate multiple secret items for multiple rounds
        items = await self._generate_secret_items(
            location=location,
            difficulty=difficulty,
            count=5
        )
        
        # Initialize game progress
        progress = GameProgress()
        
        return {
            "secret_items": items,
            "current_item_index": 0,
            "progress": progress,
            "questions_history": [],
            "categories": self.categories
        }
    
    async def _generate_secret_items(
        self,
        location: Dict[str, Any],
        difficulty: DifficultyLevel,
        count: int
    ) -> List[SecretItem]:
        """Generate secret items based on context"""
        
        prompt = f"""
        Generate {count} items for a 20 Questions game.
        
        Location context: {location.get('name', 'General')}
        Difficulty: {difficulty.value}
        
        Requirements:
        1. Mix of categories: {', '.join(self.categories)}
        2. Include both location-specific and general items
        3. Each item should be guessable but not too obvious
        4. Provide rich attributes for yes/no questions
        5. Include educational fun facts
        
        For each item provide:
        Name: [The secret item]
        Category: [From the list above]
        Description: [Brief description]
        Attributes:
        - Is_Living: [yes/no]
        - Is_Man_Made: [yes/no]
        - Size: [tiny/small/medium/large/huge]
        - Color: [primary colors or 'varies']
        - Material: [what it's made of]
        - Location: [where typically found]
        - Use: [primary purpose]
        - Age: [modern/historical/ancient]
        Hints:
        1. [Subtle hint]
        2. [Medium hint]
        3. [Obvious hint]
        Fun Facts:
        - [Interesting fact 1]
        - [Interesting fact 2]
        """
        
        response = await self.ai_client.generate_content(prompt)
        return self._parse_secret_items(response, difficulty)
    
    def _parse_secret_items(self, response: str, difficulty: DifficultyLevel) -> List[SecretItem]:
        """Parse AI response into SecretItem objects"""
        items = []
        item_blocks = response.strip().split('\n\n')
        
        for block in item_blocks:
            try:
                lines = block.strip().split('\n')
                if len(lines) < 10:
                    continue
                
                # Parse basic info
                name = ""
                category = ""
                description = ""
                attributes = {}
                hints = []
                fun_facts = []
                
                for line in lines:
                    if line.startswith('Name:'):
                        name = line.replace('Name:', '').strip()
                    elif line.startswith('Category:'):
                        category = line.replace('Category:', '').strip()
                    elif line.startswith('Description:'):
                        description = line.replace('Description:', '').strip()
                    elif line.startswith('- Is_Living:'):
                        attributes['is_living'] = 'yes' in line.lower()
                    elif line.startswith('- Is_Man_Made:'):
                        attributes['is_man_made'] = 'yes' in line.lower()
                    elif line.startswith('- Size:'):
                        attributes['size'] = line.split(':')[1].strip()
                    elif line.startswith('- Color:'):
                        attributes['color'] = line.split(':')[1].strip()
                    elif line.startswith('- Material:'):
                        attributes['material'] = line.split(':')[1].strip()
                    elif line.startswith('- Location:'):
                        attributes['location'] = line.split(':')[1].strip()
                    elif line.startswith('- Use:'):
                        attributes['use'] = line.split(':')[1].strip()
                    elif line.startswith('- Age:'):
                        attributes['age'] = line.split(':')[1].strip()
                    elif line.startswith('1.'):
                        hints.append(line[2:].strip())
                    elif line.startswith('2.'):
                        hints.append(line[2:].strip())
                    elif line.startswith('3.'):
                        hints.append(line[2:].strip())
                    elif line.startswith('- ') and 'fact' in block.lower():
                        fun_facts.append(line[2:].strip())
                
                if name and category:
                    items.append(SecretItem(
                        name=name,
                        category=category,
                        description=description,
                        hints=hints[:3],  # Ensure max 3 hints
                        key_attributes=attributes,
                        difficulty=difficulty,
                        location_relevant='location' in description.lower(),
                        fun_facts=fun_facts[:2]  # Max 2 fun facts
                    ))
                
            except Exception as e:
                logger.error(f"Error parsing secret item: {e}")
                continue
        
        return items
    
    async def _process_question(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Process a yes/no question from player"""
        content = session.metadata.get("game_content", {})
        progress = content.get("progress", GameProgress())
        
        if progress.is_solved:
            return {"error": "Game already solved"}
        
        if progress.questions_remaining <= 0:
            return {"error": "No questions remaining"}
        
        # Get current secret item
        items = content.get("secret_items", [])
        current_idx = content.get("current_item_index", 0)
        if current_idx >= len(items):
            return {"error": "No active item"}
        
        secret_item = items[current_idx]
        
        # Extract question from voice input
        question_text = action.data.get("question", "")
        if action.data.get("raw_command"):
            question_text = action.data["raw_command"]
        
        # Use AI to answer the question
        answer = await self._answer_question(question_text, secret_item)
        
        # Create question record
        question = Question(
            id=f"q_{datetime.now().timestamp()}",
            player_id=action.player_id,
            question_text=question_text,
            question_type=QuestionType.YES_NO,
            answer=answer["answer"],
            was_helpful=answer.get("helpful", False)
        )
        
        # Update progress
        progress.questions_asked += 1
        progress.questions_remaining -= 1
        content["questions_history"].append(question)
        
        # Generate voice response
        narrative = await self._generate_answer_narrative(
            question,
            answer,
            progress
        )
        
        return {
            "answer": answer["answer"],
            "questions_remaining": progress.questions_remaining,
            "voice_narrative": narrative,
            "audio_cue": "question_answered"
        }
    
    async def _answer_question(self, question: str, secret_item: SecretItem) -> Dict[str, Any]:
        """Use AI to answer yes/no question about secret item"""
        
        prompt = f"""
        You are playing 20 Questions. The secret item is: {secret_item.name}
        
        Item details:
        - Category: {secret_item.category}
        - Description: {secret_item.description}
        - Attributes: {secret_item.key_attributes}
        
        Question: {question}
        
        Answer with:
        1. YES, NO, or SOMETIMES/DEPENDS
        2. Whether this question is helpful for narrowing down the answer
        3. Brief explanation (1 sentence max)
        
        Be accurate but don't give away the answer directly.
        """
        
        response = await self.ai_client.generate_content(prompt)
        
        # Parse response
        lines = response.strip().split('\n')
        answer = "NO"  # Default
        helpful = False
        explanation = ""
        
        for line in lines:
            lower_line = line.lower()
            if any(word in lower_line for word in ['yes', 'no', 'sometimes', 'depends']):
                if 'yes' in lower_line and 'no' not in lower_line:
                    answer = "YES"
                elif 'no' in lower_line and 'yes' not in lower_line:
                    answer = "NO"
                elif 'sometimes' in lower_line or 'depends' in lower_line:
                    answer = "SOMETIMES"
            if 'helpful' in lower_line:
                helpful = True
            if '.' in line and len(line) > 10:
                explanation = line.strip()
        
        return {
            "answer": answer,
            "helpful": helpful,
            "explanation": explanation
        }
    
    async def _process_guess(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Process a guess from player"""
        content = session.metadata.get("game_content", {})
        progress = content.get("progress", GameProgress())
        
        if progress.is_solved:
            return {"error": "Game already solved"}
        
        # Get current secret item
        items = content.get("secret_items", [])
        current_idx = content.get("current_item_index", 0)
        secret_item = items[current_idx]
        
        # Extract guess
        guess = action.data.get("guess", "")
        if action.data.get("raw_command"):
            # Extract guess from voice command
            command = action.data["raw_command"].lower()
            guess = command.replace("i think it's", "").replace("is the answer", "").strip()
        
        # Check if correct
        correct = self._check_guess(guess, secret_item)
        
        progress.guesses_made += 1
        
        if correct:
            progress.is_solved = True
            progress.solved_by = action.player_id
            progress.solve_time = (datetime.now() - session.started_at).total_seconds()
            
            # Calculate score
            player = session.players.get(action.player_id)
            if player:
                score = self._calculate_score(progress)
                player.score += score
                player.correct_answers += 1
        
        # Generate response narrative
        narrative = await self._generate_guess_narrative(
            guess,
            correct,
            secret_item,
            progress
        )
        
        result = {
            "correct": correct,
            "guess": guess,
            "voice_narrative": narrative,
            "audio_cue": "guess_correct" if correct else "guess_incorrect"
        }
        
        if correct:
            result["answer"] = secret_item.name
            result["score"] = self._calculate_score(progress)
            result["fun_facts"] = secret_item.fun_facts
            
            # Move to next item if available
            if current_idx + 1 < len(items):
                content["current_item_index"] = current_idx + 1
                content["progress"] = GameProgress()
                result["next_round"] = True
            else:
                result["game_complete"] = True
        
        return result
    
    def _check_guess(self, guess: str, secret_item: SecretItem) -> bool:
        """Check if guess matches secret item"""
        guess_lower = guess.lower().strip()
        answer_lower = secret_item.name.lower().strip()
        
        # Exact match
        if guess_lower == answer_lower:
            return True
        
        # Check if guess contains the answer
        if answer_lower in guess_lower or guess_lower in answer_lower:
            return True
        
        # Check common variations
        # Remove articles
        for article in ['a ', 'an ', 'the ']:
            if guess_lower.startswith(article):
                guess_lower = guess_lower[len(article):]
            if answer_lower.startswith(article):
                answer_lower = answer_lower[len(article):]
        
        return guess_lower == answer_lower
    
    def _calculate_score(self, progress: GameProgress) -> int:
        """Calculate score based on performance"""
        score = self.base_score
        
        # Deduct for questions used
        score -= progress.questions_asked * self.question_penalty
        
        # Deduct for hints used
        score -= progress.hints_used * self.hint_penalty
        
        # Time bonus (faster = more points)
        if progress.solve_time:
            time_minutes = progress.solve_time / 60
            if time_minutes < 5:
                score += int(50 * (1 - time_minutes / 5))
        
        return max(score, 10)  # Minimum 10 points
    
    async def _provide_hint(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Provide a hint for the current item"""
        content = session.metadata.get("game_content", {})
        progress = content.get("progress", GameProgress())
        
        if progress.is_solved:
            return {"error": "Game already solved"}
        
        if progress.questions_remaining < self.hint_cost:
            return {"error": f"Not enough questions remaining. Hints cost {self.hint_cost} questions."}
        
        # Get current secret item
        items = content.get("secret_items", [])
        current_idx = content.get("current_item_index", 0)
        secret_item = items[current_idx]
        
        # Get appropriate hint
        hint_idx = min(progress.hints_used, len(secret_item.hints) - 1)
        hint = secret_item.hints[hint_idx]
        
        # Update progress
        progress.hints_used += 1
        progress.questions_remaining -= self.hint_cost
        
        return {
            "hint": hint,
            "hint_number": progress.hints_used,
            "questions_cost": self.hint_cost,
            "questions_remaining": progress.questions_remaining,
            "voice_response": f"Here's hint number {progress.hints_used}: {hint}. This cost you {self.hint_cost} questions."
        }
    
    async def _handle_give_up_action(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Handle when player gives up"""
        content = session.metadata.get("game_content", {})
        progress = content.get("progress", GameProgress())
        
        # Get current secret item
        items = content.get("secret_items", [])
        current_idx = content.get("current_item_index", 0)
        secret_item = items[current_idx]
        
        # Mark as completed without solving
        progress.is_solved = True
        
        narrative = f"The answer was {secret_item.name}! {secret_item.description} "
        if secret_item.fun_facts:
            narrative += f"Here's an interesting fact: {secret_item.fun_facts[0]}"
        
        result = {
            "gave_up": True,
            "answer": secret_item.name,
            "description": secret_item.description,
            "fun_facts": secret_item.fun_facts,
            "voice_narrative": narrative
        }
        
        # Move to next item if available
        if current_idx + 1 < len(items):
            content["current_item_index"] = current_idx + 1
            content["progress"] = GameProgress()
            result["next_round"] = True
        else:
            result["game_complete"] = True
        
        return result
    
    async def _get_game_status(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Get current game status"""
        content = session.metadata.get("game_content", {})
        progress = content.get("progress", GameProgress())
        questions_history = content.get("questions_history", [])
        
        # Get recent questions
        recent_questions = [
            {"question": q.question_text, "answer": q.answer}
            for q in questions_history[-5:]
        ]
        
        return {
            "questions_asked": progress.questions_asked,
            "questions_remaining": progress.questions_remaining,
            "hints_used": progress.hints_used,
            "guesses_made": progress.guesses_made,
            "recent_questions": recent_questions,
            "voice_response": f"You have {progress.questions_remaining} questions left. You've used {progress.hints_used} hints."
        }
    
    async def _generate_answer_narrative(self, question: Question, answer: Dict[str, Any], progress: GameProgress) -> str:
        """Generate narrative for question answer"""
        parts = [answer["answer"]]
        
        if answer["answer"] == "SOMETIMES":
            parts[0] = "Sometimes, it depends"
        
        if progress.questions_remaining <= 5:
            parts.append(f"You have {progress.questions_remaining} questions left.")
        
        if answer.get("helpful") and progress.questions_remaining > 10:
            encouragements = ["Good question!", "That narrows it down!", "You're on the right track!"]
            parts.append(random.choice(encouragements))
        
        return " ".join(parts)
    
    async def _generate_guess_narrative(self, guess: str, correct: bool, secret_item: SecretItem, progress: GameProgress) -> str:
        """Generate narrative for guess result"""
        if correct:
            parts = [
                f"Congratulations! You got it! The answer was {secret_item.name}!",
                f"You solved it in {progress.questions_asked} questions."
            ]
            
            if progress.questions_asked <= 10:
                parts.append("Excellent deduction!")
            elif progress.questions_asked <= 15:
                parts.append("Well done!")
            
            if secret_item.fun_facts:
                parts.append(f"Fun fact: {secret_item.fun_facts[0]}")
        else:
            remaining_guesses = self.max_guesses - progress.guesses_made
            parts = [
                f"Sorry, {guess} is not correct.",
                f"You have {remaining_guesses} guesses and {progress.questions_remaining} questions remaining."
            ]
            
            if remaining_guesses == 0:
                parts.append("No more guesses allowed, but you can still ask questions!")
        
        return " ".join(parts)
    
    # Voice command handlers
    
    async def _handle_yes_no_question(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle yes/no question from voice"""
        return {
            "type": "ask_question",
            "data": {"question": command}
        }
    
    async def _handle_guess(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle guess from voice"""
        return {
            "type": "make_guess",
            "data": {"raw_command": command}
        }
    
    async def _handle_hint_request(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle hint request"""
        return {
            "type": "request_hint",
            "data": {}
        }
    
    async def _handle_give_up(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle give up"""
        return {
            "type": "give_up",
            "data": {}
        }
    
    async def _handle_status_request(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle status request"""
        return {
            "type": "get_status",
            "data": {}
        }
