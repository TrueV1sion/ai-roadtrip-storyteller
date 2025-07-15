from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
from app.core.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(
        self,
        rate: int = 50,  # requests per minute
        burst: int = 10  # burst capacity
    ):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()
        
        # Track usage per client
        self.client_usage: Dict[str, Dict] = {}
    
    async def acquire(self, client_id: Optional[str] = None) -> bool:
        """
        Attempt to acquire a token for API call.
        
        Args:
            client_id: Optional identifier for client-specific tracking
            
        Returns:
            bool: True if token acquired, False if rate limit exceeded
        """
        async with self._lock:
            now = datetime.now()
            time_passed = now - self.last_update
            
            # Replenish tokens based on time passed
            new_tokens = (time_passed.total_seconds() * self.rate) / 60
            self.tokens = min(self.burst, self.tokens + new_tokens)
            self.last_update = now
            
            # Track client usage if client_id provided
            if client_id:
                if client_id not in self.client_usage:
                    self.client_usage[client_id] = {
                        "count": 0,
                        "first_request": now
                    }
                
                # Reset count if 24 hours have passed
                client = self.client_usage[client_id]
                if now - client["first_request"] > timedelta(hours=24):
                    client["count"] = 0
                    client["first_request"] = now
                
                # Check daily limit (2500 requests per day)
                if client["count"] >= 2500:
                    logger.warning(
                        f"Daily limit exceeded for client {client_id}"
                    )
                    return False
                
                client["count"] += 1
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
                
            logger.warning("Rate limit exceeded")
            return False
    
    def get_client_usage(self, client_id: str) -> Dict:
        """Get usage statistics for a client."""
        if client_id not in self.client_usage:
            return {"count": 0, "first_request": None}
        return self.client_usage[client_id].copy()


# Global rate limiter instance
rate_limiter = RateLimiter() 