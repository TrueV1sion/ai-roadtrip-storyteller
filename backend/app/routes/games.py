"""
Game Routes
Handles trivia, scavenger hunts, achievements, and family game coordination
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.app.core.db_optimized import get_db
from backend.app.core.auth import get_current_user
from backend.app.core.logger import logger
from backend.app.models.user import User
from backend.app.services.game_engine import (
    game_coordinator,
    trivia_engine,
    scavenger_engine,
    GameType,
    Difficulty,
    Player
)
from backend.app.services.game_content_service import (
    game_content_service,
    ContentCategory
)


router = APIRouter(prefix="/games", tags=["games"])


# Request/Response Models
class CreateGameSessionRequest(BaseModel):
    game_type: GameType
    players: List[Dict[str, Any]] = Field(..., description="List of players with id, name, age")
    location: Dict[str, Any] = Field(..., description="Current location with lat, lng, name")
    difficulty: Optional[Difficulty] = Difficulty.MEDIUM
    theme: Optional[str] = None


class GameSessionResponse(BaseModel):
    session_id: str
    game_type: str
    players: List[Dict[str, Any]]
    started_at: datetime
    location: Dict[str, Any]
    status: str = "active"


class TriviaQuestionResponse(BaseModel):
    id: str
    text: str
    options: List[str]
    time_limit: int
    category: str
    points: int


class SubmitAnswerRequest(BaseModel):
    answer: str
    time_taken: float


class AnswerResultResponse(BaseModel):
    correct: bool
    points_earned: int
    correct_answer: str
    player_score: int
    current_streak: int
    leaderboard: List[Tuple[str, int]]
    new_achievements: Optional[List[Dict[str, Any]]] = None


class ScavengerItemResponse(BaseModel):
    id: str
    name: str
    description: str
    hint: str
    points: int
    location_clue: Optional[str]
    photo_required: bool
    found: bool = False
    found_by: Optional[str] = None


class MarkItemFoundRequest(BaseModel):
    item_id: str
    photo_url: Optional[str] = None


class GameStateResponse(BaseModel):
    leaderboard: List[Tuple[str, int]]
    player_score: int
    session_progress: Dict[str, Any]
    current_item: Optional[Any] = None
    game_over: bool = False


class LeaderboardEntry(BaseModel):
    player_name: str
    score: int
    games_played: int
    achievements: List[str]
    rank: int


class AchievementResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    points: int
    unlocked: bool
    unlocked_at: Optional[datetime]


# Game Session Management
@router.post("/sessions", response_model=GameSessionResponse)
async def create_game_session(
    request: CreateGameSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new game session for family or solo play"""
    try:
        # Create game session
        session = await game_coordinator.create_family_session(
            family_id=str(current_user.id),
            players=request.players,
            location=request.location,
            game_type=request.game_type
        )
        
        return GameSessionResponse(
            session_id=session.id,
            game_type=session.type.value,
            players=[{
                "id": p.id,
                "name": p.name,
                "score": p.score
            } for p in session.players],
            started_at=session.started_at,
            location=session.location
        )
    except Exception as e:
        logger.error(f"Error creating game session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=GameStateResponse)
async def get_game_state(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current state of a game session"""
    session = game_coordinator.active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return GameStateResponse(
        leaderboard=sorted(
            [(p.name, session.leaderboard[p.id]) for p in session.players],
            key=lambda x: x[1],
            reverse=True
        ),
        player_score=session.leaderboard.get(str(current_user.id), 0),
        session_progress={
            "type": session.type.value,
            "duration_minutes": int((datetime.now() - session.started_at).total_seconds() / 60),
            "questions_answered": session.questions_answered if session.type == GameType.TRIVIA else None,
            "items_found": sum(1 for item in session.scavenger_items if item.found) if session.type == GameType.SCAVENGER_HUNT else None,
            "total_items": len(session.scavenger_items) if session.type == GameType.SCAVENGER_HUNT else None
        }
    )


@router.delete("/sessions/{session_id}")
async def end_game_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """End a game session and get final results"""
    try:
        result = await game_coordinator.end_session(session_id)
        return result
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Trivia Game Endpoints
@router.get("/trivia/questions/{session_id}", response_model=TriviaQuestionResponse)
async def get_next_trivia_question(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the next trivia question for the session"""
    question = await trivia_engine.get_next_question(session_id)
    if not question:
        raise HTTPException(status_code=404, detail="No more questions available")
    
    return TriviaQuestionResponse(
        id=question.id,
        text=question.text,
        options=question.options,
        time_limit=question.time_limit,
        category=question.category,
        points=question.points
    )


@router.post("/trivia/answer/{session_id}", response_model=AnswerResultResponse)
async def submit_trivia_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit an answer to the current trivia question"""
    result = await game_coordinator.update_game_state(
        session_id=session_id,
        action="submit_answer",
        player_id=str(current_user.id),
        data={
            "answer": request.answer,
            "time_taken": request.time_taken
        }
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return AnswerResultResponse(**result)


@router.get("/trivia/categories", response_model=List[str])
async def get_available_categories():
    """Get list of available trivia categories"""
    return [cat.value for cat in ContentCategory]


@router.post("/trivia/generate-questions")
async def generate_location_questions(
    location: Dict[str, Any] = Body(...),
    count: int = Query(10, ge=5, le=50),
    categories: Optional[List[str]] = Query(None),
    age_range: Tuple[int, int] = Query((8, 80))
):
    """Generate trivia questions for a specific location"""
    try:
        category_enums = [ContentCategory(cat) for cat in (categories or [])]
        questions = await game_content_service.generate_location_specific_content(
            location=location,
            count=count,
            categories=category_enums if category_enums else None
        )
        
        return {
            "questions": [{
                "question": q.question,
                "correct_answer": q.correct_answer,
                "incorrect_answers": q.incorrect_answers,
                "category": q.category.value,
                "difficulty": q.difficulty_score,
                "educational_context": q.educational_context,
                "fun_fact": q.fun_fact
            } for q in questions]
        }
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Scavenger Hunt Endpoints
@router.get("/scavenger/items/{session_id}", response_model=List[ScavengerItemResponse])
async def get_scavenger_items(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all scavenger hunt items for a session"""
    session = game_coordinator.active_sessions.get(session_id)
    if not session or session.type != GameType.SCAVENGER_HUNT:
        raise HTTPException(status_code=404, detail="Scavenger hunt session not found")
    
    return [
        ScavengerItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            hint=item.hint,
            points=item.points,
            location_clue=item.location_clue,
            photo_required=item.photo_required,
            found=item.found,
            found_by=item.found_by
        )
        for item in session.scavenger_items
    ]


@router.post("/scavenger/found/{session_id}")
async def mark_scavenger_item_found(
    session_id: str,
    request: MarkItemFoundRequest,
    current_user: User = Depends(get_current_user)
):
    """Mark a scavenger hunt item as found"""
    result = await game_coordinator.update_game_state(
        session_id=session_id,
        action="mark_found",
        player_id=str(current_user.id),
        data={
            "item_id": request.item_id,
            "photo_url": request.photo_url
        }
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/scavenger/generate-hunt")
async def generate_scavenger_hunt(
    location: Dict[str, Any] = Body(...),
    radius: int = Query(5000, ge=1000, le=20000),
    count: int = Query(10, ge=5, le=30),
    theme: Optional[str] = Query(None)
):
    """Generate a new scavenger hunt for a location"""
    try:
        items = await scavenger_engine.generate_hunt_items(
            location=location,
            radius=radius,
            count=count,
            theme=theme
        )
        
        return {
            "items": [{
                "name": item.name,
                "description": item.description,
                "hint": item.hint,
                "points": item.points,
                "location_clue": item.location_clue,
                "photo_required": item.photo_required
            } for item in items]
        }
    except Exception as e:
        logger.error(f"Error generating scavenger hunt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Achievement Endpoints
@router.get("/achievements", response_model=List[AchievementResponse])
async def get_all_achievements(current_user: User = Depends(get_current_user)):
    """Get all available achievements and their status for the current user"""
    achievement_system = game_coordinator.achievement_system
    player_achievements = achievement_system.player_achievements.get(str(current_user.id), [])
    
    achievements = []
    for achievement_id, achievement in achievement_system.achievements.items():
        achievements.append(AchievementResponse(
            id=achievement.id,
            name=achievement.name,
            description=achievement.description,
            icon=achievement.icon,
            points=achievement.points,
            unlocked=achievement_id in player_achievements,
            unlocked_at=achievement.unlocked_at if achievement_id in player_achievements else None
        ))
    
    return achievements


@router.get("/achievements/recent", response_model=List[AchievementResponse])
async def get_recent_achievements(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50)
):
    """Get recently unlocked achievements"""
    # This would query from database in production
    achievement_system = game_coordinator.achievement_system
    player_achievements = achievement_system.player_achievements.get(str(current_user.id), [])
    
    recent = []
    for achievement_id in player_achievements[-limit:]:
        achievement = achievement_system.achievements.get(achievement_id)
        if achievement:
            recent.append(AchievementResponse(
                id=achievement.id,
                name=achievement.name,
                description=achievement.description,
                icon=achievement.icon,
                points=achievement.points,
                unlocked=True,
                unlocked_at=achievement.unlocked_at
            ))
    
    return recent


# Leaderboard Endpoints
@router.get("/leaderboard/global", response_model=List[LeaderboardEntry])
async def get_global_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get global leaderboard across all players"""
    # In production, this would query from database
    # For now, return mock data
    return [
        LeaderboardEntry(
            player_name=f"Player {i}",
            score=1000 - (i * 50),
            games_played=20 - i,
            achievements=["first_game", "trivia_streak_5"],
            rank=i
        )
        for i in range(1, min(limit + 1, 11))
    ]


@router.get("/leaderboard/friends", response_model=List[LeaderboardEntry])
async def get_friends_leaderboard(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get leaderboard among friends/family"""
    # Would query friends/family from database
    return []


@router.get("/leaderboard/session/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_leaderboard(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current session leaderboard"""
    session = game_coordinator.active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    leaderboard = sorted(
        [
            {
                "player_name": p.name,
                "score": session.leaderboard[p.id],
                "current_streak": p.current_streak,
                "rank": 0
            }
            for p in session.players
        ],
        key=lambda x: x["score"],
        reverse=True
    )
    
    # Add ranks
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return leaderboard


# Game History
@router.get("/history")
async def get_game_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    game_type: Optional[GameType] = Query(None),
    db: Session = Depends(get_db)
):
    """Get user's game history"""
    # Would query from database in production
    return {
        "games": [],
        "total_games": 0,
        "total_score": 0,
        "favorite_category": "history",
        "win_rate": 0.0
    }


# Educational Content
@router.get("/educational/{question_id}")
async def get_educational_content(
    question_id: str,
    extended: bool = Query(False)
):
    """Get educational content for a specific question"""
    # Would fetch question from cache/database
    return {
        "context": "Educational context about the question",
        "fun_fact": "An interesting related fact",
        "learn_more_url": "https://example.com/learn-more"
    }


# Themed Quizzes
@router.get("/themes", response_model=List[str])
async def get_available_themes():
    """Get list of available quiz themes"""
    return [
        "State History",
        "National Parks",
        "Presidents",
        "Science & Nature",
        "Local Legends",
        "Architecture",
        "Food & Culture",
        "Sports History",
        "Music & Arts",
        "Transportation History"
    ]


@router.post("/themed-quiz")
async def create_themed_quiz(
    theme: str = Body(...),
    location: Dict[str, Any] = Body(...),
    question_count: int = Query(15, ge=5, le=30),
    age_range: Tuple[int, int] = Query((8, 80))
):
    """Create a themed quiz"""
    try:
        questions = await game_content_service.create_themed_quiz(
            theme=theme,
            location=location,
            question_count=question_count,
            age_range=age_range
        )
        
        return {
            "theme": theme,
            "questions": [{
                "question": q.question,
                "correct_answer": q.correct_answer,
                "incorrect_answers": q.incorrect_answers,
                "category": q.category.value,
                "difficulty": q.difficulty_score
            } for q in questions]
        }
    except Exception as e:
        logger.error(f"Error creating themed quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Hints System
@router.get("/hint/{session_id}")
async def get_hint(
    session_id: str,
    hint_level: int = Query(1, ge=1, le=3),
    current_user: User = Depends(get_current_user)
):
    """Get a hint for the current question"""
    session = game_coordinator.active_sessions.get(session_id)
    if not session or not session.current_question:
        raise HTTPException(status_code=404, detail="No active question")
    
    # Would integrate with game_content_service.get_hint_for_question
    hints = {
        1: f"This is a {session.current_question.category} question.",
        2: f"The answer starts with '{session.current_question.correct_answer[0]}'",
        3: f"The answer has {len(session.current_question.correct_answer.split())} words"
    }
    
    return {"hint": hints.get(hint_level, "No more hints available")}


# Location-based triggers
@router.get("/location-triggers")
async def get_location_triggers(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius: int = Query(5000, ge=1000, le=20000)
):
    """Get game triggers for nearby locations"""
    # Would query spatial database for nearby POIs with game triggers
    return {
        "triggers": [
            {
                "location": {"lat": latitude, "lng": longitude, "name": "Historical Site"},
                "trigger_type": "auto_start_trivia",
                "game_config": {
                    "type": "trivia",
                    "theme": "Local History",
                    "questions": 5
                }
            }
        ]
    }