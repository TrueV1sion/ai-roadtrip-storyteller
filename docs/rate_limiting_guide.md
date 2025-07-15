# Rate Limiting Guide

This guide explains how to use the production-ready rate limiting middleware in the AI Road Trip Storyteller application.

## Overview

The rate limiting middleware provides distributed rate limiting using Redis with a sliding window algorithm. It supports:

- **Per-user rate limits** - Different limits for authenticated users
- **Per-IP rate limits** - Limits for anonymous users
- **Per-endpoint rate limits** - Custom limits for specific API endpoints
- **Global rate limits** - Overall API protection
- **Burst allowance** - Temporary spikes in traffic
- **Admin bypass** - Exemption for admin users
- **Proper 429 responses** - With Retry-After headers
- **Rate limit headers** - X-RateLimit-* headers on all responses
- **Violation logging** - For monitoring and intrusion detection

## Configuration

### Basic Setup

The rate limiting middleware is configured in your FastAPI application:

```python
from backend.app.middleware.rate_limit_middleware import RateLimitMiddleware

app = FastAPI()

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    enable_global_limit=True,      # Enable global API limit
    enable_per_ip_limit=True,       # Enable per-IP limits
    enable_per_user_limit=True,     # Enable per-user limits
    enable_endpoint_limits=True,    # Enable endpoint-specific limits
    admin_bypass=True               # Allow admin users to bypass limits
)
```

### Default Limits

The middleware comes with sensible defaults:

- **Global**: 10,000 requests/hour
- **Per-IP**: 1,000 requests/hour
- **Per-User**: 2,000 requests/hour (authenticated users get higher limits)

### Endpoint-Specific Limits

Critical endpoints have stricter limits:

```python
# Authentication endpoints
"/api/v1/auth/login": 5 requests per 5 minutes
"/api/v1/auth/register": 3 requests per 15 minutes
"/api/v1/auth/password-reset": 3 requests per 15 minutes

# AI endpoints (expensive operations)
"/api/v1/stories/generate": 50 requests per hour
"/api/v1/voice/synthesize": 100 requests per hour

# Booking endpoints
"/api/v1/bookings": 20 requests per 5 minutes
```

### Custom Limits

You can add custom limits for specific endpoints:

```python
from backend.app.middleware.rate_limit_middleware import RateLimitConfig

custom_limits = {
    "/api/v1/custom-endpoint": RateLimitConfig(
        requests=10,
        window_seconds=60,
        burst_multiplier=1.0  # No burst for this endpoint
    )
}

app.add_middleware(
    RateLimitMiddleware,
    custom_limits=custom_limits
)
```

## Response Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 1000        # Maximum requests allowed
X-RateLimit-Remaining: 950     # Requests remaining in window
X-RateLimit-Reset: 1640995200  # Unix timestamp when limit resets
X-RateLimit-Type: per_ip       # Which limit type is most restrictive
```

## 429 Too Many Requests Response

When rate limit is exceeded:

```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please retry after some time.",
    "retry_after": 300,
    "limit": 100,
    "window_seconds": 3600,
    "limit_type": "endpoint",
    "burst_active": false
}
```

Headers:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 300
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
X-RateLimit-Type: endpoint
```

## Burst Allowance

The middleware supports burst traffic with a multiplier:

- Default burst multiplier: 1.5x
- Allows temporary spikes above the normal limit
- Burst limit applies until the base limit is reached
- After that, strict limiting applies

Example:
- Normal limit: 100 requests/hour
- Burst limit: 150 requests/hour
- If current usage < 100: Can make up to 150 total
- If current usage >= 100: Strict 100 limit applies

## Admin Bypass

Admin users can bypass rate limits:

1. Middleware checks if user is admin
2. If admin, request proceeds without rate limiting
3. Response includes `X-RateLimit-Bypass: admin` header

## Monitoring

### Rate Limit Status

Check current rate limit status for any key:

```python
from backend.app.middleware.rate_limit_middleware import get_rate_limit_status

# Check status for a user
status = await get_rate_limit_status("user:123")
# Returns:
# {
#     "global": {"current": 50, "limit": 10000, "remaining": 9950, ...},
#     "per_ip": {"current": 20, "limit": 1000, "remaining": 980, ...},
#     "per_user": {"current": 30, "limit": 2000, "remaining": 1970, ...}
# }
```

### Violations

Monitor rate limit violations:

```python
from backend.app.middleware.rate_limit_middleware import get_rate_limit_violations

# Get violations in the last hour
violations = await get_rate_limit_violations()

# Get violations in specific time range
violations = await get_rate_limit_violations(
    start_time=1640991600,
    end_time=1640995200
)
```

### Reset Limits

Manually reset rate limits for a key:

```python
from backend.app.middleware.rate_limit_middleware import reset_rate_limit

# Reset all limits for a user
await reset_rate_limit("user:123")

# Reset specific limit type
await reset_rate_limit("ip:192.168.1.1", limit_type="per_ip")
```

## Integration with Other Middleware

The rate limiting middleware should be added early in the middleware stack:

```python
# Recommended order
app.add_middleware(RateLimitMiddleware)      # First - rate limiting
app.add_middleware(SecurityHeadersMiddleware) # Second - security headers
app.add_middleware(CSRFMiddleware)           # Third - CSRF protection
app.add_middleware(CORSMiddleware)           # Fourth - CORS
```

## Testing

### Bypassing in Tests

For testing, you can disable rate limiting:

```python
app.add_middleware(
    RateLimitMiddleware,
    enable_global_limit=False,
    enable_per_ip_limit=False,
    enable_per_user_limit=False,
    enable_endpoint_limits=False
)
```

### Simulating Rate Limits

```python
# In tests, mock Redis to simulate rate limit scenarios
mock_redis.client.pipeline.return_value.execute.return_value = [None, 1001]  # Over limit
```

## Best Practices

1. **Set appropriate limits**: Balance between protecting resources and user experience
2. **Monitor violations**: Look for patterns that might indicate attacks
3. **Use burst allowance wisely**: Enable for general endpoints, disable for auth
4. **Cache admin status**: Avoid database lookups on every request
5. **Handle Redis failures gracefully**: The middleware fails open (allows requests)
6. **Log violations**: For security monitoring and intrusion detection
7. **Test rate limits**: Ensure they work as expected in your environment

## Troubleshooting

### Redis Connection Issues

If Redis is unavailable:
- Middleware logs warning
- Requests are allowed through (fail open)
- No rate limiting is applied

### High Memory Usage

If Redis memory grows:
- Check key expiration (should be window + 60 seconds)
- Monitor for key leaks
- Use Redis memory analysis tools

### Performance Impact

Rate limiting adds minimal overhead:
- ~1-2ms per request with Redis on same network
- Use connection pooling (already configured)
- Consider Redis cluster for very high traffic

## Security Considerations

1. **IP Spoofing**: The middleware trusts proxy headers. Ensure your load balancer sets them correctly.
2. **Distributed Attacks**: Combine with other security measures (WAF, DDoS protection).
3. **User Enumeration**: Rate limits on login don't reveal if user exists.
4. **Admin Bypass**: Ensure admin check is secure and cached appropriately.