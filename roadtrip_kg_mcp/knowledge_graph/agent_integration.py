#!/usr/bin/env python3
"""
Agent Integration Layer for Knowledge Graph
Enables Claude and subagents to query and update the graph
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
from pydantic import BaseModel

class KnowledgeGraphClient:
    """Client for agents to interact with the knowledge graph"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def search_code(self, query: str, context: str = "") -> List[Dict]:
        """Search for code patterns, functions, or concepts"""
        response = await self.client.post(
            f"{self.base_url}/api/search",
            json={"query": query, "limit": 20}
        )
        results = response.json()["results"]
        
        # Enhance with context
        for result in results:
            result["context"] = context
            result["agent_query"] = query
        
        return results
    
    async def analyze_impact(self, file_or_function: str) -> Dict:
        """Analyze impact before making changes"""
        response = await self.client.post(
            f"{self.base_url}/api/impact/analyze",
            json={"node_id": file_or_function, "max_depth": 5}
        )
        return response.json()
    
    async def find_related_code(self, node_id: str) -> List[Dict]:
        """Find all code related to a specific component"""
        # Get graph structure
        response = await self.client.get(f"{self.base_url}/api/graph/structure")
        graph = response.json()
        
        # Find connected nodes
        related = []
        for link in graph["links"]:
            if link["source"] == node_id:
                target = next((n for n in graph["nodes"] if n["id"] == link["target"]), None)
                if target:
                    related.append({
                        "node": target,
                        "relationship": link["type"]
                    })
            elif link["target"] == node_id:
                source = next((n for n in graph["nodes"] if n["id"] == link["source"]), None)
                if source:
                    related.append({
                        "node": source,
                        "relationship": f"reverse_{link['type']}"
                    })
        
        return related
    
    async def add_agent_note(self, node_id: str, agent_id: str, note: str, note_type: str = "observation"):
        """Add agent observations to the graph"""
        await self.client.post(
            f"{self.base_url}/api/agent/note",
            json={
                "node_id": node_id,
                "agent_id": agent_id,
                "note": note,
                "note_type": note_type
            }
        )
    
    async def get_file_content(self, file_path: str) -> str:
        """Get full file content"""
        response = await self.client.get(f"{self.base_url}/api/file/{file_path}")
        data = response.json()
        return data.get("content", "")
    
    async def find_implementation(self, concept: str) -> List[Dict]:
        """Find where a concept is implemented"""
        # Search for the concept
        results = await self.search_code(concept)
        
        # For each result, get related code
        implementations = []
        for result in results[:5]:  # Limit to avoid too many requests
            related = await self.find_related_code(result["id"])
            implementations.append({
                "main": result,
                "related": related
            })
        
        return implementations
    
    async def check_dependencies(self, file_path: str) -> Dict:
        """Check what depends on this file"""
        impact = await self.analyze_impact(file_path)
        
        # Group by type
        dependencies = {
            "imports_this": [],
            "uses_classes": [],
            "calls_functions": []
        }
        
        for node in impact.get("impact_nodes", []):
            if node["type"] == "file":
                dependencies["imports_this"].append(node)
            elif node["type"] == "class":
                dependencies["uses_classes"].append(node)
            elif node["type"] == "function":
                dependencies["calls_functions"].append(node)
        
        return dependencies
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()

# Agent-specific use cases
class SubAgentIntegration:
    """How different subagents can use the knowledge graph"""
    
    def __init__(self, kg_client: KnowledgeGraphClient):
        self.kg = kg_client
    
    async def navigation_agent_usage(self):
        """Navigation Agent: Find all route-related code"""
        # Find navigation implementation
        nav_code = await self.kg.search_code("navigation route path")
        
        # Check impact of changes
        for result in nav_code:
            if "navigation" in result["path"]:
                impact = await self.kg.analyze_impact(result["id"])
                await self.kg.add_agent_note(
                    result["id"],
                    "NavigationAgent",
                    f"This component affects {impact['summary']['total_impacted_nodes']} other components",
                    "impact_analysis"
                )
        
        return nav_code
    
    async def booking_agent_usage(self):
        """Booking Agent: Find all booking services and APIs"""
        # Find booking implementations
        booking_code = await self.kg.search_code("booking reservation API")
        
        # Find partner integrations
        partners = await self.kg.search_code("ticketmaster viator booking")
        
        # Document findings
        for result in booking_code:
            if "booking" in result["path"]:
                await self.kg.add_agent_note(
                    result["id"],
                    "BookingAgent",
                    "Core booking service - handles partner integrations",
                    "documentation"
                )
        
        return {"booking_services": booking_code, "partner_apis": partners}
    
    async def story_agent_usage(self):
        """Story Generation Agent: Find AI and story components"""
        # Find story generation code
        story_code = await self.kg.search_code("story generation narrative")
        
        # Find AI client usage
        ai_usage = await self.kg.search_code("vertex_ai gemini generate")
        
        # Check caching implementation
        cache_code = await self.kg.search_code("cache redis story")
        
        return {
            "story_logic": story_code,
            "ai_integration": ai_usage,
            "caching": cache_code
        }
    
    async def security_agent_usage(self):
        """Security Agent: Audit security implementations"""
        # Find authentication code
        auth_code = await self.kg.search_code("JWT auth login security")
        
        # Find API endpoints
        endpoints = await self.kg.search_code("@app.post @app.get route")
        
        # Check for vulnerabilities
        for result in auth_code:
            content = await self.kg.get_file_content(result["path"])
            if "password" in content and "bcrypt" not in content:
                await self.kg.add_agent_note(
                    result["id"],
                    "SecurityAgent",
                    "WARNING: Password handling without proper hashing detected",
                    "security_alert"
                )
        
        return {"auth": auth_code, "endpoints": endpoints}
    
    async def orchestration_agent_usage(self):
        """Master Orchestration Agent: Understand system flow"""
        # Find orchestration logic
        orchestration = await self.kg.search_code("orchestration agent route dispatch")
        
        # Map out agent communication
        agent_calls = await self.kg.search_code("agent_request sub_agent invoke")
        
        # Build system map
        system_map = {}
        for result in orchestration:
            if "orchestration" in result["path"]:
                related = await self.kg.find_related_code(result["id"])
                system_map[result["id"]] = {
                    "component": result,
                    "connections": related
                }
        
        return system_map

# Claude Code integration
class ClaudeCodeIntegration:
    """How Claude Code can use the knowledge graph"""
    
    def __init__(self, kg_client: KnowledgeGraphClient):
        self.kg = kg_client
    
    async def understand_change_request(self, user_request: str) -> Dict:
        """Analyze a user's change request"""
        # Search for relevant code
        relevant_code = await self.kg.search_code(user_request)
        
        # For each relevant file, check impact
        analysis = {
            "relevant_files": relevant_code,
            "impact_analysis": [],
            "dependencies": []
        }
        
        for code in relevant_code[:3]:  # Top 3 results
            impact = await self.kg.analyze_impact(code["id"])
            deps = await self.kg.check_dependencies(code["path"])
            
            analysis["impact_analysis"].append({
                "file": code["path"],
                "impact": impact["summary"]
            })
            analysis["dependencies"].append({
                "file": code["path"],
                "deps": deps
            })
        
        return analysis
    
    async def find_examples(self, pattern: str) -> List[Dict]:
        """Find code examples of a pattern"""
        examples = await self.kg.search_code(pattern)
        
        # Get full context for each example
        detailed_examples = []
        for example in examples[:5]:
            content = await self.kg.get_file_content(example["path"])
            detailed_examples.append({
                "file": example["path"],
                "matching_lines": example.get("matching_lines", []),
                "full_content": content
            })
        
        return detailed_examples
    
    async def verify_changes(self, changed_files: List[str]) -> Dict:
        """Verify impact of changes before committing"""
        verification = {
            "total_impact": 0,
            "critical_impacts": [],
            "test_files_affected": []
        }
        
        for file in changed_files:
            impact = await self.kg.analyze_impact(file)
            verification["total_impact"] += impact["summary"]["total_impacted_nodes"]
            
            # Check for critical impacts
            for node in impact["impact_nodes"]:
                if node["impact_score"] > 0.8:
                    verification["critical_impacts"].append(node)
                if "test" in node["path"]:
                    verification["test_files_affected"].append(node)
        
        return verification

# Example usage for Claude
async def claude_example():
    """Example of how Claude would use the knowledge graph"""
    kg = KnowledgeGraphClient()
    claude = ClaudeCodeIntegration(kg)
    
    # User asks: "I need to add a new voice personality"
    analysis = await claude.understand_change_request("voice personality TTS")
    print("Files to modify:", [f["path"] for f in analysis["relevant_files"]])
    
    # Find examples of existing personalities
    examples = await claude.find_examples("personality voice character")
    print("Examples found in:", [e["file"] for e in examples])
    
    # Before making changes, check impact
    verification = await claude.verify_changes(["backend/app/services/voice_services.py"])
    print(f"Changes will impact {verification['total_impact']} components")
    
    await kg.close()

# Subagent example
async def subagent_example():
    """Example of how subagents would use the knowledge graph"""
    kg = KnowledgeGraphClient()
    agents = SubAgentIntegration(kg)
    
    # Navigation agent finding route code
    nav_code = await agents.navigation_agent_usage()
    print(f"Navigation agent found {len(nav_code)} relevant files")
    
    # Booking agent analyzing integrations
    booking_analysis = await agents.booking_agent_usage()
    print(f"Found {len(booking_analysis['partner_apis'])} partner integrations")
    
    # Security agent audit
    security_audit = await agents.security_agent_usage()
    print(f"Security scan found {len(security_audit['auth'])} auth components")
    
    await kg.close()

if __name__ == "__main__":
    # Run examples
    asyncio.run(claude_example())
    # asyncio.run(subagent_example())