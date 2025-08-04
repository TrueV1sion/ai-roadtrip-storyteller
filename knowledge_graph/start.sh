#!/bin/bash
# Quick start script for Knowledge Graph

echo "🚀 AI Road Trip Knowledge Graph"
echo "=============================="

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install --user fastapi uvicorn neo4j chromadb sentence-transformers \
        websockets plotly networkx pygments gitpython \
        scikit-learn numpy || {
        echo "❌ Failed to install dependencies"
        echo "Try: pip install --user -r requirements.txt"
        exit 1
    }
fi

# Check if Neo4j is running
if ! nc -z localhost 7687 2>/dev/null; then
    echo "🗄️ Starting Neo4j..."
    docker run -d \
        --name neo4j-knowledge-graph \
        -p 7474:7474 -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/password \
        -e NEO4J_PLUGINS='["apoc"]' \
        neo4j:5.14.0 2>/dev/null || echo "Neo4j container exists"
    
    echo "Waiting for Neo4j to start..."
    sleep 10
fi

# Create required directories
mkdir -p chroma_db logs

# Start the server
echo ""
echo "🌐 Starting server on http://localhost:8000"
echo "📊 Open your browser to view the Knowledge Graph"
echo ""

python3 run_server.py