"""
Performance monitoring and cache management endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.enhanced_cache import cache_manager
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/performance/stats")
async def get_performance_stats() -> Dict[str, Any]:
    """
    Get comprehensive performance statistics.
    
    Returns:
        Dict with performance metrics
    """
    try:
        # Get cache statistics
        cache_stats = cache_manager.get_cache_stats()
        
        # Get performance middleware stats (if available)
        performance_stats = {}
        # Note: This would need to be implemented to access the middleware instance
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cache": cache_stats,
            "performance": performance_stats,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance stats: {str(e)}"
        )


@router.get("/performance/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get detailed cache statistics.
    
    Returns:
        Dict with cache metrics
    """
    try:
        stats = cache_manager.get_cache_stats()
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.post("/performance/cache/invalidate/{namespace}")
async def invalidate_cache_namespace(namespace: str) -> Dict[str, Any]:
    """
    Invalidate all cache entries for a specific namespace.
    
    Args:
        namespace: Cache namespace to invalidate
        
    Returns:
        Dict with invalidation results
    """
    try:
        count = await cache_manager.invalidate_namespace(namespace)
        
        return {
            "namespace": namespace,
            "invalidated_count": count,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache namespace {namespace}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache namespace: {str(e)}"
        )


@router.post("/performance/cache/preload")
async def preload_cache(preload_configs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Preload cache with commonly accessed data.
    
    Args:
        preload_configs: Optional custom preload configuration
        
    Returns:
        Dict with preload results
    """
    try:
        # Default preload configurations
        default_configs = [
            {
                "key": "voice:personalities:list",
                "namespace": "api",
                "callback": lambda: [
                    {"id": "friendly", "name": "Friendly Guide"},
                    {"id": "historian", "name": "Local Historian"},
                    {"id": "adventurer", "name": "Adventure Guide"}
                ]
            },
            {
                "key": "system:health:status",
                "namespace": "api", 
                "callback": lambda: {"status": "healthy", "timestamp": datetime.now().isoformat()}
            }
        ]
        
        # Use provided configs or defaults
        configs = preload_configs.get("configs", default_configs) if preload_configs else default_configs
        
        # Preload cache
        await cache_manager.preload_cache(configs)
        
        return {
            "preloaded_items": len(configs),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to preload cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preload cache: {str(e)}"
        )


@router.get("/performance/cache/test")
async def test_cache_performance() -> Dict[str, Any]:
    """
    Test cache performance with various operations.
    
    Returns:
        Dict with performance test results
    """
    try:
        import time
        import random
        
        results = {}
        
        # Test memory cache performance
        start_time = time.time()
        test_key = "performance_test"
        test_data = {"test": "data", "timestamp": time.time(), "random": random.randint(1, 1000)}
        
        # Set operation
        await cache_manager.set(test_key, test_data, "api")
        set_time = time.time() - start_time
        
        # Get operation
        start_time = time.time()
        retrieved_data = await cache_manager.get(test_key, "api")
        get_time = time.time() - start_time
        
        # Delete operation
        start_time = time.time()
        await cache_manager.delete(test_key, "api")
        delete_time = time.time() - start_time
        
        results = {
            "set_operation_ms": round(set_time * 1000, 3),
            "get_operation_ms": round(get_time * 1000, 3),
            "delete_operation_ms": round(delete_time * 1000, 3),
            "data_integrity": retrieved_data == test_data,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Cache performance test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cache performance test failed: {str(e)}"
        )


@router.get("/performance/optimization/suggestions")
async def get_optimization_suggestions() -> Dict[str, Any]:
    """
    Get performance optimization suggestions based on current metrics.
    
    Returns:
        Dict with optimization suggestions
    """
    try:
        suggestions = []
        
        # Get cache stats
        cache_stats = cache_manager.get_cache_stats()
        
        # Analyze memory cache
        memory_stats = cache_stats.get("memory", {})
        if memory_stats.get("hit_rate", 0) < 0.5:
            suggestions.append({
                "type": "cache",
                "priority": "medium",
                "description": "Memory cache hit rate is low. Consider adjusting cache TTL or preloading common data.",
                "metric": f"Hit rate: {memory_stats.get('hit_rate', 0):.2%}"
            })
        
        if memory_stats.get("size", 0) > memory_stats.get("max_size", 1000) * 0.9:
            suggestions.append({
                "type": "cache",
                "priority": "high",
                "description": "Memory cache is near capacity. Consider increasing max_size or adjusting eviction policy.",
                "metric": f"Usage: {memory_stats.get('size', 0)}/{memory_stats.get('max_size', 1000)}"
            })
        
        # Analyze Redis cache
        redis_stats = cache_stats.get("redis", {})
        if not redis_stats.get("available", False):
            suggestions.append({
                "type": "infrastructure",
                "priority": "high",
                "description": "Redis cache is not available. This may impact performance significantly.",
                "metric": "Redis: unavailable"
            })
        
        # General suggestions
        suggestions.append({
            "type": "monitoring",
            "priority": "low",
            "description": "Consider implementing request rate limiting for high-traffic endpoints.",
            "metric": "General recommendation"
        })
        
        return {
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate optimization suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate optimization suggestions: {str(e)}"
        )