# HTTPS Configuration Guide

**Last Updated:** December 15, 2024  
**Document Version:** 1.0  
**Security Level:** Required for Production

## Overview

This guide covers HTTPS configuration for the Road Trip application, including automatic redirects, secure cookies, and CORS configuration.

## Implementation Details

### 1. HTTPS Redirect Middleware

Located at: `backend/app/core/https_redirect.py`

Features:
- Automatic HTTP to HTTPS redirect in production/staging
- Handles proxy headers (X-Forwarded-Proto)
- Adds HSTS header to HTTPS responses
- Configurable per environment

```python
# Usage in main.py
app.add_middleware(HTTPSRedirectMiddleware)
```

### 2. CORS Configuration with HTTPS

Located at: `backend/app/core/cors_https.py`

Features:
- Environment-aware origin configuration
- HTTPS-only origins in production
- Wildcard support for development
- Dynamic origin validation

Allowed origins by environment:
- **Development**: localhost, local network IPs, Expo
- **Production**: HTTPS domains only (roadtrip.app, www.roadtrip.app, etc.)
- **Staging**: Includes staging domains

### 3. Secure Cookie Configuration

Authentication cookies are configured with:
- `secure=True` in production (HTTPS only)
- `httpOnly=True` (no JavaScript access)
- `sameSite="lax"` (CSRF protection)

### 4. Dynamic URL Generation

The config module provides methods for environment-aware URLs:

```python
# Get appropriate Spotify redirect URI
redirect_uri = settings.get_spotify_redirect_uri(request.url.scheme)

# Get base URL for the application
base_url = settings.get_base_url(request.url.scheme)
```

## Environment Variables

Add to `.env` for configuration:

```bash
# Environment (development, staging, production)
ENVIRONMENT=development

# Force HTTPS redirects (overrides environment detection)
FORCE_HTTPS=false

# Use secure cookies (auto-enabled in production)
SECURE_COOKIES=false
```

## Testing HTTPS Configuration

### Local Testing with HTTPS

1. Generate self-signed certificate:
```bash
python scripts/generate_ssl_certificates.py --env development --self-signed
```

2. Run with HTTPS:
```bash
FORCE_HTTPS=true uvicorn backend.app.main:app --ssl-keyfile=certs/localhost/privkey.pem --ssl-certfile=certs/localhost/fullchain.pem
```

3. Test redirect:
```bash
curl -I http://localhost:8000/api/health
# Should return 301 redirect to https://localhost:8000/api/health
```

### Production Verification

1. Check HTTPS redirect:
```bash
curl -I http://api.roadtrip.app/health
# Should return 301 with Location: https://api.roadtrip.app/health
```

2. Verify HSTS header:
```bash
curl -I https://api.roadtrip.app/health | grep Strict-Transport-Security
# Should show: Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

3. Test CORS headers:
```bash
curl -H "Origin: https://roadtrip.app" https://api.roadtrip.app/api/health
# Should include Access-Control-Allow-Origin: https://roadtrip.app
```

## Integration Points

### 1. Spotify OAuth
- Redirect URI automatically uses HTTPS in production
- Dynamically adjusts based on request scheme
- Handles both development and production flows

### 2. API Links
- All generated links respect the current scheme
- Email links use appropriate protocol
- Webhook URLs are environment-aware

### 3. WebSocket Connections
- WSS (secure WebSocket) in production
- Automatic protocol selection

## Security Checklist

- [ ] HTTPS redirect middleware is first in chain
- [ ] CORS allows only HTTPS origins in production
- [ ] Cookies have secure flag in production
- [ ] HSTS header is present on HTTPS responses
- [ ] No mixed content warnings
- [ ] API generates HTTPS URLs in production
- [ ] OAuth redirect URIs use HTTPS
- [ ] WebSocket connections use WSS

## Common Issues

### Mixed Content Warnings
- Ensure all API calls use HTTPS
- Check for hardcoded HTTP URLs
- Verify CDN resources use HTTPS

### Cookie Not Sent
- Verify secure flag matches protocol
- Check SameSite settings
- Ensure domain matches

### CORS Errors
- Verify origin is in allowed list
- Check for trailing slashes
- Ensure protocol matches (HTTP vs HTTPS)

## Monitoring

Monitor for:
- HTTP requests to production (should be 0)
- HTTPS redirect success rate
- Mixed content errors in browser console
- Cookie transmission failures

## Next Steps

1. Configure CDN for HTTPS
2. Set up HSTS preload submission
3. Implement Certificate Transparency monitoring
4. Add CSP reporting endpoint