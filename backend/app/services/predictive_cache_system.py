"""
Predictive Caching System
Intelligently pre-caches likely user requests based on patterns and context
"""
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import hashlib
import numpy as np
from collections import defaultdict, deque
import pickle

from app.core.logger import get_logger
from app.core.cache import get_redis_client
from app.services.location_service import LocationService
from app.services.ai_model_optimizer import TaskType

logger = get_logger(__name__)


class PredictionType(Enum):
    """Types of predictions for caching"""
    ROUTE_WAYPOINT = "route_waypoint"
    STORY_LOCATION = "story_location"
    BOOKING_SEARCH = "booking_search"
    NAVIGATION_UPDATE = "navigation_update"
    VOICE_COMMAND = "voice_command"
    USER_PREFERENCE = "user_preference"
    SEASONAL_CONTENT = "seasonal_content"


@dataclass
class PredictionPattern:
    """Pattern for predictive caching"""
    pattern_id: str
    pattern_type: PredictionType
    confidence: float
    trigger_conditions: Dict[str, Any]
    cache_duration_seconds: int
    priority: int  # 1-10, higher is more important


@dataclass
class CacheEntry:
    """Entry in predictive cache"""
    key: str
    value: Any
    prediction_type: PredictionType
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    confidence: float = 0.5
    size_bytes: int = 0


@dataclass
class UserContext:
    """Current user context for predictions"""
    user_id: str
    current_location: Tuple[float, float]
    destination: Optional[Tuple[float, float]]
    current_speed: float
    route_progress: float
    time_of_day: datetime
    day_of_week: int
    weather: str
    recent_commands: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


class PredictiveCacheSystem:
    """Manages predictive caching for improved performance"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.location_service = LocationService()
        self.pattern_analyzer = PatternAnalyzer()
        self.cache_warmer = CacheWarmer()
        self.eviction_manager = EvictionManager()
        
        # Cache metrics
        self.hit_rate_tracker = HitRateTracker()
        self.prediction_accuracy = defaultdict(float)
        
        # Configuration
        self.max_cache_size_mb = 100
        self.max_entries = 10000
        self.warmup_interval_seconds = 30
        
        # Start background tasks
        asyncio.create_task(self._warmup_loop())
        asyncio.create_task(self._eviction_loop())
    
    async def get_or_predict(
        self,
        key: str,
        context: UserContext,
        fetch_func,
        cache_duration: int = 300
    ) -> Tuple[Any, bool]:
        """Get from cache or predict and fetch if needed"""
        
        # Check if already cached
        cached_value = await self._get_from_cache(key)
        if cached_value is not None:
            self.hit_rate_tracker.record_hit(key)
            return cached_value, True
        
        # Record miss
        self.hit_rate_tracker.record_miss(key)
        
        # Check if we should predictively cache this
        should_cache = await self._should_predictively_cache(key, context)
        
        # Fetch the value
        value = await fetch_func()
        
        # Cache if appropriate
        if should_cache or self._is_frequently_accessed(key):
            await self._add_to_cache(
                key,
                value,
                PredictionType.VOICE_COMMAND,  # Default type
                cache_duration
            )
        
        return value, False
    
    async def predict_next_requests(
        self,
        context: UserContext,
        num_predictions: int = 5
    ) -> List[PredictionPattern]:
        """Predict next likely requests based on context"""
        
        predictions = []
        
        # Route-based predictions
        if context.destination:
            route_predictions = await self._predict_route_requests(context)
            predictions.extend(route_predictions)
        
        # Time-based predictions
        time_predictions = await self._predict_time_based_requests(context)
        predictions.extend(time_predictions)
        
        # Pattern-based predictions
        pattern_predictions = await self.pattern_analyzer.analyze_patterns(context)
        predictions.extend(pattern_predictions)
        
        # User preference predictions
        pref_predictions = await self._predict_preference_requests(context)
        predictions.extend(pref_predictions)
        
        # Sort by confidence and priority
        predictions.sort(key=lambda p: (p.confidence * p.priority), reverse=True)
        
        return predictions[:num_predictions]
    
    async def _predict_route_requests(self, context: UserContext) -> List[PredictionPattern]:
        """Predict requests based on route progress"""
        predictions = []
        
        if not context.destination:
            return predictions
        
        # Predict upcoming waypoints
        if context.route_progress < 0.8:  # Not near destination
            # Next story location
            predictions.append(PredictionPattern(
                pattern_id=f"story_next_{context.user_id}",
                pattern_type=PredictionType.STORY_LOCATION,
                confidence=0.9,
                trigger_conditions={
                    "distance_miles": 5,
                    "direction": "along_route"
                },
                cache_duration_seconds=600,
                priority=8
            ))
            
            # Gas station search (if been driving > 2 hours)
            if context.current_speed > 50:
                predictions.append(PredictionPattern(
                    pattern_id=f"gas_search_{context.user_id}",
                    pattern_type=PredictionType.BOOKING_SEARCH,
                    confidence=0.7,
                    trigger_conditions={
                        "search_type": "gas_station",
                        "radius_miles": 10
                    },
                    cache_duration_seconds=1800,
                    priority=6
                ))
        
        # Near destination predictions
        if context.route_progress > 0.7:
            # Parking search
            predictions.append(PredictionPattern(
                pattern_id=f"parking_dest_{context.user_id}",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.85,
                trigger_conditions={
                    "search_type": "parking",
                    "near": context.destination
                },
                cache_duration_seconds=900,
                priority=9
            ))
            
            # Restaurant search
            predictions.append(PredictionPattern(
                pattern_id=f"restaurant_dest_{context.user_id}",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.6,
                trigger_conditions={
                    "search_type": "restaurant",
                    "near": context.destination
                },
                cache_duration_seconds=1200,
                priority=5
            ))
        
        return predictions
    
    async def _predict_time_based_requests(self, context: UserContext) -> List[PredictionPattern]:
        """Predict requests based on time patterns"""
        predictions = []
        
        hour = context.time_of_day.hour
        
        # Meal time predictions
        if hour in [11, 12, 13]:  # Lunch time
            predictions.append(PredictionPattern(
                pattern_id=f"lunch_search_{context.user_id}",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.75,
                trigger_conditions={
                    "search_type": "restaurant",
                    "cuisine": "lunch"
                },
                cache_duration_seconds=3600,
                priority=7
            ))
        elif hour in [17, 18, 19]:  # Dinner time
            predictions.append(PredictionPattern(
                pattern_id=f"dinner_search_{context.user_id}",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.8,
                trigger_conditions={
                    "search_type": "restaurant",
                    "cuisine": "dinner"
                },
                cache_duration_seconds=3600,
                priority=7
            ))
        
        # Late night hotel search
        if hour >= 21 or hour <= 2:
            predictions.append(PredictionPattern(
                pattern_id=f"hotel_late_{context.user_id}",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.7,
                trigger_conditions={
                    "search_type": "hotel",
                    "check_in": "tonight"
                },
                cache_duration_seconds=1800,
                priority=8
            ))
        
        # Rush hour traffic updates
        if hour in [7, 8, 9, 16, 17, 18] and context.day_of_week < 5:  # Weekday rush
            predictions.append(PredictionPattern(
                pattern_id=f"traffic_update_{context.user_id}",
                pattern_type=PredictionType.NAVIGATION_UPDATE,
                confidence=0.9,
                trigger_conditions={
                    "update_type": "traffic",
                    "route": "current"
                },
                cache_duration_seconds=300,
                priority=9
            ))
        
        return predictions
    
    async def _predict_preference_requests(self, context: UserContext) -> List[PredictionPattern]:
        """Predict based on user preferences"""
        predictions = []
        
        # Voice personality preferences
        if "favorite_voice" in context.preferences:
            predictions.append(PredictionPattern(
                pattern_id=f"voice_pref_{context.user_id}",
                pattern_type=PredictionType.USER_PREFERENCE,
                confidence=0.95,
                trigger_conditions={
                    "preference": "voice_personality",
                    "value": context.preferences["favorite_voice"]
                },
                cache_duration_seconds=86400,  # 24 hours
                priority=5
            ))
        
        # Music preferences
        if "music_genre" in context.preferences:
            predictions.append(PredictionPattern(
                pattern_id=f"music_pref_{context.user_id}",
                pattern_type=PredictionType.USER_PREFERENCE,
                confidence=0.8,
                trigger_conditions={
                    "preference": "music",
                    "genre": context.preferences["music_genre"]
                },
                cache_duration_seconds=7200,
                priority=4
            ))
        
        return predictions
    
    async def warm_cache(self, predictions: List[PredictionPattern], context: UserContext):
        """Warm cache based on predictions"""
        
        tasks = []
        for prediction in predictions:
            if prediction.confidence > 0.6:  # Only warm high-confidence predictions
                task = self.cache_warmer.warm_prediction(prediction, context)
                tasks.append(task)
        
        # Execute warming tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _should_predictively_cache(self, key: str, context: UserContext) -> bool:
        """Determine if a key should be predictively cached"""
        
        # Check access patterns
        if self._is_frequently_accessed(key):
            return True
        
        # Check if part of a pattern
        if await self.pattern_analyzer.is_part_of_pattern(key, context):
            return True
        
        # Check resource availability
        if await self._has_cache_capacity():
            # More lenient when we have space
            return self._get_access_count(key) > 1
        
        return False
    
    def _is_frequently_accessed(self, key: str) -> bool:
        """Check if key is frequently accessed"""
        access_count = self._get_access_count(key)
        return access_count > 5
    
    def _get_access_count(self, key: str) -> int:
        """Get access count for a key"""
        return self.hit_rate_tracker.get_access_count(key)
    
    async def _has_cache_capacity(self) -> bool:
        """Check if cache has capacity"""
        current_size = await self._get_cache_size()
        return current_size < self.max_cache_size_mb * 0.8  # 80% threshold
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            cached_data = await self.redis_client.get(f"predictive:{key}")
            if cached_data:
                entry = pickle.loads(cached_data)
                
                # Update access metrics
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                
                # Re-save with updated metrics
                await self.redis_client.set(
                    f"predictive:{key}",
                    pickle.dumps(entry),
                    ex=int((entry.expires_at - datetime.now()).total_seconds())
                )
                
                return entry.value
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    async def _add_to_cache(
        self,
        key: str,
        value: Any,
        prediction_type: PredictionType,
        duration_seconds: int
    ):
        """Add value to predictive cache"""
        try:
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                prediction_type=prediction_type,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=duration_seconds),
                size_bytes=len(pickle.dumps(value))
            )
            
            # Check capacity before adding
            if await self._has_cache_capacity():
                await self.redis_client.set(
                    f"predictive:{key}",
                    pickle.dumps(entry),
                    ex=duration_seconds
                )
                
                # Track the entry
                await self._track_cache_entry(entry)
            else:
                # Trigger eviction if needed
                await self.eviction_manager.evict_if_needed()
        except Exception as e:
            logger.error(f"Cache insertion error: {e}")
    
    async def _track_cache_entry(self, entry: CacheEntry):
        """Track cache entry for analytics"""
        # Add to tracking set
        await self.redis_client.sadd(
            "predictive:entries",
            entry.key
        )
        
        # Update metrics
        await self.redis_client.hincrby(
            "predictive:metrics",
            f"count_{entry.prediction_type.value}",
            1
        )
    
    async def _get_cache_size(self) -> float:
        """Get current cache size in MB"""
        try:
            # Get all predictive cache keys
            keys = await self.redis_client.keys("predictive:*")
            
            total_size = 0
            for key in keys:
                if key != b"predictive:entries" and key != b"predictive:metrics":
                    data = await self.redis_client.get(key)
                    if data:
                        total_size += len(data)
            
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
            return 0
    
    async def _warmup_loop(self):
        """Background task to warm cache"""
        while True:
            try:
                await asyncio.sleep(self.warmup_interval_seconds)
                
                # Get active users
                active_users = await self._get_active_users()
                
                for user_id in active_users:
                    # Get user context
                    context = await self._get_user_context(user_id)
                    if context:
                        # Generate predictions
                        predictions = await self.predict_next_requests(context)
                        
                        # Warm cache
                        await self.warm_cache(predictions, context)
                
            except Exception as e:
                logger.error(f"Warmup loop error: {e}")
    
    async def _eviction_loop(self):
        """Background task to evict stale entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Check and evict if needed
                await self.eviction_manager.evict_if_needed()
                
                # Update metrics
                await self._update_cache_metrics()
                
            except Exception as e:
                logger.error(f"Eviction loop error: {e}")
    
    async def _get_active_users(self) -> List[str]:
        """Get list of active users"""
        # This would integrate with session management
        # For now, return empty list
        return []
    
    async def _get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context for predictions"""
        # This would fetch actual user context
        # For now, return None
        return None
    
    async def _update_cache_metrics(self):
        """Update cache performance metrics"""
        hit_rate = self.hit_rate_tracker.get_overall_hit_rate()
        cache_size = await self._get_cache_size()
        
        logger.info(
            f"Predictive cache metrics - Hit rate: {hit_rate:.1%}, "
            f"Size: {cache_size:.1f}MB"
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get cache performance report"""
        return {
            "hit_rate": self.hit_rate_tracker.get_overall_hit_rate(),
            "hit_rates_by_type": self.hit_rate_tracker.get_hit_rates_by_type(),
            "prediction_accuracy": dict(self.prediction_accuracy),
            "cache_size_mb": asyncio.run(self._get_cache_size()),
            "top_cached_keys": self.hit_rate_tracker.get_top_keys(10)
        }


class PatternAnalyzer:
    """Analyzes user patterns for predictions"""
    
    def __init__(self):
        self.sequence_patterns = defaultdict(list)
        self.time_patterns = defaultdict(list)
        self.location_patterns = defaultdict(list)
    
    async def analyze_patterns(self, context: UserContext) -> List[PredictionPattern]:
        """Analyze patterns from user context"""
        patterns = []
        
        # Analyze command sequences
        if len(context.recent_commands) >= 2:
            sequence_pattern = await self._analyze_command_sequence(
                context.recent_commands
            )
            if sequence_pattern:
                patterns.append(sequence_pattern)
        
        # Analyze time patterns
        time_pattern = await self._analyze_time_pattern(context)
        if time_pattern:
            patterns.append(time_pattern)
        
        # Analyze location patterns
        location_pattern = await self._analyze_location_pattern(context)
        if location_pattern:
            patterns.append(location_pattern)
        
        return patterns
    
    async def _analyze_command_sequence(
        self,
        commands: List[str]
    ) -> Optional[PredictionPattern]:
        """Analyze command sequences for patterns"""
        
        # Look for common sequences
        if len(commands) >= 2:
            last_two = tuple(commands[-2:])
            
            # Common patterns
            common_sequences = {
                ("navigate", "find_gas"): "gas_after_nav",
                ("find_restaurant", "book"): "book_after_search",
                ("traffic", "alternate_route"): "reroute_after_traffic"
            }
            
            for (cmd1, cmd2), pattern_name in common_sequences.items():
                if cmd1 in last_two[0] and cmd2 in last_two[1]:
                    return PredictionPattern(
                        pattern_id=f"seq_{pattern_name}",
                        pattern_type=PredictionType.VOICE_COMMAND,
                        confidence=0.8,
                        trigger_conditions={"sequence": [cmd1, cmd2]},
                        cache_duration_seconds=600,
                        priority=7
                    )
        
        return None
    
    async def _analyze_time_pattern(
        self,
        context: UserContext
    ) -> Optional[PredictionPattern]:
        """Analyze time-based patterns"""
        
        # Weekend patterns
        if context.day_of_week >= 5:  # Weekend
            return PredictionPattern(
                pattern_id="weekend_leisure",
                pattern_type=PredictionType.BOOKING_SEARCH,
                confidence=0.7,
                trigger_conditions={
                    "search_types": ["restaurant", "entertainment", "recreation"]
                },
                cache_duration_seconds=7200,
                priority=5
            )
        
        return None
    
    async def _analyze_location_pattern(
        self,
        context: UserContext
    ) -> Optional[PredictionPattern]:
        """Analyze location-based patterns"""
        
        # Airport proximity pattern
        # This would check actual proximity to airports
        # For now, return None
        return None
    
    async def is_part_of_pattern(self, key: str, context: UserContext) -> bool:
        """Check if key is part of a known pattern"""
        # Check if key matches any pattern conditions
        patterns = await self.analyze_patterns(context)
        
        for pattern in patterns:
            if pattern.confidence > 0.7:
                # Check if key matches pattern conditions
                # Simplified check for now
                return True
        
        return False


class CacheWarmer:
    """Warms cache based on predictions"""
    
    async def warm_prediction(
        self,
        prediction: PredictionPattern,
        context: UserContext
    ):
        """Warm cache for a specific prediction"""
        try:
            # Based on prediction type, fetch and cache data
            if prediction.pattern_type == PredictionType.STORY_LOCATION:
                await self._warm_story_location(prediction, context)
            elif prediction.pattern_type == PredictionType.BOOKING_SEARCH:
                await self._warm_booking_search(prediction, context)
            elif prediction.pattern_type == PredictionType.NAVIGATION_UPDATE:
                await self._warm_navigation_update(prediction, context)
            
        except Exception as e:
            logger.error(f"Cache warming error for {prediction.pattern_id}: {e}")
    
    async def _warm_story_location(
        self,
        prediction: PredictionPattern,
        context: UserContext
    ):
        """Warm story location cache"""
        # This would fetch story for predicted location
        # Implementation depends on story service
        pass
    
    async def _warm_booking_search(
        self,
        prediction: PredictionPattern,
        context: UserContext
    ):
        """Warm booking search cache"""
        # This would perform booking search
        # Implementation depends on booking service
        pass
    
    async def _warm_navigation_update(
        self,
        prediction: PredictionPattern,
        context: UserContext
    ):
        """Warm navigation update cache"""
        # This would fetch traffic/route updates
        # Implementation depends on navigation service
        pass


class EvictionManager:
    """Manages cache eviction strategies"""
    
    def __init__(self):
        self.eviction_strategies = {
            "lru": self._evict_lru,
            "lfu": self._evict_lfu,
            "ttl": self._evict_expired,
            "size": self._evict_by_size
        }
    
    async def evict_if_needed(self):
        """Check and evict entries if needed"""
        # First, always remove expired entries
        await self._evict_expired()
        
        # Then check if additional eviction needed
        cache_size = await self._get_cache_size()
        if cache_size > 80:  # MB
            # Use LRU strategy
            await self._evict_lru()
    
    async def _evict_lru(self):
        """Evict least recently used entries"""
        # Get all entries with access times
        entries = await self._get_all_entries()
        
        # Sort by last accessed
        entries.sort(key=lambda e: e.last_accessed or e.created_at)
        
        # Evict oldest 20%
        evict_count = len(entries) // 5
        for entry in entries[:evict_count]:
            await self._evict_entry(entry.key)
    
    async def _evict_lfu(self):
        """Evict least frequently used entries"""
        entries = await self._get_all_entries()
        
        # Sort by access count
        entries.sort(key=lambda e: e.access_count)
        
        # Evict least accessed 20%
        evict_count = len(entries) // 5
        for entry in entries[:evict_count]:
            await self._evict_entry(entry.key)
    
    async def _evict_expired(self):
        """Evict expired entries"""
        entries = await self._get_all_entries()
        
        now = datetime.now()
        for entry in entries:
            if entry.expires_at < now:
                await self._evict_entry(entry.key)
    
    async def _evict_by_size(self):
        """Evict largest entries first"""
        entries = await self._get_all_entries()
        
        # Sort by size
        entries.sort(key=lambda e: e.size_bytes, reverse=True)
        
        # Evict largest until under threshold
        target_size = 60 * 1024 * 1024  # 60MB
        current_size = sum(e.size_bytes for e in entries)
        
        for entry in entries:
            if current_size <= target_size:
                break
            await self._evict_entry(entry.key)
            current_size -= entry.size_bytes
    
    async def _get_all_entries(self) -> List[CacheEntry]:
        """Get all cache entries"""
        # This would fetch from Redis
        # Simplified for now
        return []
    
    async def _evict_entry(self, key: str):
        """Evict a single entry"""
        # Delete from Redis
        # Update metrics
        pass
    
    async def _get_cache_size(self) -> float:
        """Get cache size in MB"""
        # This would calculate actual size
        return 0.0


class HitRateTracker:
    """Tracks cache hit rates"""
    
    def __init__(self):
        self.hits = defaultdict(int)
        self.misses = defaultdict(int)
        self.access_counts = defaultdict(int)
        self.type_hits = defaultdict(int)
        self.type_misses = defaultdict(int)
    
    def record_hit(self, key: str, prediction_type: Optional[PredictionType] = None):
        """Record a cache hit"""
        self.hits[key] += 1
        self.access_counts[key] += 1
        
        if prediction_type:
            self.type_hits[prediction_type.value] += 1
    
    def record_miss(self, key: str, prediction_type: Optional[PredictionType] = None):
        """Record a cache miss"""
        self.misses[key] += 1
        self.access_counts[key] += 1
        
        if prediction_type:
            self.type_misses[prediction_type.value] += 1
    
    def get_hit_rate(self, key: str) -> float:
        """Get hit rate for specific key"""
        total = self.hits[key] + self.misses[key]
        if total == 0:
            return 0.0
        return self.hits[key] / total
    
    def get_overall_hit_rate(self) -> float:
        """Get overall hit rate"""
        total_hits = sum(self.hits.values())
        total_misses = sum(self.misses.values())
        total = total_hits + total_misses
        
        if total == 0:
            return 0.0
        return total_hits / total
    
    def get_hit_rates_by_type(self) -> Dict[str, float]:
        """Get hit rates by prediction type"""
        rates = {}
        
        for pred_type in PredictionType:
            type_name = pred_type.value
            hits = self.type_hits.get(type_name, 0)
            misses = self.type_misses.get(type_name, 0)
            total = hits + misses
            
            if total > 0:
                rates[type_name] = hits / total
        
        return rates
    
    def get_access_count(self, key: str) -> int:
        """Get access count for key"""
        return self.access_counts[key]
    
    def get_top_keys(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get top accessed keys"""
        sorted_keys = sorted(
            self.access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_keys[:n]


# Usage example
async def demonstrate_predictive_cache():
    """Demonstrate predictive caching"""
    cache_system = PredictiveCacheSystem()
    
    # Create user context
    context = UserContext(
        user_id="user123",
        current_location=(37.7749, -122.4194),  # San Francisco
        destination=(34.0522, -118.2437),  # Los Angeles
        current_speed=65.0,
        route_progress=0.3,
        time_of_day=datetime.now(),
        day_of_week=datetime.now().weekday(),
        weather="clear",
        recent_commands=["navigate to LA", "play music"],
        preferences={"favorite_voice": "captain", "music_genre": "rock"}
    )
    
    # Generate predictions
    predictions = await cache_system.predict_next_requests(context)
    
    print("Predicted next requests:")
    for pred in predictions:
        print(f"  {pred.pattern_type.value}: {pred.confidence:.0%} confidence")
    
    # Warm cache
    await cache_system.warm_cache(predictions, context)
    
    # Simulate getting data
    async def fetch_data():
        await asyncio.sleep(0.1)  # Simulate API call
        return {"data": "example"}
    
    # First call (miss)
    data, hit = await cache_system.get_or_predict("test_key", context, fetch_data)
    print(f"\nFirst call - Hit: {hit}")
    
    # Second call (hit)
    data, hit = await cache_system.get_or_predict("test_key", context, fetch_data)
    print(f"Second call - Hit: {hit}")
    
    # Get performance report
    report = cache_system.get_performance_report()
    print(f"\nCache performance: {report['hit_rate']:.0%} hit rate")


if __name__ == "__main__":
    asyncio.run(demonstrate_predictive_cache())