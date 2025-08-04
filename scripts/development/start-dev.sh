#!/bin/bash
# AI Road Trip Storyteller - Development Environment Startup Script
# This script starts all services needed for development

set -e

echo "🚗 AI Road Trip Storyteller - Starting Development Environment"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js 16+ first.${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}❌ npm is not installed. Please install npm first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file. Please edit it with your API keys.${NC}"
    else
        echo -e "${RED}❌ No .env.example found. Please create a .env file.${NC}"
        exit 1
    fi
fi

# Start backend services
echo ""
echo "🚀 Starting backend services..."
cd infrastructure/docker

# Stop any existing containers
docker-compose down 2>/dev/null || true

# Start all services
echo "Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."

wait_for_service "Knowledge Graph" "http://localhost:8000/api/health"
wait_for_service "Backend API" "http://localhost:8001/health"
wait_for_service "Redis" "http://localhost:6379" || echo -e "${YELLOW}⚠️  Redis health check skipped${NC}"

# Run database migrations
echo ""
echo "🗄️  Running database migrations..."
docker-compose exec -T backend alembic upgrade head || echo -e "${YELLOW}⚠️  Migrations may have already been applied${NC}"

# Display service URLs
echo ""
echo "✅ Backend services are running!"
echo ""
echo "📍 Service URLs:"
echo "   - Knowledge Graph: http://localhost:8000"
echo "   - Backend API: http://localhost:8001"
echo "   - API Documentation: http://localhost:8001/docs"
echo "   - Database Admin: http://localhost:8080"
echo "   - Celery Flower: http://localhost:5555"

# Start mobile app in a new terminal
echo ""
echo "📱 Starting mobile app..."
cd ../../mobile

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing mobile app dependencies..."
    npm install
fi

# Create a script to run the mobile app
cat > run-mobile.sh << 'EOF'
#!/bin/bash
echo "📱 Starting Expo development server..."
echo ""
echo "Choose your platform:"
echo "  Press 'w' for web browser"
echo "  Press 'i' for iOS simulator"
echo "  Press 'a' for Android emulator"
echo "  Scan QR code with Expo Go app for physical device"
echo ""
npm start
EOF

chmod +x run-mobile.sh

# Instructions for the user
echo ""
echo "=========================================="
echo -e "${GREEN}✨ Development environment is ready!${NC}"
echo "=========================================="
echo ""
echo "📱 To start the mobile app, run:"
echo "   cd mobile && ./run-mobile.sh"
echo ""
echo "🔧 Quick commands:"
echo "   - View backend logs: cd infrastructure/docker && docker-compose logs -f backend"
echo "   - Stop all services: cd infrastructure/docker && docker-compose down"
echo "   - View Knowledge Graph: open http://localhost:8000"
echo "   - View API docs: open http://localhost:8001/docs"
echo ""
echo "⚠️  Important notes:"
echo "   - Make sure to add your Google Cloud API keys to the .env file"
echo "   - The mobile app will connect to the backend at localhost:8001"
echo "   - For physical devices, update the API URL in mobile/src/config/api.ts"
echo ""
echo "Happy coding! 🚗✨"