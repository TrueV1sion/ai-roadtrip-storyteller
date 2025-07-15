#!/usr/bin/env python3
"""
BLAZING Knowledge Graph Server - Fast startup, real analysis
"""
import os
import ast
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# Global state
CODEBASE_PATH = Path("..")  # Parent directory (roadtrip)
graph_data = {"nodes": [], "links": []}
file_tree = {}
code_index = {}
impact_map = defaultdict(set)
websocket_connections: List[WebSocket] = []
analysis_in_progress = False

class SearchQuery(BaseModel):
    query: str
    limit: int = 20

class ImpactQuery(BaseModel):
    node_id: str
    max_depth: int = 5

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting BLAZING Knowledge Graph Server")
    yield
    # Shutdown
    print("👋 Shutting down")

# Initialize FastAPI with lifespan
app = FastAPI(title="AI Road Trip Knowledge Graph - BLAZING", version="3.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def scan_directory(path: Path, ignore_patterns: Set[str] = None) -> Dict:
    """Recursively scan directory and build file tree"""
    if ignore_patterns is None:
        ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.expo', 'chroma_db'}
    
    tree = {"name": path.name, "type": "directory", "children": []}
    
    try:
        for item in sorted(path.iterdir()):
            if item.name in ignore_patterns:
                continue
                
            if item.is_dir():
                # Only add specific directories we care about
                if item.name in ['backend', 'mobile', 'scripts', 'tests', 'config']:
                    subtree = scan_directory(item, ignore_patterns)
                    if subtree["children"]:
                        tree["children"].append(subtree)
            elif item.is_file() and item.suffix in {'.py', '.js', '.ts', '.tsx', '.jsx'}:
                tree["children"].append({
                    "name": item.name,
                    "type": "file",
                    "path": str(item.relative_to(CODEBASE_PATH)),
                    "ext": item.suffix
                })
    except PermissionError:
        pass
    
    return tree

def analyze_python_file(filepath: Path) -> Tuple[List[Dict], List[Tuple[str, str, str]]]:
    """Analyze a Python file and extract entities and relationships"""
    nodes = []
    links = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        file_id = str(filepath.relative_to(CODEBASE_PATH))
        nodes.append({
            "id": file_id,
            "name": filepath.name,
            "type": "file",
            "path": file_id,
            "lines": len(content.splitlines())
        })
        
        # Extract classes and functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_id = f"{file_id}:{node.name}"
                nodes.append({
                    "id": class_id,
                    "name": node.name,
                    "type": "class",
                    "path": file_id,
                    "line": node.lineno
                })
                links.append((file_id, class_id, "contains"))
                
            elif isinstance(node, ast.FunctionDef):
                func_id = f"{file_id}:{node.name}"
                nodes.append({
                    "id": func_id,
                    "name": node.name,
                    "type": "function",
                    "path": file_id,
                    "line": node.lineno
                })
                links.append((file_id, func_id, "contains"))
        
        # Store content for search
        code_index[file_id] = {
            "content": content,
            "path": file_id,
            "type": "python"
        }
        
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
    
    return nodes, links

async def analyze_codebase_async():
    """Analyze the codebase asynchronously"""
    global graph_data, file_tree, analysis_in_progress
    
    if analysis_in_progress:
        return {"status": "already_running"}
    
    analysis_in_progress = True
    
    try:
        print(f"🔍 Analyzing codebase at {CODEBASE_PATH}")
        
        all_nodes = []
        all_links = []
        node_ids = set()
        
        # Quick scan of important directories only
        important_dirs = ['backend', 'mobile', 'scripts', 'tests']
        file_count = 0
        
        for dir_name in important_dirs:
            dir_path = CODEBASE_PATH / dir_name
            if not dir_path.exists():
                continue
                
            # Analyze Python files
            for py_file in dir_path.rglob("*.py"):
                if any(part in py_file.parts for part in ['.git', '__pycache__', 'venv']):
                    continue
                nodes, links = analyze_python_file(py_file)
                all_nodes.extend(nodes)
                all_links.extend(links)
                node_ids.update(n["id"] for n in nodes)
                file_count += 1
                
                # Limit for performance
                if file_count > 200:
                    break
        
        # Filter links to only include existing nodes
        valid_links = []
        for source, target, rel_type in all_links:
            if source in node_ids and target in node_ids:
                valid_links.append({
                    "source": source,
                    "target": target,
                    "type": rel_type
                })
        
        graph_data = {
            "nodes": all_nodes,
            "links": valid_links
        }
        
        # Build file tree
        file_tree = scan_directory(CODEBASE_PATH)
        
        print(f"📊 Analysis complete: {len(all_nodes)} nodes, {len(valid_links)} links")
        
        # Notify WebSocket clients
        for ws in websocket_connections:
            try:
                await ws.send_json({
                    "type": "analysis_complete",
                    "stats": {
                        "nodes": len(all_nodes),
                        "links": len(valid_links)
                    }
                })
            except:
                pass
                
    finally:
        analysis_in_progress = False

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI"""
    ui_path = Path(__file__).parent / "ui" / "index.html"
    if ui_path.exists():
        return ui_path.read_text()
    return "<h1>UI not found</h1>"

@app.get("/app.js")
async def serve_js():
    """Serve JavaScript"""
    js_path = Path(__file__).parent / "ui" / "app.js"
    return FileResponse(js_path, media_type="application/javascript")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "stats": {
            "nodes": len(graph_data["nodes"]),
            "links": len(graph_data["links"]),
            "indexed_files": len(code_index)
        }
    }

@app.post("/api/analyze/codebase")
async def analyze_endpoint(background_tasks: BackgroundTasks):
    """Trigger codebase analysis"""
    background_tasks.add_task(analyze_codebase_async)
    return {"status": "analysis_started"}

@app.post("/api/search")
async def semantic_search(query: SearchQuery):
    """Search through code content"""
    results = []
    search_term = query.query.lower()
    
    # Search in code content
    for file_id, file_data in code_index.items():
        score = 0
        content_lower = file_data["content"].lower()
        
        # Count occurrences
        occurrences = content_lower.count(search_term)
        if occurrences > 0:
            score = min(1.0, occurrences * 0.1)
            
            # Find matching lines
            lines = file_data["content"].splitlines()
            matching_lines = []
            for i, line in enumerate(lines):
                if search_term in line.lower():
                    matching_lines.append({
                        "line": i + 1,
                        "text": line.strip()[:100]
                    })
                    if len(matching_lines) >= 3:
                        break
            
            results.append({
                "id": file_id,
                "name": Path(file_id).name,
                "path": file_id,
                "type": "file",
                "relevance_score": score,
                "occurrences": occurrences,
                "matching_lines": matching_lines
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"results": results[:query.limit]}

@app.post("/api/impact/analyze")
async def analyze_impact(query: ImpactQuery):
    """Simple impact analysis"""
    # Find all nodes that this node links to
    impacted = []
    
    for link in graph_data["links"]:
        if link["source"] == query.node_id:
            # Find target node
            target_node = next((n for n in graph_data["nodes"] if n["id"] == link["target"]), None)
            if target_node:
                impacted.append({
                    "id": target_node["id"],
                    "name": target_node["name"],
                    "type": target_node["type"],
                    "path": target_node.get("path", ""),
                    "impact_score": 0.8,
                    "depth": 1
                })
    
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
        "impact_nodes": impacted
    }

@app.get("/api/graph/structure")
async def get_graph_structure():
    """Get the graph structure"""
    return graph_data

@app.get("/api/file-tree")
async def get_file_tree():
    """Get the file tree structure"""
    return file_tree

@app.get("/api/file/{file_path:path}")
async def get_file_content(file_path: str):
    """Get file content"""
    if file_path in code_index:
        return {
            "content": code_index[file_path]["content"],
            "type": code_index[file_path]["type"]
        }
    return {"error": "File not found"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully"
        })
        
        while True:
            data = await websocket.receive_text()
            # Echo back
            await websocket.send_text(f"Echo: {data}")
                
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

if __name__ == "__main__":
    print("🔥 Starting BLAZING Knowledge Graph Server")
    print("📊 Open http://localhost:8000 in your browser")
    print("⚡ Click 'Analyze Codebase' to start analysis")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)