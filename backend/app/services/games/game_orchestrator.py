"""
Unified Game Orchestrator
Manages all game types and provides a single interface for voice interaction
"""

from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
from datetime import datetime

from .trivia_game_engine import TriviaGameEngine
from .twenty_questions_engine import TwentyQuestionsEngine
from .bingo_game_engine import BingoGameEngine
from .game_engine_base import (
    GameSession,
    GameState,
    DifficultyLevel,
    Player,
    PlayerRole
)
from ...core.enhanced_ai_client import EnhancedAIClient
from ...services.voice_character_system import VoiceCharacterSystem
from ...services.unified_voice_orchestrator import UnifiedVoiceOrchestrator
from ...core.cache import cache_manager

logger = logging.getLogger(__name__)


class GameType:
    """Available game types"""
    TRIVIA = "trivia"
    TWENTY_QUESTIONS = "20_questions"
    BINGO = "travel_bingo"
    

class GameOrchestrator:
    """
    Unified orchestrator for all voice-driven games
    Integrates with the voice orchestration system
    """
    
    def __init__(
        self,
        ai_client: EnhancedAIClient,
        voice_system: VoiceCharacterSystem,
        voice_orchestrator: Optional[UnifiedVoiceOrchestrator] = None
    ):
        self.ai_client = ai_client
        self.voice_system = voice_system
        self.voice_orchestrator = voice_orchestrator
        
        # Initialize game engines
        self.engines = {
            GameType.TRIVIA: TriviaGameEngine(ai_client, voice_system),
            GameType.TWENTY_QUESTIONS: TwentyQuestionsEngine(ai_client, voice_system),
            GameType.BINGO: BingoGameEngine(ai_client, voice_system)
        }
        
        # Active sessions tracking
        self.active_sessions: Dict[str, GameSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id mapping
        
        # Game selection AI prompt
        self.game_selection_prompt = """
        Based on the user's request, determine which game they want to play:
        - Trivia: Questions about locations, history, facts
        - 20 Questions: AI thinks of something, players guess
        - Travel Bingo: Spot items during the journey
        
        User said: {user_input}
        
        Respond with just the game type: trivia, 20_questions, or travel_bingo
        """
        
        logger.info("Game Orchestrator initialized with all game engines")
    
    async def process_voice_input(
        self,
        user_id: str,
        voice_input: str,
        location: Dict[str, float],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process voice input for games"""
        
        # Check if user has active game session
        session_id = self.user_sessions.get(user_id)
        
        if not session_id:
            # No active game, check if they want to start one
            if any(phrase in voice_input.lower() for phrase in ["play", "game", "trivia", "bingo", "20 questions"]):
                return await self._handle_game_start(user_id, voice_input, location, context)
            else:
                return {
                    "error": "No active game",
                    "voice_response": "Would you like to play a game? I have trivia, 20 questions, and travel bingo available."
                }
        
        # Get active session
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check for game control commands
        if "pause game" in voice_input.lower():
            return await self._pause_game(session_id)
        elif "end game" in voice_input.lower() or "quit game" in voice_input.lower():
            return await self._end_game(session_id)
        elif "game score" in voice_input.lower() or "my score" in voice_input.lower():
            return await self._get_game_status(session_id)
        
        # Route to appropriate game engine
        engine = self.engines.get(session.game_type)
        if not engine:
            return {"error": "Unknown game type"}
        
        # Process through game engine
        result = await engine.process_voice_command(
            session_id=session_id,
            player_id=user_id,
            command=voice_input,
            confidence=context.get("voice_confidence", 1.0)
        )
        
        # Add session info to result
        result["session_id"] = session_id
        result["game_type"] = session.game_type
        
        return result
    
    async def _handle_game_start(
        self,
        user_id: str,
        voice_input: str,
        location: Dict[str, float],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle game start request"""
        
        # Determine game type
        game_type = await self._determine_game_type(voice_input)
        
        if not game_type:
            return {
                "needs_clarification": True,
                "voice_response": "Which game would you like to play? I have trivia questions, 20 questions where I think of something, or travel bingo for spotting items."
            }
        
        # Extract player info from context
        players_data = context.get("players", [{"id": user_id, "name": "Player"}])
        difficulty = context.get("difficulty", DifficultyLevel.MEDIUM.value)
        
        # Create game session
        session = await self.create_game_session(
            game_type=game_type,
            host_id=user_id,
            players=players_data,
            location=location,
            settings={
                "difficulty": difficulty,
                "voice_enabled": True,
                "collaborative": len(players_data) > 1
            }
        )
        
        # Generate welcome message
        welcome_msg = await self._generate_game_welcome(game_type, session)
        
        # Start the game
        engine = self.engines[game_type]
        await engine.start_session(session.session_id)
        
        # Get first game prompt
        first_action = None
        if game_type == GameType.TRIVIA:
            first_action = await engine.process_voice_command(
                session.session_id,
                user_id,
                "get first question",
                1.0
            )
        elif game_type == GameType.TWENTY_QUESTIONS:
            first_action = {
                "voice_response": "I'm thinking of something. You have 20 questions to guess what it is. Ask me yes or no questions!"
            }
        elif game_type == GameType.BINGO:
            first_action = await engine.process_voice_command(
                session.session_id,
                user_id,
                "show my card",
                1.0
            )
        
        return {
            "game_started": True,
            "session_id": session.session_id,
            "game_type": game_type,
            "voice_response": welcome_msg,
            "first_action": first_action,
            "audio_cue": "game_start"
        }
    
    async def _determine_game_type(self, voice_input: str) -> Optional[str]:
        """Use AI to determine which game the user wants"""
        
        # Quick keyword matching first
        input_lower = voice_input.lower()
        if "trivia" in input_lower or "quiz" in input_lower:
            return GameType.TRIVIA
        elif "20 questions" in input_lower or "twenty questions" in input_lower or "guess what" in input_lower:
            return GameType.TWENTY_QUESTIONS
        elif "bingo" in input_lower:
            return GameType.BINGO
        
        # Use AI for ambiguous requests
        prompt = self.game_selection_prompt.format(user_input=voice_input)
        response = await self.ai_client.generate_content(prompt)
        
        response_lower = response.lower().strip()
        if "trivia" in response_lower:
            return GameType.TRIVIA
        elif "20_questions" in response_lower or "twenty" in response_lower:
            return GameType.TWENTY_QUESTIONS
        elif "bingo" in response_lower:
            return GameType.BINGO
        
        return None
    
    async def create_game_session(
        self,
        game_type: str,
        host_id: str,
        players: List[Dict[str, Any]],
        location: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> GameSession:
        """Create a new game session"""
        
        engine = self.engines.get(game_type)
        if not engine:
            raise ValueError(f"Unknown game type: {game_type}")
        
        # Create session through engine
        session = await engine.create_session(host_id, settings or {})
        
        # Add players
        for player_data in players:
            if player_data["id"] != host_id:  # Host already added
                await engine.join_session(
                    session.session_id,
                    player_data["id"],
                    player_data.get("name")
                )
        
        # Store session references
        self.active_sessions[session.session_id] = session
        for player_data in players:
            self.user_sessions[player_data["id"]] = session.session_id
        
        # Cache session for persistence
        await cache_manager.set(
            f"game_session:{session.session_id}",
            {
                "session": session.__dict__,
                "game_type": game_type,
                "started_at": datetime.now().isoformat()
            },
            ttl=7200  # 2 hours
        )
        
        logger.info(f"Created {game_type} session {session.session_id} with {len(players)} players")
        return session
    
    async def _pause_game(self, session_id: str) -> Dict[str, Any]:
        """Pause a game session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        engine = self.engines.get(session.game_type)
        success = await engine.pause_session(session_id)
        
        if success:
            return {
                "paused": True,
                "voice_response": "Game paused. Say 'resume game' when you're ready to continue.",
                "audio_cue": "game_pause"
            }
        else:
            return {"error": "Could not pause game"}
    
    async def _end_game(self, session_id: str) -> Dict[str, Any]:
        """End a game session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        engine = self.engines.get(session.game_type)
        stats = await engine.end_session(session_id)
        
        # Clean up references
        for user_id, sid in list(self.user_sessions.items()):
            if sid == session_id:
                del self.user_sessions[user_id]
        
        del self.active_sessions[session_id]
        
        # Generate summary narrative
        narrative = await self._generate_game_summary(session.game_type, stats)
        
        return {
            "game_ended": True,
            "stats": stats,
            "voice_response": narrative,
            "audio_cue": "game_end"
        }
    
    async def _get_game_status(self, session_id: str) -> Dict[str, Any]:
        """Get current game status"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        engine = self.engines.get(session.game_type)
        state = await engine.get_session_state(session_id)
        
        if not state:
            return {"error": "Could not get game state"}
        
        # Generate status narrative
        players_info = state.get("players", {})
        scores = [(p["name"], p["score"]) for p in players_info.values()]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        narrative_parts = []
        if scores:
            leader = scores[0]
            narrative_parts.append(f"{leader[0]} is in the lead with {leader[1]} points.")
        
        if state.get("current_round"):
            narrative_parts.append(f"You're on round {state['current_round']} of {state.get('max_rounds', '?')}.")
        
        return {
            "state": state,
            "voice_response": " ".join(narrative_parts) if narrative_parts else "Game is in progress."
        }
    
    async def _generate_game_welcome(self, game_type: str, session: GameSession) -> str:
        """Generate welcome message for game start"""
        
        messages = {
            GameType.TRIVIA: [
                "Welcome to Road Trip Trivia! I'll ask questions about your journey and surroundings.",
                "Let's play Trivia! Get ready for questions about places, history, and fun facts.",
                "Trivia time! I've prepared questions just for your journey."
            ],
            GameType.TWENTY_QUESTIONS: [
                "Let's play 20 Questions! I'm thinking of something, and you have to guess what it is.",
                "Welcome to 20 Questions! Ask me yes or no questions to figure out what I'm thinking of.",
                "I've got something in mind. You have 20 questions to guess what it is!"
            ],
            GameType.BINGO: [
                "Welcome to Travel Bingo! Call out items as you spot them on your journey.",
                "Let's play Travel Bingo! Keep your eyes peeled for items on your card.",
                "Bingo time! Spot items along the way and call them out to mark your card."
            ]
        }
        
        import random
        welcome = random.choice(messages.get(game_type, ["Let's play!"]))
        
        # Add player count if multiplayer
        if len(session.players) > 1:
            welcome += f" {len(session.players)} players are ready to go!"
        
        return welcome
    
    async def _generate_game_summary(self, game_type: str, stats: Dict[str, Any]) -> str:
        """Generate game end summary"""
        
        parts = ["Game over!"]
        
        # Add winner info
        if "winner" in stats:
            winner = stats["winner"]
            parts.append(f"{winner['name']} wins with {winner['score']} points!")
        
        # Add game-specific stats
        if game_type == GameType.TRIVIA:
            if "rounds_played" in stats:
                parts.append(f"You played {stats['rounds_played']} rounds.")
        elif game_type == GameType.TWENTY_QUESTIONS:
            if "questions_used" in stats:
                parts.append(f"It took {stats['questions_used']} questions to solve.")
        elif game_type == GameType.BINGO:
            if "items_spotted" in stats:
                parts.append(f"You spotted {stats['items_spotted']} items!")
        
        # Add duration
        if "duration" in stats:
            minutes = int(stats["duration"] / 60)
            parts.append(f"Total game time: {minutes} minutes.")
        
        parts.append("Thanks for playing!")
        
        return " ".join(parts)
    
    async def get_available_games(self) -> List[Dict[str, Any]]:
        """Get list of available games with descriptions"""
        return [
            {
                "type": GameType.TRIVIA,
                "name": "Road Trip Trivia",
                "description": "Answer questions about locations, history, and fun facts",
                "min_players": 1,
                "max_players": 8,
                "voice_commands": ["play trivia", "trivia game", "quiz me"]
            },
            {
                "type": GameType.TWENTY_QUESTIONS,
                "name": "20 Questions",
                "description": "Guess what the AI is thinking with yes/no questions",
                "min_players": 1,
                "max_players": 8,
                "voice_commands": ["play 20 questions", "twenty questions", "guess what I'm thinking"]
            },
            {
                "type": GameType.BINGO,
                "name": "Travel Bingo",
                "description": "Spot items during your journey and mark your card",
                "min_players": 1,
                "max_players": 4,
                "voice_commands": ["play bingo", "travel bingo", "road trip bingo"]
            }
        ]
    
    async def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume a paused or cached session"""
        
        # Check if already active
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.state == GameState.PAUSED:
                engine = self.engines.get(session.game_type)
                await engine.resume_session(session_id)
                return {
                    "resumed": True,
                    "voice_response": "Game resumed! Let's continue where we left off.",
                    "audio_cue": "game_resume"
                }
        
        # Try to load from cache
        cached = await cache_manager.get(f"game_session:{session_id}")
        if cached:
            # Reconstruct session
            # This would need proper deserialization
            return {
                "resumed": True,
                "from_cache": True,
                "voice_response": "Welcome back! I've restored your game session."
            }
        
        return {
            "error": "Session not found",
            "voice_response": "I couldn't find that game session. Would you like to start a new game?"
        }


# Singleton instance
_game_orchestrator_instance = None

def get_game_orchestrator(
    ai_client: Optional[EnhancedAIClient] = None,
    voice_system: Optional[VoiceCharacterSystem] = None,
    voice_orchestrator: Optional[UnifiedVoiceOrchestrator] = None
) -> GameOrchestrator:
    """Get or create game orchestrator instance"""
    global _game_orchestrator_instance
    
    if _game_orchestrator_instance is None:
        if not ai_client or not voice_system:
            raise ValueError("AI client and voice system required for first initialization")
        
        _game_orchestrator_instance = GameOrchestrator(
            ai_client,
            voice_system,
            voice_orchestrator
        )
    
    return _game_orchestrator_instance
