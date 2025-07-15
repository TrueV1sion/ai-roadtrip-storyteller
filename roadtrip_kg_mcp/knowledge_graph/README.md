# AI Road Trip Knowledge Graph System

## Overview

A semantic search-enabled contextual knowledge graph database for the AI Road Trip Storyteller codebase. This system enables intelligent code analysis, impact tracking, and agent collaboration.

## Architecture

```
knowledge_graph/
├── core/
│   ├── database.py         # Neo4j graph database interface
│   ├── embeddings.py       # Semantic vector embeddings
│   └── search.py           # Semantic search engine
├── analyzers/
│   ├── code_analyzer.py    # AST-based code analysis
│   ├── dependency_mapper.py # Dependency graph builder
│   └── impact_analyzer.py  # Change impact heatmap
├── agents/
│   ├── base_agent.py       # Base agent class
│   ├── code_scout.py       # Code exploration agent
│   ├── architect.py        # Architecture analysis agent
│   └── historian.py        # Change history tracker
├── api/
│   ├── server.py           # FastAPI backend
│   └── websocket.py        # Real-time updates
└── ui/
    ├── index.html          # Main interface
    ├── graph_viz.js        # D3.js graph visualization
    └── claude_integration.js # Claude Code SDK integration
```

## Features

1. **Semantic Code Search** - Find code by meaning, not just text
2. **Impact Heatmap** - Visual change impact analysis
3. **Agent Collaboration** - Async agent notes and planning
4. **Live Code Graph** - Real-time codebase visualization
5. **Claude Integration** - Direct Claude Code CLI access

## Tech Stack

- **Database**: Neo4j (graph) + ChromaDB (vectors)
- **Backend**: FastAPI + WebSockets
- **Frontend**: React + D3.js + Monaco Editor
- **AI**: OpenAI embeddings + Claude Code SDK
- **Analysis**: Python AST + NetworkX