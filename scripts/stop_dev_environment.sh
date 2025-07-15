#!/bin/bash

# AI Road Trip Storyteller - Stop Development Environment Script

echo "🛑 Stopping AI Road Trip Storyteller development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Read PIDs from file
if [ -f ".dev_pids" ]; then
    source .dev_pids
    
    # Stop Backend API
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Stopping Backend API (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo -e "${GREEN}✓${NC} Backend API stopped"
    fi
    
    # Stop Mobile app
    if [ ! -z "$MOBILE_PID" ] && kill -0 $MOBILE_PID 2>/dev/null; then
        echo "Stopping Mobile app (PID: $MOBILE_PID)..."
        kill $MOBILE_PID
        echo -e "${GREEN}✓${NC} Mobile app stopped"
    fi
    
    # Stop Knowledge Graph
    if [ ! -z "$KG_PID" ] && kill -0 $KG_PID 2>/dev/null; then
        echo "Stopping Knowledge Graph (PID: $KG_PID)..."
        kill $KG_PID
        echo -e "${GREEN}✓${NC} Knowledge Graph stopped"
    fi
    
    rm .dev_pids
fi

# Stop Docker services
echo "Stopping Docker services..."
docker-compose down

echo -e "${GREEN}✓${NC} All services stopped successfully!"