#!/usr/bin/env python3
"""
ULTRA Knowledge Graph Server - Real functionality, no bullshit
"""
import os
import ast
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import hashlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI
app = FastAPI(title="AI Road Trip Knowledge Graph - ULTRA", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
CODEBASE_PATH = Path("..")  # Parent directory (roadtrip)
graph_data = {"nodes": [], "links": []}
file_tree = {}
code_index = {}  # For semantic search
impact_map = defaultdict(set)  # node -> affected nodes
websocket_connections: List[WebSocket] = []

class SearchQuery(BaseModel):
    query: str
    limit: int = 20

class ImpactQuery(BaseModel):
    node_id: str
    max_depth: int = 5

def scan_directory(path: Path, ignore_patterns: Set[str] = None) -> Dict:
    """Recursively scan directory and build file tree"""
    if ignore_patterns is None:
        ignore_patterns = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.expo'}
    
    tree = {"name": path.name, "type": "directory", "children": []}
    
    try:
        for item in sorted(path.iterdir()):
            if item.name in ignore_patterns:
                continue
                
            if item.is_dir():
                subtree = scan_directory(item, ignore_patterns)
                if subtree["children"]:  # Only add non-empty directories
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
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    links.append((file_id, f"module:{alias.name}", "imports"))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    links.append((file_id, f"module:{node.module}", "imports"))
            elif isinstance(node, ast.ClassDef):
                class_id = f"{file_id}:{node.name}"
                nodes.append({
                    "id": class_id,
                    "name": node.name,
                    "type": "class",
                    "path": file_id,
                    "line": node.lineno
                })
                links.append((file_id, class_id, "contains"))
                
                # Check inheritance
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        links.append((class_id, f"class:{base.id}", "inherits"))
                        
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

def analyze_javascript_file(filepath: Path) -> Tuple[List[Dict], List[Tuple[str, str, str]]]:
    """Basic JavaScript/TypeScript analysis"""
    nodes = []
    links = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
        file_id = str(filepath.relative_to(CODEBASE_PATH))
        
        nodes.append({
            "id": file_id,
            "name": filepath.name,
            "type": "file",
            "path": file_id,
            "lines": len(content.splitlines())
        })
        
        # Basic import detection
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if 'import' in line and ('from' in line or '{' in line):
                # Extract module name (basic)
                if 'from' in line:
                    parts = line.split('from')
                    if len(parts) > 1:
                        module = parts[1].strip().strip('"\'`;')
                        links.append((file_id, f"module:{module}", "imports"))
                        
            # Basic class detection
            if 'class ' in line:
                parts = line.split('class ')
                if len(parts) > 1:
                    class_name = parts[1].split()[0].strip('{')
                    class_id = f"{file_id}:{class_name}"
                    nodes.append({
                        "id": class_id,
                        "name": class_name,
                        "type": "class",
                        "path": file_id,
                        "line": i + 1
                    })
                    links.append((file_id, class_id, "contains"))
                    
            # Basic function detection
            if 'function ' in line or '=>' in line:
                if 'function ' in line:
                    parts = line.split('function ')
                    if len(parts) > 1:
                        func_name = parts[1].split('(')[0].strip()
                        if func_name:
                            func_id = f"{file_id}:{func_name}"
                            nodes.append({
                                "id": func_id,
                                "name": func_name,
                                "type": "function",
                                "path": file_id,
                                "line": i + 1
                            })
                            links.append((file_id, func_id, "contains"))
        
        # Store content for search
        code_index[file_id] = {
            "content": content,
            "path": file_id,
            "type": "javascript"
        }
        
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
    
    return nodes, links

def build_impact_map():
    """Build impact analysis map from relationships"""
    global impact_map
    impact_map.clear()
    
    # Build adjacency list
    for link in graph_data["links"]:
        impact_map[link["source"]].add(link["target"])
        # Reverse impact for "imports" and "uses"
        if link["type"] in ["imports", "uses"]:
            impact_map[link["target"]].add(link["source"])

def calculate_impact(node_id: str, max_depth: int = 5) -> Dict[str, Any]:
    """Calculate impact of changes to a node"""
    visited = set()
    impact_nodes = []
    
    def traverse(current_id: str, depth: int):
        if depth > max_depth or current_id in visited:
            return
        visited.add(current_id)
        
        for affected_id in impact_map.get(current_id, []):
            if affected_id not in visited:
                # Find node data
                node = next((n for n in graph_data["nodes"] if n["id"] == affected_id), None)
                if node:
                    impact_score = 1.0 / (depth + 1)
                    impact_nodes.append({
                        "id": affected_id,
                        "name": node["name"],
                        "type": node["type"],
                        "path": node.get("path", ""),
                        "impact_score": impact_score,
                        "depth": depth
                    })
                traverse(affected_id, depth + 1)
    
    traverse(node_id, 0)
    
    # Sort by impact score
    impact_nodes.sort(key=lambda x: x["impact_score"], reverse=True)
    
    # Calculate distribution
    high = len([n for n in impact_nodes if n["impact_score"] > 0.7])
    medium = len([n for n in impact_nodes if 0.3 < n["impact_score"] <= 0.7])
    low = len([n for n in impact_nodes if n["impact_score"] <= 0.3])
    
    return {
        "summary": {
            "source_node": node_id,
            "total_impacted_nodes": len(impact_nodes),
            "impact_distribution": {
                "high": high,
                "medium": medium,
                "low": low
            }
        },
        "impact_nodes": impact_nodes[:50],  # Limit results
        "critical_paths": []  # TODO: Implement critical path detection
    }

async def analyze_codebase():
    """Analyze the entire codebase"""
    global graph_data, file_tree
    
    print(f"🔍 Analyzing codebase at {CODEBASE_PATH}")
    
    all_nodes = []
    all_links = []
    node_ids = set()
    
    # Scan file tree
    file_tree = scan_directory(CODEBASE_PATH)
    
    # Analyze Python files
    for py_file in CODEBASE_PATH.rglob("*.py"):
        if any(part in py_file.parts for part in ['.git', '__pycache__', 'venv', '.venv']):
            continue
        nodes, links = analyze_python_file(py_file)
        all_nodes.extend(nodes)
        all_links.extend(links)
        node_ids.update(n["id"] for n in nodes)
    
    # Analyze JavaScript/TypeScript files
    for ext in ['*.js', '*.ts', '*.tsx', '*.jsx']:
        for js_file in CODEBASE_PATH.rglob(ext):
            if any(part in js_file.parts for part in ['.git', 'node_modules', '.expo']):
                continue
            nodes, links = analyze_javascript_file(js_file)
            all_nodes.extend(nodes)
            all_links.extend(links)
            node_ids.update(n["id"] for n in nodes)
    
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
        "nodes": all_nodes[:500],  # Limit for performance
        "links": valid_links[:1000]
    }
    
    # Build impact map
    build_impact_map()
    
    print(f"📊 Found {len(all_nodes)} nodes and {len(valid_links)} relationships")
    
    # Notify connected clients
    for ws in websocket_connections:
        try:
            await ws.send_json({
                "type": "analysis_complete",
                "stats": {
                    "nodes": len(all_nodes),
                    "links": len(valid_links)
                }
            })
        except Exception as e:
            pass

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    await analyze_codebase()

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
async def analyze_endpoint():
    """Re-analyze the codebase"""
    await analyze_codebase()
    return {"status": "completed", "nodes": len(graph_data["nodes"])}

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
    """Analyze impact of changes"""
    return calculate_impact(query.node_id, query.max_depth)

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
            "stats": {
                "nodes": len(graph_data["nodes"]),
                "links": len(graph_data["links"])
            }
        })
        
        while True:
            data = await websocket.receive_text()
            # Handle commands
            cmd = json.loads(data)
            if cmd.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

if __name__ == "__main__":
    print("🚀 Starting ULTRA Knowledge Graph Server")
    print("📊 Open http://localhost:8000 in your browser")
    print("🔥 Real code analysis, no mock bullshit")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)