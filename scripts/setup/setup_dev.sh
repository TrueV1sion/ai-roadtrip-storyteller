#!/bin/bash

# AI Road Trip Storyteller - Development Setup Script

set -e  # Exit on error

echo "🚗 Setting up AI Road Trip Storyteller Development Environment..."

# Check for required tools
echo "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate || . venv/Scripts/activate  # Handle both Unix and Windows

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual configuration values!"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p backend/uploads
mkdir -p backend/static

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d db redis

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Create test user (optional)
echo "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual API keys and configuration"
echo "2. Start the backend: docker-compose up backend"
echo "3. Or run locally: cd backend && uvicorn app.main:app --reload"
echo "4. Access the API docs at: http://localhost:8000/docs"
echo ""
echo "For monitoring (optional):"
echo "docker-compose --profile monitoring up -d"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (admin/admin)"