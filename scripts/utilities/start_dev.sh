#!/bin/bash
# Development environment startup script for AI Road Trip Storyteller

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}AI Road Trip Storyteller - Development Environment${NC}"
echo -e "${BLUE}===================================================${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service on port $port..."
    while ! nc -z localhost $port >/dev/null 2>&1; do
        if [ $attempt -ge $max_attempts ]; then
            echo -e " ${RED}Failed${NC}"
            return 1
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo -e " ${GREEN}Ready${NC}"
    return 0
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command_exists docker; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker Desktop and try again"
    
    # OS-specific instructions
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "On macOS: Open Docker from Applications or run: open -a Docker"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "On Windows: Start Docker Desktop from the Start Menu"
    else
        echo "On Linux: Run: sudo systemctl start docker"
    fi
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check Python
if command_exists python3; then
    PYTHON_CMD=python3
elif command_exists python; then
    PYTHON_CMD=python
else
    echo -e "${RED}✗ Python is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python is available${NC}"

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "Creating .env from template..."
    if [ -f .env.template ]; then
        cp .env.template .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
    else
        echo -e "${RED}Please create a .env file first${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Update .env for local development
echo -e "\n${YELLOW}Configuring for local development...${NC}"
if grep -q "ENVIRONMENT=production" .env; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' 's/ENVIRONMENT=production/ENVIRONMENT=development/g' .env
    else
        sed -i 's/ENVIRONMENT=production/ENVIRONMENT=development/g' .env
    fi
    echo -e "${GREEN}✓ Set ENVIRONMENT=development${NC}"
fi

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"

# Stop any existing containers
docker-compose down >/dev/null 2>&1 || true

# Start PostgreSQL and Redis
echo "Starting PostgreSQL and Redis..."
docker-compose up -d db redis

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to start...${NC}"
wait_for_service "PostgreSQL" 5432
wait_for_service "Redis" 6379

# Check database connection
echo -e "\n${YELLOW}Checking database connection...${NC}"
export DATABASE_URL=$(grep DATABASE_URL .env | cut -d'=' -f2-)
if $PYTHON_CMD -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${YELLOW}⚠ Database connection failed - will retry after migrations${NC}"
fi

# Run database migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
if command_exists alembic; then
    alembic upgrade head && echo -e "${GREEN}✓ Migrations completed${NC}" || echo -e "${YELLOW}⚠ Migrations failed - database might not be ready${NC}"
else
    echo -e "${YELLOW}⚠ Alembic not installed - skipping migrations${NC}"
    echo "Install with: pip install alembic"
fi

# Install Python dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Check if dependencies are installed
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Display service URLs
echo -e "\n${BLUE}===================================================${NC}"
echo -e "${GREEN}✓ Development environment is ready!${NC}"
echo -e "${BLUE}===================================================${NC}"

echo -e "\n${YELLOW}Services running:${NC}"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"

echo -e "\n${YELLOW}To start the API server:${NC}"
echo "  uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"

echo -e "\n${YELLOW}To start the mobile app:${NC}"
echo "  cd mobile && npm install && npm start"

echo -e "\n${YELLOW}To stop services:${NC}"
echo "  docker-compose down"

echo -e "\n${YELLOW}To view logs:${NC}"
echo "  docker-compose logs -f"

echo -e "\n${YELLOW}API Documentation will be available at:${NC}"
echo "  http://localhost:8000/docs"

# Option to start the API server
echo -e "\n${YELLOW}Would you like to start the API server now? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "\n${YELLOW}Starting API server...${NC}"
    uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
fi