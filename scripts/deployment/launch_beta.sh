#!/bin/bash

# AI Road Trip Storyteller - Beta Launch Script
# This script starts all services needed for beta testing

echo "🚀 AI Road Trip Storyteller - Beta Launch Sequence"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

command_exists python3
print_status $? "Python 3 installed"

command_exists docker
print_status $? "Docker installed"

command_exists npm
print_status $? "Node.js/npm installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please run: python scripts/setup_apis.py"
    exit 1
fi
print_status 0 ".env configuration found"

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"

# Start Redis (if using Docker)
echo "Starting Redis cache..."
docker run -d --name roadtrip-redis -p 6379:6379 redis:alpine 2>/dev/null || echo "Redis already running"
print_status 0 "Redis cache started"

# Start PostgreSQL (if using Docker)
echo "Starting PostgreSQL database..."
docker run -d --name roadtrip-postgres \
    -e POSTGRES_USER=roadtrip \
    -e POSTGRES_PASSWORD=roadtrip123 \
    -e POSTGRES_DB=roadtrip \
    -p 5432:5432 \
    postgres:13 2>/dev/null || echo "PostgreSQL already running"
print_status 0 "PostgreSQL database started"

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 5

# Run database migrations
echo -e "\n${YELLOW}Setting up database...${NC}"
cd backend
alembic upgrade head
print_status $? "Database migrations completed"
cd ..

# Start backend server
echo -e "\n${YELLOW}Starting backend server...${NC}"
cd backend
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "Backend PID: $BACKEND_PID"
sleep 5

# Check if backend is running
curl -s http://localhost:8000/health > /dev/null
print_status $? "Backend server started (PID: $BACKEND_PID)"

# Test API connections
echo -e "\n${YELLOW}Testing API connections...${NC}"
python scripts/test_api_dashboard.py --quick
print_status $? "API connections verified"

# Start mobile app (optional)
echo -e "\n${YELLOW}Mobile app setup...${NC}"
echo "To start the mobile app, run in a new terminal:"
echo "  cd mobile && npm start"

# Display status dashboard
echo -e "\n${GREEN}🎉 Beta Launch Successful!${NC}"
echo "=================================================="
echo ""
echo "📊 Service Status:"
echo "  • Backend API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo "  • Redis: localhost:6379"
echo "  • PostgreSQL: localhost:5432"
echo ""
echo "🔍 Monitoring:"
echo "  • Backend logs: tail -f backend.log"
echo "  • API Dashboard: python scripts/test_api_dashboard.py"
echo ""
echo "🎯 Next Steps:"
echo "  1. Open http://localhost:8000/docs for API testing"
echo "  2. Create your first event journey"
echo "  3. Test voice personalities"
echo "  4. Make a test booking"
echo ""
echo "💡 Quick Tests:"
echo "  • Test Recreation.gov: curl http://localhost:8000/api/bookings/campgrounds/search?query=yellowstone"
echo "  • Test Events: curl http://localhost:8000/api/event-journeys/search-events?query=concert"
echo "  • Test Personalities: curl http://localhost:8000/api/voice/personalities"
echo ""
echo "🛑 To stop all services:"
echo "  kill $BACKEND_PID"
echo "  docker stop roadtrip-redis roadtrip-postgres"
echo ""
echo "Ready for beta testing! 🚀"

# Save PID for shutdown script
echo $BACKEND_PID > .backend.pid

# Create shutdown script
cat > stop_beta.sh << 'EOF'
#!/bin/bash
echo "Stopping AI Road Trip Storyteller beta services..."
if [ -f .backend.pid ]; then
    kill $(cat .backend.pid) 2>/dev/null
    rm .backend.pid
fi
docker stop roadtrip-redis roadtrip-postgres 2>/dev/null
echo "All services stopped."
EOF
chmod +x stop_beta.sh

# Keep script running for monitoring
echo -e "\n${YELLOW}Press Ctrl+C to exit (services will continue running)${NC}"
tail -f backend.log