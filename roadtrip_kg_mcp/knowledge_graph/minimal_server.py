#!/usr/bin/env python3
"""
Minimal Knowledge Graph Server - Works without all dependencies
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(title="AI Road Trip Knowledge Graph", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for visualization
MOCK_GRAPH_DATA = {
    "nodes": [
        {"id": "main.py", "name": "main.py", "type": "file", "path": "backend/app/main.py"},
        {"id": "config.py", "name": "config.py", "type": "file", "path": "backend/app/core/config.py"},
        {"id": "unified_ai", "name": "unified_ai_client.py", "type": "file", "path": "backend/app/core/unified_ai_client.py"},
        {"id": "orchestration", "name": "master_orchestration_agent.py", "type": "file", "path": "backend/app/services/master_orchestration_agent.py"},
        {"id": "story_gen", "name": "story_generation_agent.py", "type": "file", "path": "backend/app/services/story_generation_agent.py"},
        {"id": "booking", "name": "booking_agent.py", "type": "file", "path": "backend/app/services/booking_agent.py"},
        {"id": "navigation", "name": "navigation_agent.py", "type": "file", "path": "backend/app/services/navigation_agent.py"},
        {"id": "story_route", "name": "story.py", "type": "file", "path": "backend/app/routes/story.py"},
        {"id": "auth_route", "name": "auth.py", "type": "file", "path": "backend/app/routes/auth.py"},
        {"id": "user_model", "name": "User", "type": "class", "path": "backend/app/models/user.py"},
        {"id": "story_model", "name": "Story", "type": "class", "path": "backend/app/models/story.py"},
    ],
    "links": [
        {"source": "main.py", "target": "config.py", "type": "imports"},
        {"source": "main.py", "target": "story_route", "type": "imports"},
        {"source": "main.py", "target": "auth_route", "type": "imports"},
        {"source": "orchestration", "target": "unified_ai", "type": "uses"},
        {"source": "orchestration", "target": "story_gen", "type": "orchestrates"},
        {"source": "orchestration", "target": "booking", "type": "orchestrates"},
        {"source": "orchestration", "target": "navigation", "type": "orchestrates"},
        {"source": "story_route", "target": "orchestration", "type": "calls"},
        {"source": "story_gen", "target": "unified_ai", "type": "uses"},
        {"source": "auth_route", "target": "user_model", "type": "uses"},
        {"source": "story_route", "target": "story_model", "type": "uses"},
    ]
}

class SearchQuery(BaseModel):
    query: str
    limit: int = 10

class ImpactQuery(BaseModel):
    node_id: str
    max_depth: int = 5

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the UI"""
    ui_path = Path(__file__).parent / "ui" / "index.html"
    if ui_path.exists():
        return ui_path.read_text()
    return "<h1>Knowledge Graph UI not found. Please check the ui/ directory.</h1>"

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "knowledge-graph"}

@app.post("/api/analyze/codebase")
async def analyze_codebase():
    """Mock codebase analysis"""
    return {
        "status": "analysis_started",
        "message": "Codebase analysis would run here with full dependencies"
    }

@app.post("/api/search")
async def semantic_search(query: SearchQuery):
    """Mock semantic search"""
    # Simple text matching for demo
    results = []
    for node in MOCK_GRAPH_DATA["nodes"]:
        if query.query.lower() in node["name"].lower() or query.query.lower() in node["path"].lower():
            results.append({
                **node,
                "relevance_score": 0.8  # Mock score
            })
    return {"results": results[:query.limit]}

@app.post("/api/impact/analyze")
async def analyze_impact(query: ImpactQuery):
    """Mock impact analysis"""
    # Find connected nodes
    impacted = []
    for link in MOCK_GRAPH_DATA["links"]:
        if link["source"] == query.node_id:
            target_node = next((n for n in MOCK_GRAPH_DATA["nodes"] if n["id"] == link["target"]), None)
            if target_node:
                impacted.append({
                    "id": target_node["id"],
                    "name": target_node["name"],
                    "path": target_node["path"],
                    "impact_score": 0.9,
                    "depth": 1
                })
    
    return {
        "summary": {
            "source_node": query.node_id,
            "total_impacted_nodes": len(impacted),
            "total_impacted_files": len(set(n["path"] for n in impacted)),
            "impact_distribution": {
                "high": len([n for n in impacted if n["impact_score"] > 0.7]),
                "medium": len([n for n in impacted if 0.3 < n["impact_score"] <= 0.7]),
                "low": len([n for n in impacted if n["impact_score"] <= 0.3])
            },
            "critical_paths": []
        },
        "impact_nodes": impacted,
        "file_impacts": {n["path"]: n["impact_score"] for n in impacted}
    }

@app.get("/api/graph/structure")
async def get_graph_structure():
    """Return mock graph structure"""
    return MOCK_GRAPH_DATA

@app.get("/api/agent/notes/{node_id}")
async def get_agent_notes(node_id: str):
    """Mock agent notes"""
    mock_notes = {
        "orchestration": [
            {
                "agent_id": "ArchitectAgent",
                "content": "Central orchestration point - routes to 5 specialized sub-agents",
                "created_at": "2024-01-07T10:00:00Z"
            },
            {
                "agent_id": "SecurityAgent", 
                "content": "Ensure all sub-agent calls are properly authenticated",
                "created_at": "2024-01-07T10:05:00Z"
            }
        ],
        "unified_ai": [
            {
                "agent_id": "PerformanceAgent",
                "content": "Consider caching AI responses to reduce Vertex AI costs",
                "created_at": "2024-01-07T10:10:00Z"
            }
        ]
    }
    
    return {"notes": mock_notes.get(node_id, [])}

# Serve static files
@app.get("/app.js")
async def serve_app_js():
    """Serve the app.js file"""
    js_path = Path(__file__).parent / "ui" / "app.js"
    if js_path.exists():
        return HTMLResponse(content=js_path.read_text(), media_type="application/javascript")
    return HTTPException(status_code=404, detail="app.js not found")

if __name__ == "__main__":
    import uvicorn
    
    # Create directories
    os.makedirs("ui", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("🚀 Starting Knowledge Graph Server...")
    print("📊 Open http://localhost:8000 in your browser")
    print("💡 This is running with mock data. Install full dependencies for real analysis.")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)