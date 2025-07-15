"""
Production Security Monitoring Middleware
Real-time request analysis and threat detection
"""

import time
import json
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logger import get_logger
from app.monitoring.security_monitor_v2 import (
    security_monitor_v2,
    SecurityEventType,
    ThreatLevel
)
from app.core.cache import cache_manager

logger = get_logger(__name__)


class SecurityMonitoringMiddlewareV2(BaseHTTPMiddleware):
    """Production security monitoring middleware with threat detection."""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_monitor = security_monitor_v2
        
        # Paths to exclude from monitoring
        self.excluded_paths = {
            '/health', '/metrics', '/docs', '/openapi.json',
            '/favicon.ico', '/static', '/_next'
        }
        
        # High-risk endpoints requiring extra monitoring
        self.high_risk_endpoints = {
            '/api/auth/login', '/api/auth/register', '/api/auth/reset-password',
            '/api/admin', '/api/users/*/role', '/api/payments'
        }
        
        logger.info("Security Monitoring Middleware V2 initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with comprehensive security monitoring."""
        start_time = time.time()
        
        # Skip monitoring for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Extract request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', '')
        
        # Get user ID from request state if authenticated
        user_id = getattr(request.state, 'user_id', None)
        
        # Prepare request data for analysis
        request_data = await self._prepare_request_data(request)
        
        # Analyze request for threats
        threat_analysis = await self.security_monitor.analyze_request(request_data)
        
        # Check if request should be blocked
        if threat_analysis['blocked'] or threat_analysis['threat_level'] == 'critical':
            # Log security event
            await self.security_monitor.log_event(
                event_type=SecurityEventType.INTRUSION_DETECTED,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                endpoint=request.url.path,
                details={
                    'method': request.method,
                    'threats': threat_analysis['threats'],
                    'action': 'blocked'
                }
            )
            
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Request blocked due to security concerns",
                    "error_code": "SECURITY_BLOCK"
                }
            )
        
        # Add threat score to request state
        request.state.threat_score = threat_analysis.get('threat_score', 0)
        request.state.threat_level = threat_analysis.get('threat_level', 'low')
        
        # Process request
        response = None
        error_occurred = False
        status_code = 200
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Check for security-relevant status codes
            if status_code == 401:
                await self._handle_unauthorized(request, client_ip, user_agent)
            elif status_code == 403:
                await self._handle_forbidden(request, client_ip, user_agent, user_id)
            elif status_code >= 500:
                error_occurred = True
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            error_occurred = True
            status_code = 500
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log security-relevant events
        if threat_analysis['threat_level'] in ['medium', 'high']:
            await self.security_monitor.log_event(
                event_type=SecurityEventType.SUSPICIOUS_PATTERN,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                endpoint=request.url.path,
                details={
                    'method': request.method,
                    'status_code': status_code,
                    'duration': duration,
                    'threat_analysis': threat_analysis
                }
            )
        
        # Add security headers to response
        if response:
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Add threat level header for monitoring
            if threat_analysis['threat_level'] != 'low':
                response.headers['X-Threat-Level'] = threat_analysis['threat_level']
        
        return response
    
    async def _prepare_request_data(self, request: Request) -> Dict[str, Any]:
        """Prepare request data for security analysis."""
        # Get request body safely
        body = ""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Store body for later use in request
                body_bytes = await request.body()
                request._body = body_bytes
                body = body_bytes.decode('utf-8', errors='ignore')[:1000]  # Limit size
            except:
                pass
        
        # Extract query parameters
        query_params = dict(request.query_params)
        
        # Get headers (excluding sensitive ones)
        headers = {}
        sensitive_headers = {'authorization', 'cookie', 'x-api-key'}
        for key, value in request.headers.items():
            if key.lower() not in sensitive_headers:
                headers[key.lower()] = value
        
        return {
            'path': request.url.path,
            'method': request.method,
            'query_params': query_params,
            'headers': headers,
            'body': body,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent', ''),
            'referer': request.headers.get('referer', '')
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IPs (reverse proxy)
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            # Get the first IP in the chain
            return forwarded.split(',')[0].strip()
        
        # Check other headers
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _handle_unauthorized(self, request: Request, ip_address: str, user_agent: str):
        """Handle 401 Unauthorized responses."""
        # Check for authentication endpoints
        if '/auth/' in request.url.path:
            # Likely a failed login
            username = None
            try:
                if hasattr(request, '_body'):
                    body = json.loads(request._body)
                    username = body.get('email') or body.get('username')
            except:
                pass
            
            await self.security_monitor.log_event(
                event_type=SecurityEventType.LOGIN_FAILURE,
                user_id=username,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=request.url.path,
                details={'method': request.method}
            )
        else:
            # Unauthorized access attempt
            await self.security_monitor.log_event(
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=request.url.path,
                details={'method': request.method}
            )
    
    async def _handle_forbidden(self, request: Request, ip_address: str, user_agent: str, user_id: Optional[str]):
        """Handle 403 Forbidden responses."""
        # Could be permission denied or CSRF violation
        event_type = SecurityEventType.PERMISSION_DENIED
        
        # Check if it's a CSRF violation
        if 'csrf' in request.url.path.lower() or request.headers.get('x-csrf-token'):
            event_type = SecurityEventType.CSRF_VIOLATION
        
        await self.security_monitor.log_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=request.url.path,
            details={'method': request.method}
        )