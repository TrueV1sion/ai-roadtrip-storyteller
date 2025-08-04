#!/usr/bin/env python3
"""
Production Gunicorn Configuration for Google Cloud Run
Optimized for AI operations, async FastAPI, and Cloud Run constraints
"""

import multiprocessing
import os
from datetime import datetime

# Bind to PORT environment variable (required for Cloud Run)
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker configuration for Cloud Run
# Cloud Run provides 1-8 vCPUs per instance, use conservative defaults
cpu_count = multiprocessing.cpu_count()
workers = int(os.environ.get('GUNICORN_WORKERS', min(cpu_count * 2, 4)))
worker_class = 'uvicorn.workers.UvicornWorker'  # Required for FastAPI async
worker_connections = 1000
threads = 1  # Not used with async workers but kept for compatibility

# Timeouts aligned with Cloud Run (max 60 minutes but we use 10 for safety)
timeout = 600  # 10 minutes for AI operations
graceful_timeout = 30  # Time to finish current requests on shutdown
keepalive = 5  # Keep-alive for connection reuse

# Worker lifecycle management
max_requests = 10000  # Restart workers after this many requests
max_requests_jitter = 1000  # Randomize to prevent thundering herd

# Performance optimizations
preload_app = True  # Load app before forking (saves memory)
reuse_port = True  # Better load distribution

# Logging configuration (Cloud Run captures stdout/stderr)
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = (
    '%(t)s [%(p)s] %(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" '
    'request_id=%({X-Request-ID}i)s response_time=%(L)sms'
)

# Server mechanics
proc_name = 'roadtrip-api'
daemon = False  # Don't daemonize (required for containers)
pidfile = None  # No pidfile in containers
user = None  # Run as container user
group = None  # Run as container group
tmp_upload_dir = None  # Use system default

# Security - trust Cloud Run's proxy
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTO': 'https',
}

# Disable admin endpoints in production
worker_int = None  # Disable worker interrupt hooks for security

# Server hooks for monitoring and lifecycle
def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn master ready with {workers} workers")
    server.log.info(f"Worker class: {worker_class}")
    server.log.info(f"Timeout: {timeout}s")
    # Create readiness file for health checks
    with open('/tmp/ready', 'w') as f:
        f.write(str(datetime.utcnow().isoformat()))

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Forking new worker...")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")
    
    # Critical: Reset database connections after fork
    # This prevents connection pool corruption
    try:
        from app.core.database import engine
        engine.dispose()
        server.log.info(f"Worker {worker.pid}: Database connections reset")
    except Exception as e:
        server.log.error(f"Worker {worker.pid}: Failed to reset database: {e}")

def pre_request(worker, req):
    """Called just before a worker processes a request."""
    req._start_time = datetime.utcnow()
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes a request."""
    duration = (datetime.utcnow() - req._start_time).total_seconds()
    worker.log.info(
        f"{req.method} {req.path} - {resp.status} - {duration:.3f}s"
    )

def worker_abort(worker):
    """Called when a worker is killed by timeout."""
    worker.log.error(f"Worker {worker.pid} timed out!")
    # Log current stack trace for debugging
    import traceback
    import sys
    worker.log.error("Stack trace:")
    traceback.print_stack(file=sys.stderr)

def on_exit(server):
    """Called just before master process exits."""
    server.log.info("Gunicorn master shutting down")
    # Remove readiness indicator
    try:
        os.remove('/tmp/ready')
    except:
        pass

# Cloud Run specific optimizations
if os.environ.get('K_SERVICE'):  # Running on Cloud Run
    # Use all available CPUs (Cloud Run provides them)
    workers = min(int(os.environ.get('GUNICORN_WORKERS', cpu_count * 2)), 8)
    
    # Cloud Run handles SSL/TLS
    forwarded_allow_ips = '*'
    
    # Optimize for Cloud Run's networking
    worker_connections = 10000
    
    # Log Cloud Run metadata
    print(f"Cloud Run Service: {os.environ.get('K_SERVICE')}")
    print(f"Cloud Run Revision: {os.environ.get('K_REVISION')}")

# Memory optimization
limit_request_line = 8190  # Max request line size
limit_request_fields = 200  # Max number of headers  
limit_request_field_size = 8190  # Max header size

# StatsD metrics (if configured)
if os.environ.get('STATSD_HOST'):
    statsd_host = os.environ.get('STATSD_HOST')
    statsd_prefix = 'roadtrip.gunicorn'

# Configuration summary (logged at startup)
print("=" * 60)
print("Gunicorn Production Configuration")
print("=" * 60)
print(f"Workers: {workers}")
print(f"Worker Class: {worker_class}")
print(f"Bind: {bind}")
print(f"Timeout: {timeout}s")
print(f"Graceful Timeout: {graceful_timeout}s")
print(f"Max Requests: {max_requests}")
print(f"Preload: {preload_app}")
print(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
print("=" * 60)