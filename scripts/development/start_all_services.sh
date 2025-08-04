#!/bin/bash
# AI Road Trip Storyteller - Service Startup Script

echo "🚀 Starting all services..."

# Start Docker Compose
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 10

# Start Knowledge Graph
echo "Starting Knowledge Graph..."
cd knowledge_graph && python3 blazing_server.py &

# Start Backend (if not in Docker)
# echo "Starting Backend API..."
# uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 &

# Health check
sleep 5
echo "Performing health check..."
curl -s http://localhost:8000/health && echo "✅ Backend healthy"
curl -s http://localhost:8000/api/health && echo "✅ Knowledge Graph healthy"

echo "✅ All services started!"
