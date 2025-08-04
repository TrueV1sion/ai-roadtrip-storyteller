#!/bin/bash
# Setup script for AI Road Trip Knowledge Graph

set -euo pipefail

echo "🚀 AI Road Trip Knowledge Graph Setup"
echo "===================================="

# Check Python version
if ! python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null; then
    echo "❌ Python 3.9+ required"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Setup Neo4j
echo "🗄️ Setting up Neo4j..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker required for Neo4j. Please install Docker."
    exit 1
fi

# Start Neo4j in Docker
docker run -d \
    --name neo4j-knowledge-graph \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    -v $(pwd)/neo4j/data:/data \
    neo4j:5.14.0 || echo "Neo4j already running"

# Create .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Knowledge Graph Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CODEBASE_ROOT=..
OPENAI_API_KEY=your-api-key-here

# Server
HOST=0.0.0.0
PORT=8000
EOF
fi

# Create directories
mkdir -p chroma_db
mkdir -p logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the Knowledge Graph server:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run server: python -m knowledge_graph.api.server"
echo "  3. Open browser: http://localhost:8000"
echo ""
echo "First time setup:"
echo "  - Click 'Analyze Codebase' to build the knowledge graph"
echo "  - This will take a few minutes for large codebases"