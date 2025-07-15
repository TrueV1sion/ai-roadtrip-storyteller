# CSRF Protection Implementation

This document describes the Cross-Site Request Forgery (CSRF) protection mechanism implemented in the AI Road Trip Storyteller application.

## Overview

Cross-Site Request Forgery (CSRF) is an attack that forces authenticated users to execute unwanted actions on a web application in which they're currently authenticated. We've implemented a robust CSRF protection mechanism to prevent such attacks.

## Implementation Details

### Backend Implementation

1. **CSRF Token Generation and Validation**
   - Created a dedicated `csrf.py` module in the `app/core/` directory
   - Implemented secure token generation using cryptographically secure random bytes
   - Implemented token signing using JWT to prevent tampering
   - Created validation functions to verify token integrity

2. **CSRF Middleware**
   - Implemented `CSRFMiddleware` to automatically protect all non-safe HTTP methods (POST, PUT, PATCH, DELETE)
   - Safe methods (GET, HEAD, OPTIONS) bypass CSRF verification
   - Integrated the middleware into the FastAPI application in `main.py`

3. **Token Distribution Endpoint**
   - Added a `/api/csrf-token` endpoint in `utils.py` to provide tokens to clients
   - The endpoint returns the token in three ways to support both web and mobile clients:
     - As an HTTP-only cookie (for web clients)
     - In the response headers (for mobile clients)
     - In the response body (for maximum compatibility)

4. **Dependency for Manual Protection**
   - Created a `csrf_protect` dependency that can be used to protect specific endpoints

### Frontend Implementation

1. **CSRF Token Management in API Client**
   - Updated `ApiClient.ts` to handle CSRF tokens
   - Added methods to fetch, store, and retrieve CSRF tokens
   - Implemented token storage using SecureStore with AsyncStorage fallback
   - Added token refresh logic for failed requests due to invalid CSRF tokens

2. **CSRF Token in Requests**
   - Updated all unsafe HTTP methods (POST, PUT, PATCH, DELETE) to include CSRF tokens
   - Added retry logic for CSRF-related failures
   - Configured the client to automatically fetch new tokens when needed

3. **Configuration Updates**
   - Added CSRF-related constants to the configuration files
   - Updated the client to handle cookies properly with `credentials: 'include'`

### Testing

Created a comprehensive test suite in `tests/test_csrf_protection.py` that verifies:
- CSRF token generation
- Protected endpoint access with valid tokens
- Protected endpoint rejection with invalid or missing tokens
- Safe methods bypassing CSRF protection
- Token verification failure handling

## Security Considerations

1. **Token Storage**: CSRF tokens are stored securely using:
   - HTTP-only cookies on the web
   - SecureStore on mobile (with AsyncStorage fallback)

2. **Token Transmission**: CSRF tokens are transmitted via:
   - Cookies for session identification
   - Custom headers for verification (`X-CSRF-Token`)

3. **Implementation Pattern**: We've implemented the Double Submit Cookie pattern, where:
   - The server sets a cookie with the token
   - The client must submit the same token in a custom header
   - The server verifies that both tokens match

## Usage for Developers

### Backend Developers

To protect a new endpoint:

```python
from app.core.csrf import csrf_protect
from fastapi import Depends

@router.post("/endpoint", dependencies=[Depends(csrf_protect)])
async def protected_endpoint():
    # Your endpoint logic here
    pass
```

### Frontend Developers

The API client automatically handles CSRF tokens. For new API calls:

```typescript
// The client automatically includes CSRF tokens for unsafe methods
const response = await apiClient.post('/api/endpoint', data);
```

To manually refresh the CSRF token:

```typescript
await apiClient.fetchCSRFToken();
```

## Future Improvements

1. Replace the in-memory token blacklist with Redis or another distributed cache for production
2. Implement token rotation for enhanced security
3. Add more granular control over which endpoints require CSRF protection