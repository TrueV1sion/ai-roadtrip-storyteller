#!/usr/bin/env python3
"""
Full Knowledge Graph Server with available dependencies
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import what we have available
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
from pathlib import Path

# Try to import additional modules
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("NetworkX not available - impact analysis limited")

try:
    from analyzers.code_analyzer import CodebaseAnalyzer, PythonCodeAnalyzer
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    print("Code analyzer not available - using mock data")

# Initialize FastAPI
app = FastAPI(title="AI Road Trip Knowledge Graph", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
active_connections: List[WebSocket] = []

# Global graph data
graph_data = None
impact_graph = None

# Pydantic models
class SearchQuery(BaseModel):
    query: str
    limit: int = 10

class ImpactQuery(BaseModel):
    node_id: str
    max_depth: int = 5

class AgentNote(BaseModel):
    node_id: str
    agent_id: str
    note: str
    note_type: str = "observation"

# In-memory storage
agent_notes_db = {}

# Initialize graph with real codebase analysis
def analyze_real_codebase():
    """Analyze the actual codebase"""
    global graph_data, impact_graph
    
    if not HAS_ANALYZER:
        # Use mock data if analyzer not available
        graph_data = {
            "nodes": [
                {"id": "main", "name": "main.py", "type": "file", "path": "backend/app/main.py"},
                {"id": "config", "name": "config.py", "type": "file", "path": "backend/app/core/config.py"},
                {"id": "orchestration", "name": "master_orchestration_agent.py", "type": "file", "path": "backend/app/services/master_orchestration_agent.py"},
                {"id": "unified_ai", "name": "unified_ai_client.py", "type": "file", "path": "backend/app/core/unified_ai_client.py"},
                {"id": "story_gen", "name": "story_generation_agent.py", "type": "file", "path": "backend/app/services/story_generation_agent.py"},
                {"id": "booking", "name": "booking_agent.py", "type": "file", "path": "backend/app/services/booking_agent.py"},
                {"id": "navigation", "name": "navigation_agent.py", "type": "file", "path": "backend/app/services/navigation_agent.py"},
            ],
            "links": [
                {"source": "main", "target": "config", "type": "imports"},
                {"source": "orchestration", "target": "unified_ai", "type": "uses"},
                {"source": "orchestration", "target": "story_gen", "type": "orchestrates"},
                {"source": "orchestration", "target": "booking", "type": "orchestrates"},
                {"source": "orchestration", "target": "navigation", "type": "orchestrates"},
            ]
        }
        return
    
    # Analyze real codebase
    analyzer = CodebaseAnalyzer("..")
    entities, relationships = analyzer.analyze_codebase()
    
    # Convert to graph format
    nodes = []
    for entity in entities[:100]:  # Limit for performance
        nodes.append({
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "path": entity.path,
            "lines": entity.line_end - entity.line_start
        })
    
    links = []
    for source, target, rel_type in relationships[:200]:  # Limit for performance
        links.append({
            "source": source,
            "target": target,
            "type": rel_type
        })
    
    graph_data = {"nodes": nodes, "links": links}
    
    # Build NetworkX graph if available
    if HAS_NETWORKX:
        impact_graph = nx.DiGraph()
        for node in nodes:
            impact_graph.add_node(node["id"], **node)
        for link in links:
            impact_graph.add_edge(link["source"], link["target"], type=link["type"])

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("🔍 Analyzing codebase...")
    analyze_real_codebase()
    print(f"📊 Found {len(graph_data['nodes'])} nodes and {len(graph_data['links'])} relationships")

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI"""
    ui_path = Path(__file__).parent / "ui" / "index.html"
    if ui_path.exists():
        return ui_path.read_text()
    return "<h1>UI not found</h1>"

@app.get("/app.js")
async def serve_js():
    """Serve the JavaScript file"""
    js_path = Path(__file__).parent / "ui" / "app.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return HTTPException(status_code=404)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "features": {
            "networkx": HAS_NETWORKX,
            "analyzer": HAS_ANALYZER,
            "graph_nodes": len(graph_data["nodes"]) if graph_data else 0
        }
    }

@app.post("/api/analyze/codebase")
async def analyze_codebase():
    """Re-analyze the codebase"""
    analyze_real_codebase()
    # Notify connected clients
    for connection in active_connections:
        await connection.send_json({
            "type": "analysis_complete",
            "stats": {
                "entities": len(graph_data["nodes"]),
                "relationships": len(graph_data["links"])
            }
        })
    return {"status": "completed", "nodes": len(graph_data["nodes"])}

@app.post("/api/search")
async def semantic_search(query: SearchQuery):
    """Search through the graph"""
    results = []
    search_term = query.query.lower()
    
    for node in graph_data["nodes"]:
        score = 0
        if search_term in node["name"].lower():
            score += 0.8
        if search_term in node["path"].lower():
            score += 0.5
        if node["type"] == "class" and "class" in search_term:
            score += 0.3
        if node["type"] == "function" and "function" in search_term:
            score += 0.3
            
        if score > 0:
            results.append({**node, "relevance_score": score})
    
    # Sort by score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"results": results[:query.limit]}

@app.post("/api/impact/analyze")
async def analyze_impact(query: ImpactQuery):
    """Analyze impact of changes"""
    if not impact_graph or query.node_id not in impact_graph:
        # Simple mock impact
        return {
            "summary": {
                "source_node": query.node_id,
                "total_impacted_nodes": 0,
                "impact_distribution": {"high": 0, "medium": 0, "low": 0}
            },
            "impact_nodes": [],
            "file_impacts": {}
        }
    
    # Use NetworkX to find impacted nodes
    impacted = []
    try:
        descendants = nx.descendants(impact_graph, query.node_id)
        for node_id in list(descendants)[:20]:  # Limit
            node_data = impact_graph.nodes[node_id]
            distance = nx.shortest_path_length(impact_graph, query.node_id, node_id)
            impact_score = 1.0 / (distance + 1)
            
            impacted.append({
                "id": node_id,
                "name": node_data.get("name", node_id),
                "path": node_data.get("path", ""),
                "impact_score": impact_score,
                "depth": distance
            })
    except Exception as e:
        pass
    
    # Sort by impact score
    impacted.sort(key=lambda x: x["impact_score"], reverse=True)
    
    return {
        "summary": {
            "source_node": query.node_id,
            "total_impacted_nodes": len(impacted),
            "impact_distribution": {
                "high": len([n for n in impacted if n["impact_score"] > 0.7]),
                "medium": len([n for n in impacted if 0.3 < n["impact_score"] <= 0.7]),
                "low": len([n for n in impacted if n["impact_score"] <= 0.3])
            }
        },
        "impact_nodes": impacted,
        "file_impacts": {n["path"]: n["impact_score"] for n in impacted if n.get("path")}
    }

@app.get("/api/graph/structure")
async def get_graph_structure():
    """Get the graph structure"""
    return graph_data

@app.post("/api/agent/note")
async def add_agent_note(note: AgentNote):
    """Add an agent note"""
    if note.node_id not in agent_notes_db:
        agent_notes_db[note.node_id] = []
    
    agent_notes_db[note.node_id].append({
        "agent_id": note.agent_id,
        "content": note.note,
        "type": note.note_type,
        "created_at": "2024-01-07T10:00:00Z"
    })
    
    return {"status": "added", "note_id": len(agent_notes_db[note.node_id])}

@app.get("/api/agent/notes/{node_id}")
async def get_agent_notes(node_id: str):
    """Get agent notes for a node"""
    return {"notes": agent_notes_db.get(node_id, [])}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting AI Road Trip Knowledge Graph Server")
    print("📊 Open http://localhost:8000 in your browser")
    print("🔍 Analyzing your codebase...")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)