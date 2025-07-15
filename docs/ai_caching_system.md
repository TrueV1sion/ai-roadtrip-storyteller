# AI Caching System Documentation

## Overview

The AI Caching System provides an intelligent, specialized caching implementation for AI-generated content in the Road Trip Storyteller application. This system is designed to:

1. Reduce latency by serving pre-generated content when appropriate
2. Reduce costs by avoiding unnecessary AI model invocations
3. Improve user experience by delivering content faster
4. Support different retention strategies for different user tiers
5. Intelligently handle personalized content and changing parameters

## Architecture

The caching system consists of two key components:

1. **AIResponseCache** - A specialized Redis-based cache implementation that handles different content types, TTLs by user tier, and offers simple integration with the application
2. **CachedAIClient** - An enhanced AI client that extends the existing UnifiedAIClient with transparent caching capabilities

### Key Features

- **Content-Specific Caching**: Different TTLs for different types of content (stories, personalized, conversations)
- **User Tier-Based Retention**: Premium users enjoy longer cache retention periods
- **Personalization-Aware**: Cache keys account for user preferences and context
- **Cache Statistics**: Built-in tracking of cache hits, misses, and time saved
- **Selective Invalidation**: Options to clear cache by user, namespace, or specific entries
- **Force Refresh**: Ability to bypass cache when fresh content is required
- **Seamless Integration**: Drop-in replacement for existing AI client

## Cache Namespaces

The system uses different namespaces for different types of content:

- **ai:story** - General location-based stories
- **ai:personalized** - Personalized content that includes user preferences
- **ai:conversation** - Conversation contexts (typically shorter TTL)
- **ai:location** - Location-based information (typically longer TTL)

## TTL Strategy

The system employs different Time-To-Live (TTL) settings based on content type and user tier:

### Standard Users
- Stories: 7 days
- Personalized content: 1 day
- Conversation contexts: 2 hours
- Location data: 30 days

### Premium Users
- Stories: 30 days
- Personalized content: 7 days
- Conversation contexts: 24 hours
- Location data: 60 days

## Cache Key Generation

Cache keys are carefully constructed to maintain uniqueness while allowing for efficient retrieval. Keys include:

- Namespace (e.g., `ai:story`)
- Optional user ID (e.g., `user:123`)
- Optional provider (e.g., `provider:google`)
- Parameter hash (SHA-256 hash of serialized parameters)

### Example Cache Keys
- `ai:story:35a7c72f0c48e692d8bea54cc4d64e91f9c1a39d9460dc0ad37bc85bf0a28cc0`
- `ai:personalized:user:123:provider:google:6d8ea1f6ecfec1069ce11ae5986ac137d4a8d74d45e07132ef54ee0a44615b89`

## API Documentation

### AIResponseCache

```python
class AIResponseCache:
    # Cache namespaces
    NAMESPACE_STORY = "ai:story"
    NAMESPACE_PERSONALIZED = "ai:personalized"
    NAMESPACE_CONVERSATION = "ai:conversation"
    NAMESPACE_LOCATION = "ai:location"
    
    # Core Methods
    def get(namespace, request_params, user_id=None, provider=None) -> Optional[Dict]
    def set(namespace, request_params, response, user_id=None, provider=None, is_premium=False, ttl=None) -> bool
    def invalidate(namespace, request_params, user_id=None, provider=None) -> bool
    def invalidate_by_user(user_id) -> int
    def invalidate_by_namespace(namespace) -> int
    def get_stats() -> Dict[str, Any]
    def get_or_generate(namespace, request_params, generator_func, user_id=None, provider=None, 
                       is_premium=False, ttl=None, force_refresh=False) -> Dict[str, Any]
```

### CachedAIClient

```python
class CachedAIClient(UnifiedAIClient):
    async def generate_story(location, interests, context=None, style=StoryStyle.DEFAULT,
                           conversation_id=None, force_refresh=False, user_id=None, is_premium=False) -> Dict[str, Any]
    
    async def generate_personalized_story(user_id, location, interests, user_preferences=None,
                                        context=None, style=None, force_refresh=False, is_premium=False) -> Dict[str, Any]
    
    def clear_user_cache(user_id) -> int
    def clear_story_cache() -> int
    def clear_personalized_cache() -> int
    def get_cache_stats() -> Dict[str, Any]
```

## REST API Endpoints

The system exposes REST API endpoints for cache management:

- `GET /api/cache/stats` - Retrieve cache statistics (admin only)
- `DELETE /api/cache/all` - Clear all caches (admin only)
- `DELETE /api/cache/story` - Clear all story caches (admin only)
- `DELETE /api/cache/personalized` - Clear all personalized story caches (admin only)
- `DELETE /api/cache/user/{user_id}` - Clear a specific user's cache (admin or user themselves)

## Integration

The caching system is integrated with the existing story generation endpoints, which now support:

- Automatic caching of generated stories
- Cache hit/miss tracking
- Force refresh option via `force_refresh` parameter
- Cache source indication in response via `from_cache` field

## Monitoring

The caching system tracks key performance metrics:

- **Hit Count**: Number of successful cache retrievals
- **Miss Count**: Number of cache misses
- **Hit Rate**: Percentage of requests served from cache
- **Total Time Saved**: Estimated model generation time saved by cache hits

## Security Considerations

- Cache entries include user IDs but do not contain authentication information
- Cache invalidation endpoints require appropriate authorization
- User-specific cache operations enforce proper permissions
- Premium-tier access is validated before applying premium TTLs

## Testing

The caching system includes a comprehensive test suite in `tests/unit/test_ai_cache.py` that covers:

- Cache key generation
- Hit/miss behavior
- TTL strategies
- Invalidation operations
- Integration with the AI client

## Performance Impact

Based on similar implementations, the expected performance improvements are:

- 50-70% reduction in average response time for common stories
- 30-50% reduction in AI generation costs
- Improved consistency in high-traffic scenarios
- Higher scalability during peak usage