# Knowledge Graph Agent Integration Guide

## How Claude and Subagents Leverage the Knowledge Graph

### 1. **Real-Time Code Understanding**
```python
# Before making any change, I can instantly understand:
- What files contain the functionality
- What depends on this code
- What will break if I change it
- Where similar patterns exist
```

### 2. **Impact Analysis Before Changes**
```python
# Example: User wants to modify authentication
kg = KnowledgeGraphClient()

# Find all auth code
auth_files = await kg.search_code("JWT authentication middleware")

# Check what breaks if we change it
for file in auth_files:
    impact = await kg.analyze_impact(file["id"])
    print(f"{file['name']} affects {impact['summary']['total_impacted_nodes']} components")
```

### 3. **Pattern Recognition**
```python
# Find all instances of a pattern to ensure consistency
booking_patterns = await kg.search_code("async def book")
voice_patterns = await kg.search_code("personality_config")

# Learn from existing code
examples = await kg.find_examples("error handling try except")
```

### 4. **Subagent Coordination**

#### Navigation Agent
- Searches for: route calculations, GPS integration, mapping services
- Updates graph with: performance metrics, API usage patterns
- Checks impact on: mobile app navigation, story triggers

#### Booking Agent  
- Searches for: partner APIs, commission logic, availability checks
- Updates graph with: new integrations, API changes
- Checks impact on: payment processing, user notifications

#### Story Generation Agent
- Searches for: narrative templates, AI prompts, caching logic
- Updates graph with: new story patterns, performance data
- Checks impact on: voice generation, content filtering

#### Voice Agent
- Searches for: TTS configurations, personality definitions, audio processing
- Updates graph with: new voices, accent variations
- Checks impact on: story delivery, user preferences

#### Security Agent
- Searches for: auth endpoints, encryption usage, API keys
- Updates graph with: vulnerability findings, security patches
- Checks impact on: all protected routes, data access patterns

### 5. **Continuous Learning**

```python
# Agents document their findings
await kg.add_agent_note(
    node_id="backend/app/services/booking_agent.py",
    agent_id="BookingAgent",
    note="Ticketmaster API rate limit: 5000/day. Implement caching here.",
    note_type="optimization"
)

# Future agents learn from these notes
notes = await kg.get_agent_notes("backend/app/services/booking_agent.py")
# Returns all previous agent observations
```

### 6. **Intelligent Code Generation**

```python
# When generating new code, check existing patterns
async def generate_new_endpoint(feature: str):
    # Find similar endpoints
    similar = await kg.search_code(f"@app.post {feature}")
    
    # Extract patterns
    patterns = {
        "auth": "requires_auth" in similar[0]["content"],
        "validation": "BaseModel" in similar[0]["content"],
        "error_handling": extract_error_patterns(similar)
    }
    
    # Generate consistent with codebase
    return generate_code_with_patterns(patterns)
```

### 7. **Cross-Agent Communication**

```python
# Master Orchestration Agent builds system understanding
system_map = await kg.search_code("orchestration dispatch route")

# Shares with other agents
for agent in ["NavigationAgent", "BookingAgent", "StoryAgent"]:
    await kg.add_agent_note(
        node_id="master_orchestration",
        agent_id="MasterAgent",
        note=f"{agent} handles: {get_agent_responsibilities(agent)}",
        note_type="system_architecture"
    )
```

### 8. **Test Impact Analysis**

```python
# Before any change, find affected tests
change_file = "backend/app/services/story_generation.py"
impact = await kg.analyze_impact(change_file)

affected_tests = [
    node for node in impact["impact_nodes"] 
    if "test" in node["path"]
]

print(f"Must update {len(affected_tests)} test files")
```

### 9. **Performance Optimization**

```python
# Find performance bottlenecks
slow_endpoints = await kg.search_code("TODO optimize performance")
cache_usage = await kg.search_code("@cache redis")

# Document findings
for endpoint in slow_endpoints:
    related = await kg.find_related_code(endpoint["id"])
    await kg.add_agent_note(
        endpoint["id"],
        "PerformanceAgent",
        f"Consider caching. {len(related)} components depend on this.",
        "performance"
    )
```

### 10. **Semantic Understanding**

```python
# Natural language to code mapping
user_request = "add a pirate voice personality"

# Find semantic matches
relevant = await kg.search_code("voice personality character")
implementation = await kg.find_implementation("personality")

# Understand the full context
for impl in implementation:
    print(f"Found in: {impl['main']['path']}")
    print(f"Related components: {len(impl['related'])}")
```

## Benefits Over Traditional Approaches

1. **No More Blind Changes**: Every modification is made with full understanding of impact
2. **Consistency**: New code follows existing patterns automatically
3. **Faster Development**: Find examples and similar code instantly
4. **Better Testing**: Know exactly what tests need updating
5. **Knowledge Persistence**: Agent learnings are preserved across sessions
6. **Reduced Errors**: Impact analysis prevents breaking changes
7. **Team Coordination**: All agents share the same understanding

## Integration with Claude Code

```python
# In CLAUDE.md or agent instructions
"Before making any code changes:
1. Query the knowledge graph at http://localhost:8000
2. Search for existing implementations
3. Analyze impact of proposed changes
4. Document findings for future agents
5. Generate code consistent with patterns"
```

This transforms the codebase from static files into a living, queryable knowledge system that gets smarter with every interaction.