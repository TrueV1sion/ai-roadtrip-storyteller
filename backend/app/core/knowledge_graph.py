"""
Knowledge Graph Integration for Backend Services
Provides decorators and utilities for automatic KG consultation
"""

import os
import asyncio
import functools
import logging
from typing import Any, Callable, Dict, List, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Knowledge Graph configuration
KG_URL = os.getenv("KNOWLEDGE_GRAPH_URL", "http://localhost:8000")
KG_ENABLED = os.getenv("KNOWLEDGE_GRAPH_ENABLED", "false").lower() == "true"
KG_TIMEOUT = float(os.getenv("KNOWLEDGE_GRAPH_TIMEOUT", "5.0"))


class KnowledgeGraphClient:
    """Client for interacting with Knowledge Graph service"""
    
    def __init__(self):
        self.base_url = KG_URL
        self.enabled = KG_ENABLED
        self._client = None
        
    @property
    def client(self):
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=KG_TIMEOUT
            )
        return self._client
    
    async def analyze_impact(self, file_path: str) -> Dict[str, Any]:
        """Analyze impact of changes to a file"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            response = await self.client.post(
                "/api/impact/analyze",
                json={"node_id": file_path}
            )
            return response.json()
        except Exception as e:
            logger.warning(f"KG impact analysis failed: {e}")
            return {"error": str(e)}
    
    async def search_patterns(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for code patterns"""
        if not self.enabled:
            return []
        
        try:
            response = await self.client.post(
                "/api/search",
                json={"query": query, "limit": limit}
            )
            return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"KG pattern search failed: {e}")
            return []
    
    async def notify_change(self, file_path: str, change_type: str = "modified"):
        """Notify KG of file change"""
        if not self.enabled:
            return
        
        try:
            await self.client.post(
                "/api/agent/file-change",
                json={
                    "file_path": file_path,
                    "change_type": change_type
                }
            )
        except Exception as e:
            logger.warning(f"KG change notification failed: {e}")
    
    async def add_note(self, node_id: str, note: str):
        """Add note about code changes"""
        if not self.enabled:
            return
        
        try:
            await self.client.post(
                "/api/agent/note",
                json={
                    "node_id": node_id,
                    "agent_id": "backend-service",
                    "note": note
                }
            )
        except Exception as e:
            logger.warning(f"KG note addition failed: {e}")
    
    async def validate_patterns(self, file_path: str, content: str) -> Dict[str, Any]:
        """Validate code patterns"""
        if not self.enabled:
            return {"valid": True}
        
        try:
            response = await self.client.post(
                "/api/agent/analyze",
                json={
                    "type": "pattern_check",
                    "data": {
                        "file_path": file_path,
                        "content": content
                    }
                }
            )
            return response.json()
        except Exception as e:
            logger.warning(f"KG pattern validation failed: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the client connection"""
        if self._client:
            await self._client.aclose()


# Global client instance
kg_client = KnowledgeGraphClient()


# Decorators

def kg_analyze_impact(func: Callable) -> Callable:
    """
    Decorator to analyze impact before executing a function
    Use on functions that modify important data or configurations
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract file path from function context
        module = func.__module__
        file_path = f"backend/{module.replace('.', '/')}.py"
        
        # Analyze impact
        impact = await kg_client.analyze_impact(file_path)
        
        # Log high-impact operations
        if impact.get("dependencies", []):
            logger.info(f"KG Impact: {func.__name__} affects {len(impact['dependencies'])} files")
        
        # Execute function
        result = await func(*args, **kwargs)
        
        # Notify KG of completion
        await kg_client.add_note(
            file_path,
            f"Function {func.__name__} executed successfully"
        )
        
        return result
    
    return wrapper


def kg_pattern_check(pattern_type: str = "general"):
    """
    Decorator to check if implementation follows established patterns
    Use on new service methods or route handlers
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Search for similar patterns
            patterns = await kg_client.search_patterns(
                f"{pattern_type} {func.__name__}",
                limit=5
            )
            
            if patterns:
                logger.debug(f"KG: Found {len(patterns)} similar patterns for {func.__name__}")
            
            # Execute function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def kg_track_usage(service_name: str):
    """
    Decorator to track service usage patterns
    Use on service class methods
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Track successful usage
                await kg_client.add_note(
                    f"services/{service_name}",
                    f"Method {func.__name__} called successfully"
                )
                
                return result
                
            except Exception as e:
                # Track errors
                await kg_client.add_note(
                    f"services/{service_name}",
                    f"Method {func.__name__} failed: {str(e)}"
                )
                raise
        
        return wrapper
    return decorator


def kg_suggest_improvements(func: Callable) -> Callable:
    """
    Decorator to get improvement suggestions from KG
    Use during development on methods you want to optimize
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get suggestions before execution
        module = func.__module__
        suggestions = await kg_client.search_patterns(
            f"optimize {func.__name__}",
            limit=3
        )
        
        if suggestions and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"KG Suggestions for {func.__name__}:")
            for s in suggestions:
                logger.debug(f"  - {s.get('suggestion', s)}")
        
        # Execute function
        return await func(*args, **kwargs)
    
    return wrapper


# Context managers

class KGTransaction:
    """
    Context manager for tracking complex operations
    Use for multi-step processes that should be tracked as a unit
    """
    
    def __init__(self, operation_name: str, metadata: Dict[str, Any] = None):
        self.operation_name = operation_name
        self.metadata = metadata or {}
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = datetime.now()
        await kg_client.add_note(
            "transactions",
            f"Starting {self.operation_name}: {self.metadata}"
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            await kg_client.add_note(
                "transactions",
                f"Failed {self.operation_name} after {duration}s: {exc_val}"
            )
        else:
            await kg_client.add_note(
                "transactions",
                f"Completed {self.operation_name} in {duration}s"
            )


# Middleware for automatic KG integration

class KnowledgeGraphMiddleware:
    """
    FastAPI middleware for automatic KG integration
    Tracks API usage and patterns
    """
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            method = scope["method"]
            
            # Track API call
            if kg_client.enabled and path.startswith("/api/"):
                await kg_client.add_note(
                    "api_routes",
                    f"{method} {path} called"
                )
        
        await self.app(scope, receive, send)


# Utility functions

async def find_similar_implementations(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Find similar implementations in the codebase"""
    return await kg_client.search_patterns(query, limit)


async def check_breaking_changes(file_path: str) -> bool:
    """Check if changes to file would cause breaking changes"""
    impact = await kg_client.analyze_impact(file_path)
    
    # Consider it breaking if it affects tests or core files
    critical_deps = [
        d for d in impact.get("dependencies", [])
        if any(x in d for x in ["test", "core", "main", "api"])
    ]
    
    return len(critical_deps) > 0


async def get_code_suggestions(context: str) -> List[str]:
    """Get code suggestions based on context"""
    patterns = await kg_client.search_patterns(context, limit=3)
    return [p.get("suggestion", str(p)) for p in patterns]


# Initialize on import if enabled
if KG_ENABLED:
    logger.info("Knowledge Graph integration enabled")
else:
    logger.info("Knowledge Graph integration disabled")