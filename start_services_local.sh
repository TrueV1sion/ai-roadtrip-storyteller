#!/bin/bash
# AI Road Trip Storyteller - Local Service Startup Script (No Docker)

echo "🚀 Starting services locally (without Docker)..."

# Create necessary directories
mkdir -p logs
mkdir -p data

# Check Python version
echo "Checking Python version..."
python3 --version

# Install minimal dependencies if needed
echo "Checking dependencies..."
pip3 list | grep -E "fastapi|uvicorn|redis|psycopg2" || echo "⚠️  Some dependencies may be missing"

# Start Redis (if installed locally)
echo "Checking for local Redis..."
if command -v redis-server &> /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379 --dir ./data
else
    echo "⚠️  Redis not installed locally - caching will be disabled"
fi

# Start PostgreSQL (if installed locally)
echo "Checking for local PostgreSQL..."
if command -v pg_ctl &> /dev/null; then
    echo "PostgreSQL available"
else
    echo "⚠️  PostgreSQL not installed locally - using SQLite fallback"
fi

# Start Knowledge Graph
echo "Starting Knowledge Graph service..."
cd knowledge_graph
python3 blazing_server.py > ../logs/knowledge_graph.log 2>&1 &
KG_PID=$!
cd ..
echo "Knowledge Graph started with PID: $KG_PID"

# Wait for Knowledge Graph to be ready
echo "Waiting for Knowledge Graph to initialize..."
sleep 5

# Check Knowledge Graph health
curl -s http://localhost:8000/api/health && echo "✅ Knowledge Graph healthy" || echo "❌ Knowledge Graph not responding"

# Start Backend API (if not conflicting with KG port)
echo "Checking backend configuration..."
if [ -f "backend/app/main.py" ]; then
    echo "⚠️  Backend would conflict with Knowledge Graph on port 8000"
    echo "   Modify backend to use port 8001 if needed"
fi

# Create a simple health check script
cat > check_services.sh << 'EOF'
#!/bin/bash
echo "🏥 Service Health Check"
echo "======================"

# Knowledge Graph
echo -n "Knowledge Graph: "
curl -s http://localhost:8000/api/health > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"

# Redis (if available)
echo -n "Redis: "
redis-cli ping > /dev/null 2>&1 && echo "✅ Running" || echo "⚠️  Not available"

# Show running Python processes
echo ""
echo "Python processes:"
ps aux | grep python3 | grep -v grep
EOF

chmod +x check_services.sh

echo ""
echo "✅ Service startup complete!"
echo ""
echo "To check service status, run: ./check_services.sh"
echo ""
echo "Knowledge Graph Dashboard: http://localhost:8000"
echo "Knowledge Graph API Health: http://localhost:8000/api/health"
echo ""
echo "Logs are available in the 'logs' directory"