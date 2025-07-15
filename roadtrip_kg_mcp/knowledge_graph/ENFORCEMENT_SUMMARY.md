# Knowledge Graph Enforcement Summary

## How We Ensure It's ALWAYS Used:

### 1. **CLAUDE.md Integration** ✅
- Added MANDATORY section at the top
- Clear workflow for every operation
- Specific curl commands for each step
- Can't miss it - it's the first thing you see

### 2. **Auto-Start System**
```bash
# The blazing_server.py auto-starts when imported
# Any Python operation triggers the KG
```

### 3. **Git Pre-Commit Hooks**
- Blocks commits if KG isn't running
- Analyzes impact of all changes
- Warns on high-impact modifications

### 4. **Environment Variables**
```bash
export KNOWLEDGE_GRAPH_URL=http://localhost:8000
export KNOWLEDGE_GRAPH_REQUIRED=true
```

### 5. **VS Code Integration**
- Tasks for quick KG operations
- Keyboard shortcuts for search/impact
- Status bar shows KG health

### 6. **Shell Alias**
```bash
alias roadtrip='cd /path/to/project && ./start_with_kg.sh'
# Always starts with KG running
```

### 7. **Agent Instructions**
- All agent files updated
- KG consultation is first step
- Can't proceed without checking

### 8. **Import Hooks**
```python
# Auto-integration tracks all file operations
# Logs changes automatically
```

### 9. **Continuous Monitoring**
```bash
# Background process checks KG health
# Alerts if it goes down
```

### 10. **Documentation Integration**
- Every task starts with KG search
- Impact analysis before changes
- Pattern matching for new code
- Change documentation after edits

## Quick Verification:

```bash
# Check if KG is running
curl http://localhost:8000/api/health

# See current stats
curl http://localhost:8000/api/health | jq

# Test search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

## For Subagents:

Each subagent MUST:
1. Import `from knowledge_graph.agent_integration import KnowledgeGraphClient`
2. Initialize client: `kg = KnowledgeGraphClient()`
3. Search before analyzing: `await kg.search_code("task terms")`
4. Check impact: `await kg.analyze_impact("file.py")`
5. Document changes: `await kg.add_agent_note(...)`

## Enforcement Metrics:

- **Pre-commit blocks**: Prevents disasters
- **Auto-documentation**: Every change logged
- **Impact tracking**: Know before you break
- **Pattern library**: Consistency enforced
- **Agent memory**: Learnings preserved

The Knowledge Graph is now as essential as syntax checking!