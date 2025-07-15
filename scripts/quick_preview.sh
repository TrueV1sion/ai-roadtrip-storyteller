#!/bin/bash

# Quick Preview Script - Minimal setup for viewing the application
# This script provides the fastest way to preview the app with minimal configuration

echo "🚀 AI Road Trip Storyteller - Quick Preview Mode"
echo "================================================"

# Create minimal .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Minimal configuration for preview
ENVIRONMENT=development
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://roadtrip:roadtrip@localhost:5432/roadtrip_dev
REDIS_URL=redis://localhost:6379/0
GOOGLE_AI_PROJECT_ID=demo-mode
MOCK_AI_RESPONSES=true
LOG_LEVEL=INFO
EOF
    echo "✓ Created minimal .env file for preview"
fi

# Start only essential services
echo ""
echo "Starting essential services..."

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services
sleep 5

# Install minimal Python dependencies
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis pydantic python-jose passlib

# Simple database initialization
cd backend
python3 -c "
from app.core.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('✓ Database initialized')
"
cd ..

# Start backend in demo mode
echo ""
echo "Starting Backend API in demo mode..."
cd backend
MOCK_AI_RESPONSES=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Install minimal mobile dependencies
echo ""
echo "Preparing mobile preview..."
cd mobile
npm install --production
cd ..

# Display preview information
echo ""
echo "================================================"
echo "✓ Preview environment ready!"
echo ""
echo "Preview URLs:"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • API Health Check:  http://localhost:8000/health"
echo ""
echo "To view mobile app:"
echo "  cd mobile && npm start"
echo ""
echo "Note: This is a preview mode with:"
echo "  • Mock AI responses (no Google Cloud required)"
echo "  • Basic features only"
echo "  • No external API integrations"
echo ""
echo "For full features, use ./scripts/start_dev_environment.sh"
echo "================================================"

# Save PID for cleanup
echo "BACKEND_PID=$BACKEND_PID" > .preview_pid

# Open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8000/docs
elif command -v open > /dev/null; then
    open http://localhost:8000/docs
fi

echo ""
echo "Press Ctrl+C to stop preview..."
trap 'kill $BACKEND_PID; docker-compose down; rm .preview_pid; exit' INT
wait