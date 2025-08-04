#!/usr/bin/env python3
"""
Gunicorn Production Configuration - Six Sigma Implementation
Optimized for horizontal scaling and high availability
"""

import multiprocessing
import os
from datetime import datetime

# Bind to PORT environment variable (for Cloud Run) or default
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker configuration
# Formula: (2 * CPU_COUNT) + 1 for optimal performance
cpu_count = multiprocessing.cpu_count()
workers = min(int(os.environ.get('GUNICORN_WORKERS', (2 * cpu_count) + 1)), 8)
worker_class = 'uvicorn.workers.UvicornWorker'  # Async worker for FastAPI
worker_connections = 1000

# Worker lifecycle
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 100  # Randomize restart to avoid thundering herd
timeout = 600  # Kill workers that don't respond in 10 minutes (matches Cloud Run timeout)
graceful_timeout = 30  # Grace period for workers to finish requests
keepalive = 5  # Keep connections alive for 5 seconds

# Performance optimizations
preload_app = True  # Load app before forking workers
reuse_port = True  # Enable SO_REUSEPORT for better load distribution

# Logging configuration
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = (
    '%(t)s %(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" '
    'request_id=%({X-Request-ID}i)s response_time=%(L)sms'
)

# StatsD integration for metrics
statsd_host = os.environ.get('STATSD_HOST', 'localhost:8125')
if os.environ.get('ENABLE_STATSD', 'false').lower() == 'true':
    statsd_prefix = 'roadtrip.gunicorn'

# Server mechanics
proc_name = 'roadtrip-api'  # Process name for monitoring
chdir = '/app'  # Change to app directory (correct path in container)
pidfile = '/tmp/gunicorn.pid'  # PID file location
user = None  # Run as current user (container user)
group = None  # Run as current group
tmp_upload_dir = '/tmp'  # Temp directory for uploads

# SSL/TLS (handled by Cloud Run/Load Balancer)
forwarded_allow_ips = '*'  # Trust X-Forwarded-* headers
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'https',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Server hooks for lifecycle management
def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn server ready with {workers} workers")
    server.log.info(f"Worker class: {worker_class}")
    server.log.info(f"Worker connections: {worker_connections}")
    
    # Create readiness indicator
    with open('/tmp/ready', 'w') as f:
        f.write(str(datetime.now()))

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Pre-fork: Worker spawning...")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Post-fork: Worker {worker.pid} spawned")
    
    # Reset database connections in forked process
    # This is critical for connection pool safety
    try:
        from app.core.database import engine
        engine.dispose()
    except ImportError:
        pass

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process...")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    # Add request timing
    req.start_time = datetime.now()
    
    # Log request start (debug level)
    worker.log.debug(f"{req.method} {req.path} - Start processing")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    # Calculate request duration
    duration = (datetime.now() - req.start_time).total_seconds() * 1000
    
    # Log request completion with duration
    worker.log.info(
        f"{req.method} {req.path} - {resp.status} - {duration:.2f}ms"
    )

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} interrupted")

def worker_abort(worker):
    """Called when a worker is killed by timeout."""
    worker.log.error(f"Worker {worker.pid} aborted (timeout)")
    
    # Log stack trace for debugging
    import traceback
    import sys
    traceback.print_stack(file=sys.stderr)

def child_exit(server, worker):
    """Called just after a worker has been killed."""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has exited."""
    server.log.info(f"Worker {worker.pid} cleanup complete")

def nworkers_changed(server, new_value, old_value):
    """Called when number of workers changes."""
    server.log.info(f"Worker count changed: {old_value} -> {new_value}")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Gunicorn master shutting down")
    
    # Remove readiness indicator
    try:
        os.remove('/tmp/ready')
    except:
        pass

# Health check configuration
health_check_interval = 30  # Seconds between health checks
health_check_timeout = 10   # Seconds before health check times out

# Production optimizations based on expected load
# These can be tuned based on monitoring data
if os.environ.get('ENVIRONMENT') == 'production':
    # Production settings
    workers = min(workers, 8)  # Cap at 8 workers
    max_requests = 10000  # Higher request limit
    timeout = 600  # 10 minute timeout for long AI operations (matches Cloud Run)
    graceful_timeout = 60  # More grace time
    
    # Enable New Relic if available
    try:
        import newrelic.agent
        newrelic.agent.initialize('/app/newrelic.ini')
    except ImportError:
        pass

# Development optimizations
elif os.environ.get('ENVIRONMENT') == 'development':
    workers = 2  # Fewer workers for development
    reload = True  # Auto-reload on code changes
    reload_extra_files = ['./app/']  # Watch additional files
    timeout = 600  # Longer timeout for debugging

# Memory optimization settings
limit_request_line = 4096  # Max request line size
limit_request_fields = 100  # Max number of headers
limit_request_field_size = 8192  # Max header size

# Security headers (additional to app middleware)
raw_env = [
    f'PROMETHEUS_MULTIPROC_DIR={os.environ.get("PROMETHEUS_MULTIPROC_DIR", "/tmp")}',
]

# Graceful shutdown configuration
def handle_term(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    import sys
    sys.exit(0)

def handle_hup(signum, frame):
    """Handle SIGHUP for configuration reload."""
    # Reload configuration without dropping connections
    pass

# Register signal handlers
import signal
signal.signal(signal.SIGTERM, handle_term)
signal.signal(signal.SIGHUP, handle_hup)

# Export configuration summary
print(f"Gunicorn Configuration Summary:")
print(f"  Workers: {workers}")
print(f"  Worker Class: {worker_class}")
print(f"  Bind: {bind}")
print(f"  Timeout: {timeout}s")
print(f"  Max Requests: {max_requests}")
print(f"  Preload App: {preload_app}")