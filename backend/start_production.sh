#!/bin/bash
# Production startup script with health checks and graceful shutdown

set -e

# Environment setup
export PYTHONUNBUFFERED=1
export PROMETHEUS_MULTIPROC_DIR=${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}

# Create necessary directories
mkdir -p $PROMETHEUS_MULTIPROC_DIR
mkdir -p /tmp/logs

# Clean up any stale Prometheus metrics
rm -f $PROMETHEUS_MULTIPROC_DIR/*.db

# Database migration check
echo "Checking database migrations..."
python -m alembic upgrade head || {
    echo "Database migration failed!"
    exit 1
}

# Pre-flight checks
echo "Running pre-flight checks..."
python -c "
import sys
sys.path.insert(0, '/app')

# Test database connection
from backend.app.core.database import engine
try:
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    sys.exit(1)

# Test Redis connection
from backend.app.core.cache import cache_manager
try:
    import asyncio
    asyncio.run(cache_manager.redis_client.client.ping())
    print('✓ Redis connection successful')
except Exception as e:
    print(f'⚠ Redis connection failed (non-critical): {e}')

print('Pre-flight checks completed')
"

# Signal handlers for graceful shutdown
trap 'echo "SIGTERM received, initiating graceful shutdown..."; kill -TERM $PID' TERM
trap 'echo "SIGINT received, forcing shutdown..."; kill -INT $PID' INT

# Start Gunicorn with production configuration
echo "Starting Gunicorn with horizontal scaling configuration..."
exec gunicorn backend.app.main:app \
    -c backend/gunicorn_config.py \
    --pid /tmp/gunicorn.pid &

PID=$!

# Wait for Gunicorn to start
sleep 2

# Health check loop
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_FAILURES=0
MAX_HEALTH_CHECK_FAILURES=3

while true; do
    # Check if Gunicorn is still running
    if ! kill -0 $PID 2>/dev/null; then
        echo "Gunicorn process died unexpectedly"
        exit 1
    fi
    
    # Perform health check
    if curl -f -s http://localhost:${PORT:-8080}/health/v2/ready > /dev/null; then
        HEALTH_CHECK_FAILURES=0
    else
        HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
        echo "Health check failed ($HEALTH_CHECK_FAILURES/$MAX_HEALTH_CHECK_FAILURES)"
        
        if [ $HEALTH_CHECK_FAILURES -ge $MAX_HEALTH_CHECK_FAILURES ]; then
            echo "Too many health check failures, restarting..."
            kill -TERM $PID
            wait $PID
            exit 1
        fi
    fi
    
    # Wait for next check or signal
    sleep $HEALTH_CHECK_INTERVAL &
    wait $!
done