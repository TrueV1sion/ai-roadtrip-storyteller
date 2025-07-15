#!/bin/bash

# AI Road Trip Storyteller - Development Environment Startup Script
# This script sets up and launches all services needed for local development

set -e

echo "🚗 AI Road Trip Storyteller - Development Environment Setup"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for a service
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $name..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null $url; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}✗${NC} Node.js not found. Please install Node.js 16 or higher."
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js found: $(node --version)"

# Check Docker
if ! command_exists docker; then
    echo -e "${RED}✗${NC} Docker not found. Please install Docker."
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker found: $(docker --version)"

# Check Docker Compose
if ! command_exists docker-compose; then
    echo -e "${RED}✗${NC} Docker Compose not found. Please install Docker Compose."
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker Compose found: $(docker-compose --version)"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠${NC}  .env file not found. Creating from template..."
    cp .env.example .env
    echo -e "${YELLOW}⚠${NC}  Please edit .env file with your API keys before continuing."
    echo "    Required keys:"
    echo "    - GOOGLE_AI_PROJECT_ID"
    echo "    - GOOGLE_MAPS_API_KEY"
    echo "    - DATABASE_URL"
    echo "    - REDIS_URL"
    echo "    - SECRET_KEY"
    read -p "Press Enter after updating .env file..."
fi

# Check if ports are available
echo ""
echo "Checking port availability..."
PORTS=(8000 5432 6379 3000 9090)
SERVICES=("Backend API" "PostgreSQL" "Redis" "Mobile App" "Prometheus")

for i in "${!PORTS[@]}"; do
    if port_in_use ${PORTS[$i]}; then
        echo -e "${RED}✗${NC} Port ${PORTS[$i]} is in use (needed for ${SERVICES[$i]})"
        echo "  Please stop the service using this port or change the port in .env"
        exit 1
    else
        echo -e "${GREEN}✓${NC} Port ${PORTS[$i]} is available (${SERVICES[$i]})"
    fi
done

# Start infrastructure services
echo ""
echo "Starting infrastructure services..."
docker-compose up -d postgres redis

# Wait for database
wait_for_service "PostgreSQL" "http://localhost:5432" || {
    echo -e "${RED}Failed to start PostgreSQL${NC}"
    exit 1
}

# Wait for Redis
wait_for_service "Redis" "http://localhost:6379" || {
    echo -e "${RED}Failed to start Redis${NC}"
    exit 1
}

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo ""
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Start Knowledge Graph
echo ""
echo "Starting Knowledge Graph service..."
cd knowledge_graph
if ! port_in_use 8001; then
    python3 blazing_server.py &
    KG_PID=$!
    cd ..
    wait_for_service "Knowledge Graph" "http://localhost:8001/api/health" || {
        echo -e "${RED}Failed to start Knowledge Graph${NC}"
        exit 1
    }
else
    echo -e "${GREEN}✓${NC} Knowledge Graph already running"
    cd ..
fi

# Start Backend API
echo ""
echo "Starting Backend API..."
cd backend
if ! port_in_use 8000; then
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    wait_for_service "Backend API" "http://localhost:8000/health" || {
        echo -e "${RED}Failed to start Backend API${NC}"
        exit 1
    }
else
    echo -e "${GREEN}✓${NC} Backend API already running"
    cd ..
fi

# Install Mobile dependencies
echo ""
echo "Installing Mobile app dependencies..."
cd mobile
if [ ! -d "node_modules" ]; then
    npm install
fi

# Start Mobile app
echo ""
echo "Starting Mobile app..."
npm start &
MOBILE_PID=$!
cd ..

# Display access information
echo ""
echo "=========================================================="
echo -e "${GREEN}✓ Development environment is ready!${NC}"
echo ""
echo "Access points:"
echo "  • Backend API:      http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Knowledge Graph:   http://localhost:8001"
echo "  • Mobile App:        http://localhost:3000 (or scan QR code)"
echo ""
echo "Monitoring (if enabled):"
echo "  • Prometheus:        http://localhost:9090"
echo "  • Grafana:          http://localhost:3001"
echo ""
echo "To stop all services, run: ./scripts/stop_dev_environment.sh"
echo ""
echo "Tips:"
echo "  • Check logs: docker-compose logs -f [service]"
echo "  • Backend logs: tail -f backend/logs/app.log"
echo "  • Mobile logs: Check terminal where npm start is running"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:8000/docs to test API endpoints"
echo "  2. Use Expo Go app to scan QR code for mobile preview"
echo "  3. Or use iOS/Android simulator with 'npm run ios' or 'npm run android'"
echo "=========================================================="

# Create PID file for cleanup
echo "BACKEND_PID=$BACKEND_PID" > .dev_pids
echo "MOBILE_PID=$MOBILE_PID" >> .dev_pids
echo "KG_PID=$KG_PID" >> .dev_pids

# Keep script running
echo ""
echo "Press Ctrl+C to stop all services..."
trap 'echo "Stopping services..."; ./scripts/stop_dev_environment.sh; exit' INT
wait