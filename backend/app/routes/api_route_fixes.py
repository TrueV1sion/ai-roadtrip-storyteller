"""
Fixes for failing API route tests
"""

from fastapi import HTTPException, Request, status
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimitingFixes:
    """Fixes for API rate limiting"""
    
    # Rate limiting configuration
    RATE_LIMITS = {
        "/api/games/trivia/start": {"calls": 10, "window": 60},  # 10 calls per minute
        "/api/games/trivia/session/*/answer": {"calls": 60, "window": 60},  # 1 per second
        "/api/reservations/search": {"calls": 30, "window": 60},  # 30 searches per minute
        "/api/reservations/book": {"calls": 5, "window": 60},  # 5 bookings per minute
    }
    
    # In-memory rate limit storage (use Redis in production)
    _rate_limit_storage = {}
    
    @classmethod
    async def check_rate_limit(cls, request: Request, user_id: str) -> bool:
        """
        Check if request is within rate limits
        FIX: Implement proper rate limiting
        """
        path = request.url.path
        
        # Find matching rate limit rule
        limit_config = None
        for pattern, config in cls.RATE_LIMITS.items():
            if "*" in pattern:
                # Wildcard matching
                pattern_parts = pattern.split("*")
                if all(part in path for part in pattern_parts):
                    limit_config = config
                    break
            elif path == pattern:
                limit_config = config
                break
        
        if not limit_config:
            return True  # No rate limit for this endpoint
        
        # Create storage key
        key = f"{user_id}:{path}"
        now = datetime.now()
        
        # Get or create user's request history
        if key not in cls._rate_limit_storage:
            cls._rate_limit_storage[key] = []
        
        # Clean old entries
        window_start = now - timedelta(seconds=limit_config["window"])
        cls._rate_limit_storage[key] = [
            timestamp for timestamp in cls._rate_limit_storage[key]
            if timestamp > window_start
        ]
        
        # Check if limit exceeded
        if len(cls._rate_limit_storage[key]) >= limit_config["calls"]:
            return False
        
        # Add current request
        cls._rate_limit_storage[key].append(now)
        return True
    
    @classmethod
    def create_rate_limit_middleware(cls):
        """Create rate limiting middleware"""
        async def rate_limit_middleware(request: Request, call_next):
            # Extract user ID from auth token or session
            user_id = getattr(request.state, "user_id", "anonymous")
            
            if not await cls.check_rate_limit(request, user_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            response = await call_next(request)
            return response
        
        return rate_limit_middleware


class SessionCleanupFixes:
    """Fixes for game session cleanup"""
    
    # Session timeout configuration
    SESSION_TIMEOUT_MINUTES = 30
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
    
    @staticmethod
    async def cleanup_expired_sessions(game_engines: Dict[str, Any]):
        """
        Clean up expired game sessions
        FIX: Implement automatic session cleanup
        """
        while True:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(minutes=SessionCleanupFixes.SESSION_TIMEOUT_MINUTES)
                
                # Clean up trivia sessions
                if 'trivia_engine' in game_engines:
                    trivia_engine = game_engines['trivia_engine']
                    expired_sessions = []
                    
                    for session_id, session in trivia_engine.active_sessions.items():
                        if hasattr(session, 'last_activity') and session.last_activity < timeout_threshold:
                            expired_sessions.append(session_id)
                    
                    for session_id in expired_sessions:
                        logger.info(f"Cleaning up expired trivia session: {session_id}")
                        await trivia_engine.end_session(session_id)
                
                # Clean up scavenger hunt sessions
                if 'hunt_engine' in game_engines:
                    hunt_engine = game_engines['hunt_engine']
                    expired_hunts = []
                    
                    for hunt_id, hunt in hunt_engine.active_hunts.items():
                        if 'last_activity' in hunt and hunt['last_activity'] < timeout_threshold:
                            expired_hunts.append(hunt_id)
                    
                    for hunt_id in expired_hunts:
                        logger.info(f"Cleaning up expired hunt: {hunt_id}")
                        del hunt_engine.active_hunts[hunt_id]
                
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
            
            # Wait before next cleanup
            await asyncio.sleep(SessionCleanupFixes.CLEANUP_INTERVAL_SECONDS)


class ConcurrentGameLimitFixes:
    """Fixes for concurrent game limit enforcement"""
    
    MAX_CONCURRENT_GAMES = 3
    
    @staticmethod
    async def enforce_game_limit(game_engine, user_id: int) -> bool:
        """
        Enforce concurrent game limits
        FIX: Properly track and limit concurrent games
        """
        # Count active sessions for user
        active_count = sum(
            1 for session in game_engine.active_sessions.values()
            if session.user_id == user_id and session.active
        )
        
        if active_count >= ConcurrentGameLimitFixes.MAX_CONCURRENT_GAMES:
            # Try to clean up any finished sessions
            finished_sessions = [
                sid for sid, session in game_engine.active_sessions.items()
                if session.user_id == user_id and (
                    hasattr(session, 'ended_at') and session.ended_at is not None
                )
            ]
            
            for sid in finished_sessions:
                del game_engine.active_sessions[sid]
            
            # Recount after cleanup
            active_count = sum(
                1 for session in game_engine.active_sessions.values()
                if session.user_id == user_id and session.active
            )
            
            return active_count < ConcurrentGameLimitFixes.MAX_CONCURRENT_GAMES
        
        return True


class ReservationValidationFixes:
    """Fixes for reservation API validation"""
    
    @staticmethod
    def validate_past_booking(date_time: datetime) -> None:
        """
        Validate booking is not in the past
        FIX: Add validation that was missing in routes
        """
        if date_time < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create reservations for past dates"
            )
    
    @staticmethod
    def validate_large_party(party_size: int) -> None:
        """
        Validate large party sizes
        FIX: Add special handling for large parties
        """
        if party_size > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For parties larger than 20, please contact the restaurant directly"
            )
    
    @staticmethod
    async def handle_concurrent_booking(reservation_service, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle concurrent booking attempts
        FIX: Add locking mechanism for concurrent bookings
        """
        # Create a unique lock key for the venue and time slot
        lock_key = f"{booking_data['venue_id']}:{booking_data['date_time'].strftime('%Y%m%d%H%M')}"
        
        # Use asyncio lock (in production, use distributed lock with Redis)
        if not hasattr(handle_concurrent_booking, '_locks'):
            handle_concurrent_booking._locks = {}
        
        if lock_key not in handle_concurrent_booking._locks:
            handle_concurrent_booking._locks[lock_key] = asyncio.Lock()
        
        async with handle_concurrent_booking._locks[lock_key]:
            # Check availability again inside the lock
            available = await reservation_service.check_availability(
                provider=booking_data['provider'],
                venue_id=booking_data['venue_id'],
                date=booking_data['date_time'].date(),
                party_size=booking_data['party_size']
            )
            
            time_str = booking_data['date_time'].strftime('%H:%M')
            if time_str not in available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This time slot was just booked by another user"
                )
            
            # Proceed with booking
            return await reservation_service.create_reservation(**booking_data)


# Apply fixes to routes
def apply_route_fixes(app):
    """Apply all fixes to the FastAPI routes"""
    from app.routes import games, reservations_v2
    
    # Add rate limiting middleware
    app.middleware("http")(RateLimitingFixes.create_rate_limit_middleware())
    
    # Start session cleanup task
    @app.on_event("startup")
    async def startup_event():
        # Get game engines
        game_engines = {
            'trivia_engine': getattr(games, 'trivia_engine', None),
            'hunt_engine': getattr(games, 'hunt_engine', None)
        }
        
        # Start cleanup task
        asyncio.create_task(SessionCleanupFixes.cleanup_expired_sessions(game_engines))
    
    # Wrap game creation endpoints
    if hasattr(games.router, 'routes'):
        for route in games.router.routes:
            if route.path == "/trivia/start" and route.methods == {"POST"}:
                original_endpoint = route.endpoint
                
                async def wrapped_start_game(*args, **kwargs):
                    # Get user from request
                    request = kwargs.get('request')
                    user = kwargs.get('current_user')
                    
                    if user and hasattr(games, 'trivia_engine'):
                        if not await ConcurrentGameLimitFixes.enforce_game_limit(games.trivia_engine, user.id):
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail=f"Maximum concurrent games ({ConcurrentGameLimitFixes.MAX_CONCURRENT_GAMES}) reached"
                            )
                    
                    return await original_endpoint(*args, **kwargs)
                
                route.endpoint = wrapped_start_game
    
    # Wrap reservation endpoints
    if hasattr(reservations_v2.router, 'routes'):
        for route in reservations_v2.router.routes:
            if route.path == "/book" and route.methods == {"POST"}:
                original_endpoint = route.endpoint
                
                async def wrapped_book_reservation(*args, **kwargs):
                    booking_data = kwargs.get('reservation_data', {})
                    
                    # Validate past booking
                    if 'dateTime' in booking_data:
                        date_time = datetime.fromisoformat(booking_data['dateTime'].replace('Z', '+00:00'))
                        ReservationValidationFixes.validate_past_booking(date_time)
                    
                    # Validate large party
                    if 'partySize' in booking_data:
                        ReservationValidationFixes.validate_large_party(booking_data['partySize'])
                    
                    # Handle concurrent booking with lock
                    if hasattr(reservations_v2, 'reservation_service'):
                        return await ReservationValidationFixes.handle_concurrent_booking(
                            reservations_v2.reservation_service,
                            booking_data
                        )
                    
                    return await original_endpoint(*args, **kwargs)
                
                route.endpoint = wrapped_book_reservation