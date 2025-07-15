"""
Enhanced rate limiting with dynamic adjustment and user tiers.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from collections import defaultdict, deque
from enum import Enum
import json

from fastapi import Request, HTTPException, status
from starlette.responses import Response

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.monitoring.security_monitor import security_monitor, SecurityEvent, SecurityEventType, SecurityEventSeverity

logger = get_logger(__name__)


class RateLimitTier(Enum):
    """User rate limit tiers."""
    ANONYMOUS = "anonymous"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


class RateLimitConfig:
    """Rate limit configuration for different tiers."""
    
    # Requests per minute
    TIER_LIMITS = {
        RateLimitTier.ANONYMOUS: {
            "requests_per_minute": 20,
            "requests_per_hour": 100,
            "requests_per_day": 500,
            "burst_size": 5,
            "concurrent_requests": 2,
        },
        RateLimitTier.BASIC: {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000,
            "burst_size": 10,
            "concurrent_requests": 5,
        },
        RateLimitTier.PREMIUM: {
            "requests_per_minute": 300,
            "requests_per_hour": 10000,
            "requests_per_day": 100000,
            "burst_size": 50,
            "concurrent_requests": 20,
        },
        RateLimitTier.ENTERPRISE: {
            "requests_per_minute": 1000,
            "requests_per_hour": 50000,
            "requests_per_day": 1000000,
            "burst_size": 100,
            "concurrent_requests": 100,
        },
        RateLimitTier.ADMIN: {
            "requests_per_minute": 10000,
            "requests_per_hour": 500000,
            "requests_per_day": 10000000,
            "burst_size": 1000,
            "concurrent_requests": 1000,
        },
    }
    
    # Endpoint-specific limits (override tier limits)
    ENDPOINT_LIMITS = {
        "/api/auth/login": {
            "requests_per_minute": 5,
            "requests_per_hour": 20,
            "penalty_on_exceed": 300,  # 5 minutes
        },
        "/api/auth/register": {
            "requests_per_minute": 3,
            "requests_per_hour": 10,
            "penalty_on_exceed": 600,  # 10 minutes
        },
        "/api/export": {
            "requests_per_minute": 1,
            "requests_per_hour": 5,
            "requests_per_day": 20,
        },
        "/api/ai": {
            "requests_per_minute": 10,
            "cost_based": True,  # Track AI API costs
        },
    }
    
    # Dynamic adjustment factors
    ADJUSTMENT_FACTORS = {
        "high_load": 0.5,  # Reduce limits by 50% during high load
        "attack_detected": 0.2,  # Reduce limits by 80% during attacks
        "off_peak": 1.5,  # Increase limits by 50% during off-peak
    }


class TokenBucket:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket."""
        async with self._lock:
            # Refill bucket
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now
            
            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def available_tokens(self) -> float:
        """Get available tokens without consuming."""
        now = time.time()
        elapsed = now - self.last_refill
        return min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )


class RateLimitTracker:
    """Track rate limit usage and violations."""
    
    def __init__(self):
        self.request_history = defaultdict(lambda: deque(maxlen=10000))
        self.violation_history = defaultdict(list)
        self.concurrent_requests = defaultdict(int)
        self.cost_tracking = defaultdict(float)
        
    def add_request(self, key: str, timestamp: datetime, cost: float = 0.0):
        """Add request to history."""
        self.request_history[key].append({
            "timestamp": timestamp,
            "cost": cost
        })
        
        if cost > 0:
            self.cost_tracking[key] += cost
    
    def add_violation(self, key: str, violation_type: str):
        """Record rate limit violation."""
        self.violation_history[key].append({
            "timestamp": datetime.utcnow(),
            "type": violation_type
        })
    
    def get_request_count(self, key: str, window_seconds: int) -> int:
        """Get request count in time window."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        return sum(
            1 for req in self.request_history[key]
            if req["timestamp"] > cutoff
        )
    
    def get_violation_count(self, key: str, window_seconds: int) -> int:
        """Get violation count in time window."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        return sum(
            1 for v in self.violation_history[key]
            if v["timestamp"] > cutoff
        )


class EnhancedRateLimiter:
    """Enhanced rate limiter with multiple strategies."""
    
    def __init__(self):
        self.config = RateLimitConfig()
        self.tracker = RateLimitTracker()
        self.token_buckets = {}
        self.blocked_keys = {}
        self.dynamic_adjustments = {}
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "rate_limited_requests": 0,
            "blocked_requests": 0,
        }
    
    def get_user_tier(self, user_id: Optional[str], user_role: Optional[str]) -> RateLimitTier:
        """Determine user's rate limit tier."""
        if not user_id:
            return RateLimitTier.ANONYMOUS
        
        if user_role == "admin" or user_role == "super_admin":
            return RateLimitTier.ADMIN
        elif user_role == "enterprise":
            return RateLimitTier.ENTERPRISE
        elif user_role == "premium":
            return RateLimitTier.PREMIUM
        
        return RateLimitTier.BASIC
    
    def get_rate_limit_key(self, request: Request, user_id: Optional[str]) -> str:
        """Generate rate limit key."""
        if user_id:
            return f"user:{user_id}"
        
        # Use IP for anonymous users
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        endpoint_cost: float = 1.0
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if request is within rate limits.
        
        Returns:
            (allowed, rate_limit_info)
        """
        self.metrics["total_requests"] += 1
        
        # Get rate limit key and tier
        key = self.get_rate_limit_key(request, user_id)
        tier = self.get_user_tier(user_id, user_role)
        endpoint = request.url.path
        
        # Check if key is blocked
        if await self._is_blocked(key):
            self.metrics["blocked_requests"] += 1
            return False, {"reason": "blocked", "retry_after": self.blocked_keys.get(key)}
        
        # Get applicable limits
        limits = self._get_effective_limits(tier, endpoint)
        
        # Check concurrent requests
        if not await self._check_concurrent_requests(key, limits):
            return False, {"reason": "concurrent_limit_exceeded"}
        
        # Check rate limits using token bucket
        bucket_key = f"{key}:{endpoint}"
        if bucket_key not in self.token_buckets:
            self.token_buckets[bucket_key] = TokenBucket(
                capacity=limits.get("burst_size", 10),
                refill_rate=limits["requests_per_minute"] / 60.0
            )
        
        bucket = self.token_buckets[bucket_key]
        
        # Try to consume tokens
        if not await bucket.consume(endpoint_cost):
            self.metrics["rate_limited_requests"] += 1
            
            # Record violation
            self.tracker.add_violation(key, "rate_limit_exceeded")
            
            # Check for repeated violations
            violation_count = self.tracker.get_violation_count(key, 3600)  # 1 hour
            if violation_count > 10:
                await self._block_key(key, 3600)  # Block for 1 hour
                await self._report_abuse(key, user_id, violation_count)
            
            # Calculate retry after
            retry_after = self._calculate_retry_after(bucket, endpoint_cost)
            
            return False, {
                "reason": "rate_limit_exceeded",
                "retry_after": retry_after,
                "limit": limits["requests_per_minute"],
                "remaining": int(bucket.available_tokens()),
                "reset": int(time.time() + retry_after)
            }
        
        # Track request
        self.tracker.add_request(key, datetime.utcnow(), endpoint_cost)
        
        # Update concurrent requests
        self.tracker.concurrent_requests[key] += 1
        
        # Return rate limit info
        return True, {
            "limit": limits["requests_per_minute"],
            "remaining": int(bucket.available_tokens()),
            "reset": int(time.time() + 60),
            "tier": tier.value
        }
    
    async def release_concurrent_request(self, request: Request, user_id: Optional[str] = None):
        """Release concurrent request slot."""
        key = self.get_rate_limit_key(request, user_id)
        if self.tracker.concurrent_requests[key] > 0:
            self.tracker.concurrent_requests[key] -= 1
    
    def _get_effective_limits(self, tier: RateLimitTier, endpoint: str) -> Dict[str, Any]:
        """Get effective rate limits considering tier and endpoint."""
        # Start with tier limits
        limits = self.config.TIER_LIMITS[tier].copy()
        
        # Apply endpoint-specific limits
        if endpoint in self.config.ENDPOINT_LIMITS:
            endpoint_limits = self.config.ENDPOINT_LIMITS[endpoint]
            for key, value in endpoint_limits.items():
                if key != "cost_based":
                    limits[key] = min(limits.get(key, float('inf')), value)
        
        # Apply dynamic adjustments
        for adjustment_type, factor in self.dynamic_adjustments.items():
            for key in ["requests_per_minute", "requests_per_hour", "requests_per_day"]:
                if key in limits:
                    limits[key] = int(limits[key] * factor)
        
        return limits
    
    async def _check_concurrent_requests(self, key: str, limits: Dict[str, Any]) -> bool:
        """Check concurrent request limit."""
        current = self.tracker.concurrent_requests.get(key, 0)
        limit = limits.get("concurrent_requests", 10)
        return current < limit
    
    async def _is_blocked(self, key: str) -> bool:
        """Check if key is blocked."""
        if key in self.blocked_keys:
            if time.time() < self.blocked_keys[key]:
                return True
            else:
                del self.blocked_keys[key]
        
        # Check cache for distributed blocking
        cache_key = f"rate_limit_blocked:{key}"
        is_blocked = await cache_manager.exists(cache_key)
        return is_blocked
    
    async def _block_key(self, key: str, duration: int):
        """Block a key for specified duration."""
        expiry = time.time() + duration
        self.blocked_keys[key] = expiry
        
        # Store in cache for distributed blocking
        cache_key = f"rate_limit_blocked:{key}"
        await cache_manager.set(cache_key, "1", ttl=duration)
        
        logger.warning(f"Blocked key {key} for {duration} seconds")
    
    async def _report_abuse(self, key: str, user_id: Optional[str], violation_count: int):
        """Report rate limit abuse to security monitor."""
        event = SecurityEvent(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecurityEventSeverity.MEDIUM,
            user_id=user_id,
            ip_address=key.split(":")[-1] if key.startswith("ip:") else None,
            details={
                "violation_count": violation_count,
                "key": key,
                "action": "blocked"
            }
        )
        await security_monitor.log_event(event)
    
    def _calculate_retry_after(self, bucket: TokenBucket, tokens_needed: float) -> int:
        """Calculate seconds until tokens are available."""
        available = bucket.available_tokens()
        if available >= tokens_needed:
            return 0
        
        tokens_deficit = tokens_needed - available
        seconds_needed = tokens_deficit / bucket.refill_rate
        
        return max(1, int(seconds_needed))
    
    def set_dynamic_adjustment(self, adjustment_type: str, factor: float):
        """Set dynamic rate limit adjustment."""
        if adjustment_type in self.config.ADJUSTMENT_FACTORS:
            self.dynamic_adjustments[adjustment_type] = factor
            logger.info(f"Set rate limit adjustment: {adjustment_type} = {factor}")
    
    def remove_dynamic_adjustment(self, adjustment_type: str):
        """Remove dynamic rate limit adjustment."""
        if adjustment_type in self.dynamic_adjustments:
            del self.dynamic_adjustments[adjustment_type]
            logger.info(f"Removed rate limit adjustment: {adjustment_type}")
    
    async def get_usage_stats(self, key: str) -> Dict[str, Any]:
        """Get usage statistics for a key."""
        return {
            "requests_last_minute": self.tracker.get_request_count(key, 60),
            "requests_last_hour": self.tracker.get_request_count(key, 3600),
            "requests_last_day": self.tracker.get_request_count(key, 86400),
            "violations_last_hour": self.tracker.get_violation_count(key, 3600),
            "is_blocked": await self._is_blocked(key),
            "concurrent_requests": self.tracker.concurrent_requests.get(key, 0),
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics."""
        return {
            **self.metrics,
            "active_buckets": len(self.token_buckets),
            "blocked_keys": len(self.blocked_keys),
            "tracked_keys": len(self.tracker.request_history),
        }


# Middleware function
async def rate_limit_middleware(
    request: Request,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    cost: float = 1.0
):
    """Rate limiting middleware function."""
    rate_limiter = enhanced_rate_limiter
    
    # Check rate limit
    allowed, info = await rate_limiter.check_rate_limit(
        request, user_id, user_role, cost
    )
    
    if not allowed:
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(info.get("limit", 0)),
            "X-RateLimit-Remaining": str(info.get("remaining", 0)),
            "X-RateLimit-Reset": str(info.get("reset", 0)),
        }
        
        if "retry_after" in info:
            headers["Retry-After"] = str(info["retry_after"])
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {info.get('reason', 'unknown')}",
            headers=headers
        )
    
    # Add rate limit headers to response
    request.state.rate_limit_info = info


# Global rate limiter instance
enhanced_rate_limiter = EnhancedRateLimiter()