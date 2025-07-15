"""
FastAPI server for Knowledge Graph system
"""
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import os
from pathlib import Path

from ..core.database import KnowledgeGraphDB, CodeNode
from ..core.embeddings import EmbeddingGenerator
from ..analyzers.code_analyzer import CodebaseAnalyzer
from ..analyzers.impact_analyzer import ImpactAnalyzer


# Pydantic models
class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    file_types: Optional[List[str]] = None


class CodeUpdate(BaseModel):
    file_path: str
    content: str
    change_type: str  # create, update, delete


class ImpactQuery(BaseModel):
    node_id: str
    max_depth: int = 5


class AgentNote(BaseModel):
    node_id: str
    agent_id: str
    note: str
    note_type: str = "observation"


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

# Global instances
db: Optional[KnowledgeGraphDB] = None
embedding_gen: Optional[EmbeddingGenerator] = None
impact_analyzer: Optional[ImpactAnalyzer] = None
codebase_analyzer: Optional[CodebaseAnalyzer] = None

# WebSocket connections
active_connections: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db, embedding_gen, impact_analyzer, codebase_analyzer
    
    # Initialize database
    db = KnowledgeGraphDB(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        chroma_persist_dir="./chroma_db"
    )
    
    # Initialize services
    embedding_gen = EmbeddingGenerator(use_local_model=True)
    impact_analyzer = ImpactAnalyzer()
    codebase_analyzer = CodebaseAnalyzer(os.getenv("CODEBASE_ROOT", "."))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if db:
        db.close()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "knowledge-graph"}


@app.post("/api/analyze/codebase")
async def analyze_codebase(background_tasks: BackgroundTasks):
    """Trigger full codebase analysis"""
    background_tasks.add_task(run_codebase_analysis)
    return {"status": "analysis_started", "message": "Codebase analysis running in background"}


async def run_codebase_analysis():
    """Run full codebase analysis"""
    try:
        # Analyze codebase
        entities, relationships = codebase_analyzer.analyze_codebase()
        
        # Generate embeddings
        for entity in entities:
            if entity.type in ["file", "class", "function"]:
                embedding = embedding_gen.generate_embedding(
                    entity.content,
                    metadata={"type": entity.type, "path": entity.path}
                )
                
                # Store in database
                node = CodeNode(
                    id=entity.id,
                    type=entity.type,
                    name=entity.name,
                    path=entity.path,
                    content=entity.content,
                    metadata={
                        "line_start": entity.line_start,
                        "line_end": entity.line_end,
                        "docstring": entity.docstring,
                        "imports": entity.imports,
                        "calls": entity.calls
                    },
                    embedding=embedding.embedding
                )
                db.add_code_node(node)
        
        # Add relationships
        for source, target, rel_type in relationships:
            db.add_relationship(CodeRelationship(
                source_id=source,
                target_id=target,
                type=rel_type,
                metadata={}
            ))
        
        # Build impact graph
        impact_analyzer.build_dependency_graph(entities, relationships)
        
        # Notify connected clients
        await broadcast_update({
            "type": "analysis_complete",
            "stats": {
                "entities": len(entities),
                "relationships": len(relationships)
            }
        })
        
    except Exception as e:
        await broadcast_update({
            "type": "analysis_error",
            "error": str(e)
        })


@app.post("/api/search")
async def semantic_search(query: SearchQuery):
    """Semantic search across codebase"""
    # Generate embedding for query
    query_embedding = embedding_gen.generate_embedding(query.query)
    
    # Search
    results = db.semantic_search(
        query.query,
        query_embedding.embedding,
        limit=query.limit
    )
    
    # Get full node details
    detailed_results = []
    for node_id, score in results:
        node_context = db.get_node_context(node_id)
        if node_context:
            node_context["relevance_score"] = score
            detailed_results.append(node_context)
    
    return {"results": detailed_results}


@app.post("/api/impact/analyze")
async def analyze_impact(query: ImpactQuery):
    """Analyze impact of changes to a node"""
    heatmap = impact_analyzer.analyze_change_impact(
        query.node_id,
        query.max_depth
    )
    
    summary = impact_analyzer.get_impact_summary(heatmap)
    
    return {
        "summary": summary,
        "impact_nodes": [
            {
                "id": node.id,
                "path": node.path,
                "name": node.name,
                "impact_score": node.impact_score,
                "depth": node.depth
            }
            for node in heatmap.impact_nodes
        ],
        "file_impacts": heatmap.file_impacts
    }


@app.post("/api/code/update")
async def update_code(update: CodeUpdate):
    """Handle code updates and refresh impact analysis"""
    # Re-analyze the updated file
    analyzer = PythonCodeAnalyzer(update.file_path, update.content)
    entities, relationships = analyzer.analyze()
    
    # Update database
    for entity in entities:
        embedding = embedding_gen.generate_embedding(entity.content)
        node = CodeNode(
            id=entity.id,
            type=entity.type,
            name=entity.name,
            path=entity.path,
            content=entity.content,
            metadata={"updated_by": "user"},
            embedding=embedding.embedding
        )
        db.add_code_node(node)
    
    # Analyze impact
    file_node = next((e for e in entities if e.type == "file"), None)
    if file_node:
        heatmap = impact_analyzer.analyze_change_impact(file_node.id)
        
        # Broadcast impact update
        await broadcast_update({
            "type": "code_updated",
            "file": update.file_path,
            "impact_summary": impact_analyzer.get_impact_summary(heatmap)
        })
    
    return {"status": "updated", "entities_updated": len(entities)}


@app.post("/api/agent/note")
async def add_agent_note(note: AgentNote):
    """Add an agent note to a node"""
    note_id = db.add_agent_note(
        agent_id=note.agent_id,
        node_id=note.node_id,
        note=note.note,
        note_type=note.note_type
    )
    
    return {"note_id": note_id}


@app.get("/api/agent/notes/{node_id}")
async def get_agent_notes(node_id: str):
    """Get all agent notes for a node"""
    notes = db.get_agent_notes(node_id=node_id)
    return {"notes": notes}


@app.get("/api/graph/structure")
async def get_graph_structure():
    """Get graph structure for visualization"""
    # This would return a simplified structure for D3.js visualization
    # Implementation depends on visualization needs
    return {"nodes": [], "links": []}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except:
        active_connections.remove(websocket)


async def broadcast_update(update: Dict[str, Any]):
    """Broadcast update to all connected clients"""
    message = json.dumps(update)
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            # Remove dead connections
            active_connections.remove(connection)


# Mount static files for UI
app.mount("/", StaticFiles(directory="ui", html=True), name="static")