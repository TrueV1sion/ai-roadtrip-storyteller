"""
Security Monitoring Middleware - Production Implementation
Routes to V2 implementation for backward compatibility
"""

from app.middleware.security_monitoring_v2 import SecurityMonitoringMiddlewareV2

# Use V2 implementation directly
SecurityMonitoringMiddleware = SecurityMonitoringMiddlewareV2
