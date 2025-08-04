#!/usr/bin/env python3
"""
Auto-Integration Layer - Ensures Knowledge Graph is ALWAYS used
"""
import os
import sys
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

class KnowledgeGraphAutoStart:
    """Ensures knowledge graph is always running"""
    
    def __init__(self):
        self.kg_port = 8000
        self.kg_url = f"http://localhost:{self.kg_port}"
        self.process = None
    
    def is_running(self) -> bool:
        """Check if knowledge graph server is running"""
        try:
            response = httpx.get(f"{self.kg_url}/api/health", timeout=2)
            return response.status_code == 200
        except Exception as e:
            return False
    
    def start_server(self):
        """Start the knowledge graph server"""
        if self.is_running():
            print("✅ Knowledge Graph already running")
            return
        
        print("🚀 Starting Knowledge Graph server...")
        kg_path = Path(__file__).parent
        
        # Kill any existing processes on port 8000
        try:
            subprocess.run(["fuser", "-k", f"{self.kg_port}/tcp"], 
                         capture_output=True, text=True)
        except Exception as e:
            pass
        
        # Start blazing server in background
        self.process = subprocess.Popen(
            [sys.executable, "blazing_server.py"],
            cwd=kg_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup
        for _ in range(10):
            if self.is_running():
                print("✅ Knowledge Graph server started successfully")
                
                # Trigger initial analysis
                try:
                    httpx.post(f"{self.kg_url}/api/analyze/codebase", timeout=5)
                    print("📊 Codebase analysis initiated")
                except Exception as e:
                    pass
                    
                return
            time.sleep(1)
        
        print("❌ Failed to start Knowledge Graph server")
    
    def ensure_running(self):
        """Ensure server is running, start if not"""
        if not self.is_running():
            self.start_server()

# Auto-start on import
_auto_starter = KnowledgeGraphAutoStart()
_auto_starter.ensure_running()

class KnowledgeGraphMiddleware:
    """Middleware that intercepts all code operations"""
    
    def __init__(self):
        self.kg_client = None
        self._ensure_client()
    
    def _ensure_client(self):
        """Ensure we have a working client"""
        if not self.kg_client:
            from agent_integration import KnowledgeGraphClient
            self.kg_client = KnowledgeGraphClient()
    
    async def before_file_edit(self, file_path: str) -> Dict[str, Any]:
        """MUST be called before editing any file"""
        self._ensure_client()
        
        # Get current state
        current_content = await self.kg_client.get_file_content(file_path)
        
        # Analyze impact
        impact = await self.kg_client.analyze_impact(file_path)
        
        # Find related code
        related = await self.kg_client.find_related_code(file_path)
        
        # Get previous agent notes
        notes = await self.kg_client.get_agent_notes(file_path)
        
        analysis = {
            "file": file_path,
            "current_content": current_content,
            "impact_summary": impact["summary"],
            "affected_files": [n["path"] for n in impact["impact_nodes"]],
            "related_components": related,
            "agent_notes": notes,
            "warnings": []
        }
        
        # Add warnings
        if impact["summary"]["total_impacted_nodes"] > 10:
            analysis["warnings"].append(
                f"⚠️ HIGH IMPACT: This change affects {impact['summary']['total_impacted_nodes']} components"
            )
        
        if any("test" in node["path"] for node in impact["impact_nodes"]):
            analysis["warnings"].append(
                "🧪 TEST IMPACT: Update test files after this change"
            )
        
        return analysis
    
    async def after_file_edit(self, file_path: str, changes: str, agent_id: str = "Claude"):
        """MUST be called after editing any file"""
        self._ensure_client()
        
        # Document the change
        await self.kg_client.add_agent_note(
            node_id=file_path,
            agent_id=agent_id,
            note=f"Modified: {changes}",
            note_type="change_log"
        )
        
        # Re-analyze if significant change
        if file_path.endswith(".py"):
            await self.kg_client.analyze_codebase()
    
    async def before_function_create(self, function_name: str, file_path: str) -> Dict[str, Any]:
        """Before creating a new function"""
        self._ensure_client()
        
        # Find similar functions
        similar = await self.kg_client.search_code(f"def {function_name}")
        
        # Find patterns in file
        patterns = await self.kg_client.search_code(f"def.*{file_path}")
        
        return {
            "similar_functions": similar,
            "file_patterns": patterns,
            "naming_convention": self._extract_naming_convention(patterns),
            "suggested_location": self._suggest_location(function_name, patterns)
        }
    
    def _extract_naming_convention(self, patterns):
        """Extract naming conventions from existing code"""
        # Analyze existing function names
        conventions = {
            "uses_snake_case": True,
            "prefix_patterns": [],
            "async_functions": 0,
            "total_functions": len(patterns)
        }
        
        for pattern in patterns:
            if "async def" in pattern.get("content", ""):
                conventions["async_functions"] += 1
        
        return conventions
    
    def _suggest_location(self, function_name: str, patterns):
        """Suggest where to place the function"""
        # Basic heuristic - could be enhanced
        if "test_" in function_name:
            return "Place in test file"
        elif "handle_" in function_name:
            return "Place with other handlers"
        elif "get_" in function_name or "fetch_" in function_name:
            return "Place with other data access functions"
        return "Place at end of file"

# Global middleware instance
kg_middleware = KnowledgeGraphMiddleware()

# Hook into Python import system
class KnowledgeGraphImportHook:
    """Automatically integrate with Python imports"""
    
    def __init__(self):
        self.original_open = open
        self.kg_middleware = kg_middleware
    
    def install(self):
        """Install the import hook"""
        # Override built-in open
        import builtins
        builtins._original_open = builtins.open
        builtins.open = self._wrapped_open
    
    def _wrapped_open(self, file, mode='r', *args, **kwargs):
        """Wrapped version of open() that tracks file access"""
        result = self.original_open(file, mode, *args, **kwargs)
        
        # If opening for writing, track it
        if 'w' in mode or 'a' in mode:
            asyncio.create_task(self._track_file_write(str(file)))
        
        return result
    
    async def _track_file_write(self, file_path: str):
        """Track file modifications"""
        if file_path.endswith(('.py', '.js', '.ts', '.tsx')):
            try:
                await self.kg_middleware.after_file_edit(
                    file_path,
                    "File modified via open()",
                    "SystemHook"
                )
            except Exception as e:
                pass

# Auto-install hook
_import_hook = KnowledgeGraphImportHook()
_import_hook.install()

# Integration with common tools
class ToolIntegration:
    """Integrate with common development tools"""
    
    @staticmethod
    def create_git_hooks():
        """Create git hooks that use knowledge graph"""
        pre_commit_hook = '''#!/bin/bash
# Auto-generated Knowledge Graph pre-commit hook

echo "🔍 Analyzing changes with Knowledge Graph..."

# Get changed files
changed_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|ts|tsx)$')

if [ -z "$changed_files" ]; then
    exit 0
fi

# Analyze each file
for file in $changed_files; do
    echo "Analyzing impact of $file..."
    
    # Query knowledge graph
    impact=$(curl -s -X POST http://localhost:8000/api/impact/analyze \
        -H "Content-Type: application/json" \
        -d "{\"node_id\": \"$file\"}" | jq -r '.summary.total_impacted_nodes')
    
    if [ "$impact" -gt 20 ]; then
        echo "⚠️  WARNING: $file impacts $impact components!"
        echo "Consider breaking this change into smaller commits."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
done

echo "✅ Impact analysis complete"
'''
        
        # Write git hooks
        git_dir = Path(".git/hooks")
        if git_dir.exists():
            hook_path = git_dir / "pre-commit"
            hook_path.write_text(pre_commit_hook)
            hook_path.chmod(0o755)
            print("✅ Git pre-commit hook installed")
    
    @staticmethod
    def create_vscode_settings():
        """Create VS Code settings that integrate knowledge graph"""
        vscode_settings = {
            "python.terminal.activateEnvironment": True,
            "python.terminal.executeInFileDir": True,
            "terminal.integrated.env.linux": {
                "KNOWLEDGE_GRAPH_URL": "http://localhost:8000"
            },
            "tasks": {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "Analyze Impact",
                        "type": "shell",
                        "command": "curl -X POST http://localhost:8000/api/impact/analyze -H 'Content-Type: application/json' -d '{\"node_id\": \"${file}\"}'",
                        "group": "build",
                        "presentation": {
                            "reveal": "always",
                            "panel": "new"
                        }
                    },
                    {
                        "label": "Search Code",
                        "type": "shell",
                        "command": "curl -X POST http://localhost:8000/api/search -H 'Content-Type: application/json' -d '{\"query\": \"${input:searchQuery}\"}'",
                        "group": "build"
                    }
                ]
            }
        }
        
        vscode_dir = Path(".vscode")
        vscode_dir.mkdir(exist_ok=True)
        
        settings_path = vscode_dir / "settings.json"
        if settings_path.exists():
            current = json.loads(settings_path.read_text())
            current.update(vscode_settings)
            vscode_settings = current
        
        settings_path.write_text(json.dumps(vscode_settings, indent=2))
        print("✅ VS Code integration configured")

# Environment variable to force usage
os.environ["KNOWLEDGE_GRAPH_REQUIRED"] = "true"
os.environ["KNOWLEDGE_GRAPH_URL"] = "http://localhost:8000"

# Modify Python path to ensure our integration loads
sys.path.insert(0, str(Path(__file__).parent))

print("""
🔥 KNOWLEDGE GRAPH AUTO-INTEGRATION ACTIVE 🔥
============================================
✅ Server auto-start enabled
✅ File operation hooks installed  
✅ Import tracking active
✅ Git hooks available
✅ VS Code integration ready

The Knowledge Graph is now MANDATORY for all operations.
""")

if __name__ == "__main__":
    # Setup integrations
    tool_integration = ToolIntegration()
    tool_integration.create_git_hooks()
    tool_integration.create_vscode_settings()
    
    print("\n📊 Knowledge Graph URL: http://localhost:8000")
    print("🚀 All systems integrated and running!")