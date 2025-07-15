#!/usr/bin/env python3
"""
Direct runner for the Knowledge Graph server
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment variables if .env doesn't exist
if not os.path.exists('.env'):
    with open('.env', 'w') as f:
        f.write("""# Knowledge Graph Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CODEBASE_ROOT=..
OPENAI_API_KEY=your-api-key-here

# Server
HOST=0.0.0.0
PORT=8000
""")

# Create required directories
os.makedirs('chroma_db', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Import and run the server
try:
    import uvicorn
    from api.server import app
    
    print("🚀 Starting Knowledge Graph Server...")
    print("📊 Open http://localhost:8000 in your browser")
    print("💡 Click 'Analyze Codebase' to build the knowledge graph")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("pip install fastapi uvicorn neo4j chromadb sentence-transformers")
    sys.exit(1)