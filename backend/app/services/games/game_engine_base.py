"""
Base Game Engine for Voice-Driven Games
Provides common infrastructure for all game types
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging
import uuid

from ...core.cache import cache_manager
from ..conversation_manager import conversation_manager
from ..audio_orchestration_service import get_audio_orchestrator, AudioPriority

logger = logging.getLogger(__name__)


class GameState(Enum):
    """Game state enum"""
    WAITING = "waiting"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PlayerRole(Enum):
    """Player roles in game"""
    HOST = "host"
    PLAYER = "player"
    SPECTATOR = "spectator"


class DifficultyLevel(Enum):
    """Game difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"
    ADAPTIVE = "adaptive"


@dataclass
class Player:
    """Game player information"""
    user_id: str
    name: str
    role: PlayerRole
    score: int = 0
    streak: int = 0
    correct_answers: int = 0
    total_answers: int = 0
    join_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameSession:
    """Game session information"""
    session_id: str
    game_type: str
    state: GameState
    players: Dict[str, Player]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_round: int = 0
    max_rounds: int = 10
    turn_order: List[str] = field(default_factory=list)
    current_turn_index: int = 0


@dataclass
class GameAction:
    """Player action in game"""
    action_id: str
    player_id: str
    action_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    voice_confidence: float = 1.0


@dataclass
class GameEvent:
    """Game event for notifications"""
    event_type: str
    session_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    broadcast: bool = True


class BaseGameEngine(ABC):
    """
    Abstract base class for all voice-driven games
    Provides common functionality for state management, multiplayer, and voice interaction
    """
    
    def __init__(self, game_type: str):
        self.game_type = game_type
        self.sessions: Dict[str, GameSession] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.voice_commands: Dict[str, Callable] = {}
        self.audio_orchestrator = get_audio_orchestrator()
        
        # Configuration
        self.min_players = 1
        self.max_players = 8
        self.session_timeout = timedelta(minutes=30)
        self.turn_timeout = timedelta(seconds=30)
        
        # Initialize game-specific components
        self._initialize_game()
        
        logger.info(f"{game_type} game engine initialized")
    
    @abstractmethod
    def _initialize_game(self):
        """Initialize game-specific components"""
        pass
    
    @abstractmethod
    async def process_game_action(
        self,
        session: GameSession,
        action: GameAction
    ) -> Dict[str, Any]:
        """Process game-specific action"""
        pass
    
    @abstractmethod
    async def generate_game_content(
        self,
        session: GameSession,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate game-specific content"""
        pass
    
    async def create_session(
        self,
        host_id: str,
        settings: Dict[str, Any] = None
    ) -> GameSession:
        """Create new game session"""
        session_id = f"{self.game_type}_{uuid.uuid4().hex[:8]}"
        
        # Create host player
        host = Player(
            user_id=host_id,
            name=settings.get("host_name", f"Player_{host_id[:4]}"),
            role=PlayerRole.HOST
        )
        
        # Create session
        session = GameSession(
            session_id=session_id,
            game_type=self.game_type,
            state=GameState.WAITING,
            players={host_id: host},
            created_at=datetime.now(),
            settings=settings or {},
            turn_order=[host_id]
        )
        
        # Store session
        self.sessions[session_id] = session
        await self._persist_session(session)
        
        # Broadcast event
        await self._broadcast_event(GameEvent(
            event_type="session_created",
            session_id=session_id,
            data={"host_id": host_id}
        ))
        
        logger.info(f"Created game session: {session_id}")
        return session
    
    async def join_session(
        self,
        session_id: str,
        player_id: str,
        player_name: Optional[str] = None
    ) -> bool:
        """Join existing game session"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Check if game already started or full
        if session.state != GameState.WAITING:
            return False
        
        if len(session.players) >= self.max_players:
            return False
        
        # Add player
        player = Player(
            user_id=player_id,
            name=player_name or f"Player_{player_id[:4]}",
            role=PlayerRole.PLAYER
        )
        
        session.players[player_id] = player
        session.turn_order.append(player_id)
        
        # Persist and broadcast
        await self._persist_session(session)
        await self._broadcast_event(GameEvent(
            event_type="player_joined",
            session_id=session_id,
            data={"player_id": player_id, "player_name": player.name}
        ))
        
        return True
    
    async def start_session(self, session_id: str) -> bool:
        """Start game session"""
        session = self.sessions.get(session_id)
        if not session or session.state != GameState.WAITING:
            return False
        
        # Check minimum players
        if len(session.players) < self.min_players:
            return False
        
        # Update state
        session.state = GameState.STARTING
        session.started_at = datetime.now()
        
        # Initialize game content
        await self._initialize_session_content(session)
        
        # Start game
        session.state = GameState.IN_PROGRESS
        await self._persist_session(session)
        
        # Broadcast
        await self._broadcast_event(GameEvent(
            event_type="game_started",
            session_id=session_id,
            data={"players": list(session.players.keys())}
        ))
        
        # Start first turn/round
        await self._start_next_turn(session)
        
        return True
    
    async def process_voice_command(
        self,
        session_id: str,
        player_id: str,
        command: str,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Process voice command from player"""
        session = self.sessions.get(session_id)
        if not session or player_id not in session.players:
            return {"error": "Invalid session or player"}
        
        # Update player activity
        session.players[player_id].last_activity = datetime.now()
        
        # Parse command intent
        intent = await self._parse_voice_intent(command, session)
        
        # Create action
        action = GameAction(
            action_id=str(uuid.uuid4()),
            player_id=player_id,
            action_type=intent["type"],
            data=intent["data"],
            voice_confidence=confidence
        )
        
        # Validate action
        if not await self._validate_action(session, action):
            return {
                "error": "Invalid action",
                "voice_response": "I didn't understand that. Please try again."
            }
        
        # Process game-specific action
        result = await self.process_game_action(session, action)
        
        # Update session
        await self._persist_session(session)
        
        # Generate voice response
        voice_response = await self._generate_voice_response(session, result)
        
        return {
            "success": True,
            "result": result,
            "voice_response": voice_response,
            "game_state": session.state.value
        }
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause game session"""
        session = self.sessions.get(session_id)
        if not session or session.state != GameState.IN_PROGRESS:
            return False
        
        session.state = GameState.PAUSED
        await self._persist_session(session)
        
        await self._broadcast_event(GameEvent(
            event_type="game_paused",
            session_id=session_id,
            data={}
        ))
        
        return True
    
    async def resume_session(self, session_id: str) -> bool:
        """Resume paused game session"""
        session = self.sessions.get(session_id)
        if not session or session.state != GameState.PAUSED:
            return False
        
        session.state = GameState.IN_PROGRESS
        await self._persist_session(session)
        
        await self._broadcast_event(GameEvent(
            event_type="game_resumed",
            session_id=session_id,
            data={}
        ))
        
        return True
    
    async def end_session(
        self,
        session_id: str,
        reason: str = "completed"
    ) -> Dict[str, Any]:
        """End game session"""
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        # Update state
        session.state = GameState.COMPLETED if reason == "completed" else GameState.ABANDONED
        session.completed_at = datetime.now()
        
        # Calculate final scores and stats
        stats = await self._calculate_final_stats(session)
        
        # Persist final state
        await self._persist_session(session)
        
        # Broadcast
        await self._broadcast_event(GameEvent(
            event_type="game_ended",
            session_id=session_id,
            data={"reason": reason, "stats": stats}
        ))
        
        # Clean up after delay
        asyncio.create_task(self._cleanup_session(session_id, delay=300))
        
        return stats
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state"""
        session = self.sessions.get(session_id)
        if not session:
            # Try to load from cache
            session = await self._load_session(session_id)
            if not session:
                return None
        
        return {
            "session_id": session.session_id,
            "game_type": session.game_type,
            "state": session.state.value,
            "players": {
                pid: {
                    "name": p.name,
                    "score": p.score,
                    "role": p.role.value
                }
                for pid, p in session.players.items()
            },
            "current_round": session.current_round,
            "max_rounds": session.max_rounds,
            "settings": session.settings,
            "metadata": session.metadata
        }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def register_voice_command(self, command: str, handler: Callable):
        """Register voice command handler"""
        self.voice_commands[command.lower()] = handler
    
    # Protected helper methods
    
    async def _initialize_session_content(self, session: GameSession):
        """Initialize game-specific content for session"""
        content = await self.generate_game_content(session, {
            "difficulty": session.settings.get("difficulty", DifficultyLevel.MEDIUM.value),
            "location": session.metadata.get("location"),
            "players": len(session.players)
        })
        session.metadata["game_content"] = content
    
    async def _start_next_turn(self, session: GameSession):
        """Start next turn in game"""
        # Get current player
        current_player_id = session.turn_order[session.current_turn_index]
        
        # Broadcast turn start
        await self._broadcast_event(GameEvent(
            event_type="turn_started",
            session_id=session.session_id,
            data={
                "player_id": current_player_id,
                "round": session.current_round,
                "timeout": self.turn_timeout.total_seconds()
            }
        ))
        
        # Set turn timer
        asyncio.create_task(self._turn_timer(session.session_id, current_player_id))
    
    async def _turn_timer(self, session_id: str, player_id: str):
        """Handle turn timeout"""
        await asyncio.sleep(self.turn_timeout.total_seconds())
        
        session = self.sessions.get(session_id)
        if not session or session.state != GameState.IN_PROGRESS:
            return
        
        # Check if still same player's turn
        current_player = session.turn_order[session.current_turn_index]
        if current_player == player_id:
            # Timeout - skip turn
            await self._advance_turn(session)
    
    async def _advance_turn(self, session: GameSession):
        """Advance to next turn"""
        # Move to next player
        session.current_turn_index = (session.current_turn_index + 1) % len(session.turn_order)
        
        # Check if round complete
        if session.current_turn_index == 0:
            session.current_round += 1
            
            # Check if game complete
            if session.current_round >= session.max_rounds:
                await self.end_session(session.session_id, "completed")
                return
        
        # Start next turn
        await self._start_next_turn(session)
    
    async def _parse_voice_intent(
        self,
        command: str,
        session: GameSession
    ) -> Dict[str, Any]:
        """Parse voice command intent"""
        command_lower = command.lower()
        
        # Check registered commands
        for cmd, handler in self.voice_commands.items():
            if cmd in command_lower:
                return await handler(command, session)
        
        # Default intent parsing
        # This would integrate with conversation manager
        intent = await conversation_manager.process_turn(
            session.session_id,
            command,
            {"game_context": session.metadata}
        )
        
        return {
            "type": intent.get("intent", "unknown"),
            "data": {"raw_command": command, **intent}
        }
    
    async def _validate_action(
        self,
        session: GameSession,
        action: GameAction
    ) -> bool:
        """Validate game action"""
        # Check if player's turn (if turn-based)
        if session.metadata.get("turn_based", False):
            current_player = session.turn_order[session.current_turn_index]
            if action.player_id != current_player:
                return False
        
        # Check game state
        if session.state != GameState.IN_PROGRESS:
            return False
        
        # Game-specific validation would go here
        return True
    
    async def _generate_voice_response(
        self,
        session: GameSession,
        result: Dict[str, Any]
    ) -> str:
        """Generate voice response for game result"""
        # This would integrate with voice personality service
        # For now, return simple response
        if result.get("correct"):
            return f"That's correct! {result.get('feedback', '')}"
        else:
            return f"Sorry, that's not right. {result.get('feedback', '')}"
    
    async def _calculate_final_stats(self, session: GameSession) -> Dict[str, Any]:
        """Calculate final game statistics"""
        stats = {
            "duration": (session.completed_at - session.started_at).total_seconds(),
            "rounds_played": session.current_round,
            "players": {}
        }
        
        # Calculate player stats
        for player_id, player in session.players.items():
            accuracy = (player.correct_answers / player.total_answers * 100) if player.total_answers > 0 else 0
            stats["players"][player_id] = {
                "name": player.name,
                "score": player.score,
                "correct_answers": player.correct_answers,
                "total_answers": player.total_answers,
                "accuracy": accuracy,
                "best_streak": player.streak
            }
        
        # Determine winner
        if session.players:
            winner = max(session.players.values(), key=lambda p: p.score)
            stats["winner"] = {
                "player_id": winner.user_id,
                "name": winner.name,
                "score": winner.score
            }
        
        return stats
    
    async def _persist_session(self, session: GameSession):
        """Persist session to cache"""
        cache_key = f"game_session:{session.session_id}"
        await cache_manager.set(cache_key, session.__dict__, ttl=3600)
    
    async def _load_session(self, session_id: str) -> Optional[GameSession]:
        """Load session from cache"""
        cache_key = f"game_session:{session_id}"
        data = await cache_manager.get(cache_key)
        if data:
            # Reconstruct session object
            return GameSession(**data)
        return None
    
    async def _cleanup_session(self, session_id: str, delay: int = 0):
        """Clean up session after delay"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Keep in cache for stats/history
        logger.info(f"Cleaned up game session: {session_id}")
    
    async def _broadcast_event(self, event: GameEvent):
        """Broadcast game event"""
        if not event.broadcast:
            return
        
        # Trigger event handlers
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
        
        # Log event
        logger.info(f"Game event: {event.event_type} for session {event.session_id}")