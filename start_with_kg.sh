#!/bin/bash
# Always start with Knowledge Graph

echo "🚀 Starting AI Road Trip development environment..."

# Start Knowledge Graph first
echo "📊 Starting Knowledge Graph server..."
cd knowledge_graph
python3 blazing_server.py > kg.log 2>&1 &
KG_PID=$!

# Wait for it to be ready
sleep 3
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Knowledge Graph running at http://localhost:8000"
    
    # Trigger initial analysis
    curl -X POST http://localhost:8000/api/analyze/codebase
    echo "📊 Codebase analysis initiated"
else
    echo "❌ Knowledge Graph failed to start"
    exit 1
fi

# Now start regular development
cd ..
echo "Ready for development with Knowledge Graph integration!"
echo "Dashboard: http://localhost:8000"

# Keep running
wait $KG_PID
