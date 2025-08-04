"""
Rate limiting management endpoints.
"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user, get_current_active_user
from app.core.logger import get_logger
from app.database import get_db
from app.models.user import User
from app.core.enhanced_rate_limiter import enhanced_rate_limiter, RateLimitTier

logger = get_logger(__name__)
router = APIRouter()


@router.get("/rate-limit/status")
async def get_rate_limit_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's rate limit status.
    """
    try:
        # Generate key for current user
        key = f"user:{current_user.id}"
        
        # Get usage stats
        stats = await enhanced_rate_limiter.get_usage_stats(key)
        
        # Get user tier
        tier = enhanced_rate_limiter.get_user_tier(
            str(current_user.id),
            current_user.role
        )
        
        # Get tier limits
        limits = enhanced_rate_limiter.config.TIER_LIMITS[tier]
        
        return {
            "status": "success",
            "data": {
                "tier": tier.value,
                "limits": limits,
                "usage": stats,
                "user_id": str(current_user.id)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rate limit status"
        )


@router.get("/rate-limit/metrics")
async def get_rate_limit_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get rate limiter metrics.
    Admin access required.
    """
    try:
        metrics = enhanced_rate_limiter.get_metrics()
        
        return {
            "status": "success",
            "data": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limit metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


@router.get("/rate-limit/usage/{user_id}")
async def get_user_rate_limit_usage(
    user_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get rate limit usage for a specific user.
    Admin access required.
    """
    try:
        key = f"user:{user_id}"
        stats = await enhanced_rate_limiter.get_usage_stats(key)
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "usage": stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user rate limit usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage"
        )


@router.post("/rate-limit/adjust")
async def adjust_rate_limits(
    adjustment_type: str = Query(..., description="Type of adjustment (high_load, attack_detected, off_peak)"),
    factor: float = Query(..., ge=0.1, le=10.0, description="Adjustment factor"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Dynamically adjust rate limits.
    Admin access required.
    """
    try:
        valid_types = ["high_load", "attack_detected", "off_peak"]
        if adjustment_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid adjustment type. Must be one of: {', '.join(valid_types)}"
            )
        
        enhanced_rate_limiter.set_dynamic_adjustment(adjustment_type, factor)
        
        return {
            "status": "success",
            "message": f"Rate limits adjusted: {adjustment_type} = {factor}",
            "active_adjustments": enhanced_rate_limiter.dynamic_adjustments
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adjusting rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to adjust rate limits"
        )


@router.delete("/rate-limit/adjust/{adjustment_type}")
async def remove_rate_limit_adjustment(
    adjustment_type: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Remove dynamic rate limit adjustment.
    Admin access required.
    """
    try:
        enhanced_rate_limiter.remove_dynamic_adjustment(adjustment_type)
        
        return {
            "status": "success",
            "message": f"Removed adjustment: {adjustment_type}",
            "active_adjustments": enhanced_rate_limiter.dynamic_adjustments
        }
        
    except Exception as e:
        logger.error(f"Error removing adjustment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove adjustment"
        )


@router.post("/rate-limit/block/{key}")
async def block_rate_limit_key(
    key: str,
    duration: int = Query(3600, ge=60, le=86400, description="Block duration in seconds"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Manually block a rate limit key.
    Admin access required.
    """
    try:
        await enhanced_rate_limiter._block_key(key, duration)
        
        return {
            "status": "success",
            "message": f"Blocked key: {key} for {duration} seconds"
        }
        
    except Exception as e:
        logger.error(f"Error blocking key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to block key"
        )


@router.delete("/rate-limit/block/{key}")
async def unblock_rate_limit_key(
    key: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unblock a rate limit key.
    Admin access required.
    """
    try:
        # Remove from local blocked keys
        if key in enhanced_rate_limiter.blocked_keys:
            del enhanced_rate_limiter.blocked_keys[key]
        
        # Remove from cache
        from app.core.cache import cache_manager
        cache_key = f"rate_limit_blocked:{key}"
        await cache_manager.delete(cache_key)
        
        return {
            "status": "success",
            "message": f"Unblocked key: {key}"
        }
        
    except Exception as e:
        logger.error(f"Error unblocking key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unblock key"
        )


@router.get("/rate-limit/blocked-keys")
async def get_blocked_keys(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get list of blocked rate limit keys.
    Admin access required.
    """
    try:
        blocked_keys = []
        
        # Get local blocked keys
        for key, expiry in enhanced_rate_limiter.blocked_keys.items():
            blocked_keys.append({
                "key": key,
                "expiry": expiry,
                "remaining_seconds": max(0, int(expiry - time.time()))
            })
        
        # TODO: Also check distributed cache for blocked keys
        
        return {
            "status": "success",
            "data": {
                "blocked_keys": blocked_keys,
                "total": len(blocked_keys)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting blocked keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blocked keys"
        )


@router.get("/rate-limit/tiers")
async def get_rate_limit_tiers(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get available rate limit tiers and their limits.
    """
    try:
        tiers = {}
        
        for tier in RateLimitTier:
            if tier != RateLimitTier.ADMIN or current_user.role in ["admin", "super_admin"]:
                tiers[tier.value] = enhanced_rate_limiter.config.TIER_LIMITS[tier]
        
        return {
            "status": "success",
            "data": {
                "tiers": tiers,
                "current_tier": enhanced_rate_limiter.get_user_tier(
                    str(current_user.id),
                    current_user.role
                ).value
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limit tiers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tiers"
        )


@router.patch("/rate-limit/user/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    tier: str = Query(..., description="New tier (basic, premium, enterprise)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update user's rate limit tier.
    Admin access required.
    """
    try:
        # Validate tier
        valid_tiers = ["basic", "premium", "enterprise"]
        if tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        # Update user role to match tier
        from app.crud.crud_user import update_user
        from app.schemas.user import UserUpdate
        
        user_update = UserUpdate(role=tier)
        updated_user = update_user(db, user_id, user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "status": "success",
            "message": f"Updated user {user_id} to tier: {tier}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tier"
        )