#!/bin/bash
# Knowledge Graph Enforcement Setup
# This script ensures the knowledge graph is ALWAYS used

echo "🔧 Setting up Knowledge Graph enforcement..."

# 1. Create startup script
cat > ../start_with_kg.sh << 'EOF'
#!/bin/bash
# Always start with Knowledge Graph

echo "🚀 Starting AI Road Trip development environment..."

# Start Knowledge Graph first
echo "📊 Starting Knowledge Graph server..."
cd knowledge_graph
python3 blazing_server.py > kg.log 2>&1 &
KG_PID=$!

# Wait for it to be ready
sleep 3
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Knowledge Graph running at http://localhost:8000"
    
    # Trigger initial analysis
    curl -X POST http://localhost:8000/api/analyze/codebase
    echo "📊 Codebase analysis initiated"
else
    echo "❌ Knowledge Graph failed to start"
    exit 1
fi

# Now start regular development
cd ..
echo "Ready for development with Knowledge Graph integration!"
echo "Dashboard: http://localhost:8000"

# Keep running
wait $KG_PID
EOF

chmod +x ../start_with_kg.sh

# 2. Add to shell profile
SHELL_RC="$HOME/.bashrc"
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

# Add alias if not already present
if ! grep -q "alias roadtrip=" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# AI Road Trip Knowledge Graph" >> "$SHELL_RC"
    echo "alias roadtrip='cd $(pwd)/.. && ./start_with_kg.sh'" >> "$SHELL_RC"
    echo "export KNOWLEDGE_GRAPH_URL=http://localhost:8000" >> "$SHELL_RC"
fi

# 3. Create git hooks
cat > ../.git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Knowledge Graph pre-commit hook

echo "🔍 Checking Knowledge Graph..."

# Ensure KG is running
if ! curl -s http://localhost:8000/api/health > /dev/null; then
    echo "❌ ERROR: Knowledge Graph is not running!"
    echo "Start it with: cd knowledge_graph && python3 blazing_server.py"
    exit 1
fi

# Get changed files
changed_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|ts|tsx)$')

if [ -z "$changed_files" ]; then
    exit 0
fi

# Analyze each file
for file in $changed_files; do
    echo "Analyzing impact of $file..."
    
    # Query knowledge graph
    response=$(curl -s -X POST http://localhost:8000/api/impact/analyze \
        -H "Content-Type: application/json" \
        -d "{\"node_id\": \"$file\"}")
    
    impact=$(echo $response | grep -o '"total_impacted_nodes":[0-9]*' | cut -d: -f2)
    
    if [ -n "$impact" ] && [ "$impact" -gt 20 ]; then
        echo "⚠️  WARNING: $file impacts $impact components!"
        echo "Run full impact analysis at http://localhost:8000"
    fi
done

echo "✅ Knowledge Graph check complete"
EOF

chmod +x ../.git/hooks/pre-commit

# 4. Create VS Code tasks
mkdir -p ../.vscode
cat > ../.vscode/tasks.json << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Knowledge Graph: Search",
            "type": "shell",
            "command": "curl -X POST http://localhost:8000/api/search -H 'Content-Type: application/json' -d '{\"query\": \"${input:searchQuery}\"}'",
            "problemMatcher": []
        },
        {
            "label": "Knowledge Graph: Impact Analysis",
            "type": "shell",
            "command": "curl -X POST http://localhost:8000/api/impact/analyze -H 'Content-Type: application/json' -d '{\"node_id\": \"${relativeFile}\"}'",
            "problemMatcher": []
        },
        {
            "label": "Knowledge Graph: Open Dashboard",
            "type": "shell",
            "command": "open http://localhost:8000 || xdg-open http://localhost:8000",
            "problemMatcher": []
        }
    ],
    "inputs": [
        {
            "id": "searchQuery",
            "type": "promptString",
            "description": "Enter search query"
        }
    ]
}
EOF

# 5. Create enforcement checker
cat > ../check_kg.py << 'EOF'
#!/usr/bin/env python3
"""Check if Knowledge Graph is being used properly"""
import sys
import httpx

def check_kg():
    try:
        response = httpx.get("http://localhost:8000/api/health", timeout=2)
        if response.status_code == 200:
            stats = response.json()["stats"]
            print(f"✅ Knowledge Graph is running")
            print(f"📊 Indexed: {stats['indexed_files']} files")
            print(f"🔗 Graph: {stats['nodes']} nodes, {stats['links']} links")
            return True
    except:
        pass
    
    print("❌ Knowledge Graph is NOT running!")
    print("Start it with: cd knowledge_graph && python3 blazing_server.py")
    return False

if __name__ == "__main__":
    if not check_kg():
        sys.exit(1)
EOF

chmod +x ../check_kg.py

# 6. Create agent instruction updater
cat > update_agent_instructions.py << 'EOF'
#!/usr/bin/env python3
"""Update all agent instructions to use Knowledge Graph"""
import os
from pathlib import Path

kg_instruction = """
# MANDATORY: Knowledge Graph Integration

Before ANY operation, consult the Knowledge Graph at http://localhost:8000:

1. Search for existing implementations:
   curl -X POST http://localhost:8000/api/search -d '{"query": "YOUR_TASK"}'

2. Check impact before changes:
   curl -X POST http://localhost:8000/api/impact/analyze -d '{"node_id": "FILE_PATH"}'

3. Find patterns:
   curl -X POST http://localhost:8000/api/search -d '{"query": "PATTERN_NAME"}'

4. Document changes:
   curl -X POST http://localhost:8000/api/agent/note -d '{"node_id": "FILE", "agent_id": "AGENT_NAME", "note": "CHANGES"}'
"""

# Find all agent files
agent_files = list(Path("..").rglob("*agent*.py"))
instruction_files = list(Path("..").rglob("*instruction*.md"))

print(f"Found {len(agent_files)} agent files and {len(instruction_files)} instruction files")

# Update them
for file in agent_files + instruction_files:
    if file.is_file():
        content = file.read_text()
        if "Knowledge Graph" not in content:
            # Add to docstring or top of file
            if file.suffix == ".py" and '"""' in content:
                content = content.replace('"""', f'"""\n{kg_instruction}\n', 1)
            else:
                content = kg_instruction + "\n\n" + content
            
            file.write_text(content)
            print(f"✅ Updated {file}")

print("✅ All agent instructions updated")
EOF

python3 update_agent_instructions.py

echo """
✅ Knowledge Graph Enforcement Setup Complete!
============================================

🚀 Quick Start:
   Type 'roadtrip' in terminal to start with KG

📊 Dashboard:
   http://localhost:8000

🔧 VS Code:
   Use Ctrl+Shift+P > Tasks > Knowledge Graph

🪝 Git Hooks:
   Pre-commit hook will check impact

📖 Instructions:
   All agents updated to use KG

The Knowledge Graph is now MANDATORY for all development!
"""