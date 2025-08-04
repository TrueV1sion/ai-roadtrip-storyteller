#!/bin/sh
# Production startup script for Google Cloud Run
# Uses Gunicorn configuration file for consistency

set -e

echo "Starting RoadTrip API server..."

# Use the production configuration file if it exists, otherwise fall back to command line args
if [ -f "/app/gunicorn.prod.conf.py" ]; then
    echo "Using production Gunicorn configuration"
    exec gunicorn app.main:app -c /app/gunicorn.prod.conf.py
else
    echo "Using default Gunicorn configuration"
    exec gunicorn app.main:app \
        --bind :${PORT:-8080} \
        --workers ${GUNICORN_WORKERS:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 600 \
        --graceful-timeout 30 \
        --keep-alive 5 \
        --max-requests 10000 \
        --max-requests-jitter 1000 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        --preload
fi