"""
Game Engines for AI Road Trip Storyteller
Voice-driven interactive games for road trips
"""

from .game_engine_base import (
    BaseGameEngine,
    GameSession,
    GameAction,
    GameEvent,
    GameState,
    PlayerRole,
    DifficultyLevel,
    Player,
    GameAction,
    GameEvent
)

from .trivia_game_engine import TriviaGameEngine, TriviaQuestion, TriviaRound
from .twenty_questions_engine import TwentyQuestionsEngine, SecretItem, Question as TwentyQuestion
from .bingo_game_engine import BingoGameEngine, BingoCard, BingoItem, BingoPatternType

__all__ = [
    # Base classes
    "BaseGameEngine",
    "GameSession",
    "GameAction",
    "GameEvent",
    "GameState",
    "PlayerRole",
    "DifficultyLevel",
    "Player",
    
    # Trivia
    "TriviaGameEngine",
    "TriviaQuestion",
    "TriviaRound",
    
    # 20 Questions
    "TwentyQuestionsEngine",
    "SecretItem",
    "TwentyQuestion",
    
    # Bingo
    "BingoGameEngine",
    "BingoCard",
    "BingoItem",
    "BingoPatternType"
]
