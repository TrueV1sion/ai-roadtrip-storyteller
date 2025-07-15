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
