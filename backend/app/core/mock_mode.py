"""
Mock mode utilities for development without external dependencies.
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime
import json


class MockRedis:
    """In-memory mock Redis implementation."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if key in self._expiry:
            if datetime.now() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return None
        return self._data.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiry."""
        self._data[key] = value
        if ex:
            self._expiry[key] = datetime.now().timestamp() + ex
        return True
    
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set with expiry in seconds."""
        return self.set(key, value, ex=seconds)
    
    def delete(self, key: str) -> int:
        """Delete a key."""
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        """Check if key exists."""
        return 1 if key in self._data else 0
    
    def ping(self) -> bool:
        """Ping mock Redis."""
        return True
    
    def info(self) -> Dict[str, Any]:
        """Get mock Redis info."""
        return {
            "redis_version": "7.0.0-mock",
            "connected_clients": 1,
            "used_memory_human": "1M",
            "uptime_in_seconds": 3600
        }
    
    def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
        """Mock scan implementation."""
        # Simple implementation - return all matching keys
        import fnmatch
        matching_keys = [k for k in self._data.keys() if fnmatch.fnmatch(k, match)]
        return (0, matching_keys[:count])


class MockDatabase:
    """Mock database for testing without PostgreSQL."""
    
    def __init__(self):
        self._connected = True
    
    def execute(self, query):
        """Mock execute method."""
        class MockResult:
            def scalar(self):
                return 1
        return MockResult()
    
    def get_bind(self):
        """Mock engine binding."""
        class MockPool:
            def size(self):
                return 10
            def checkedin(self):
                return 8
            def overflow(self):
                return 0
            _created = 10
        
        class MockEngine:
            pool = MockPool()
        
        return MockEngine()


def setup_mock_mode():
    """Setup environment for mock mode."""
    os.environ['USE_MOCK_APIS'] = 'true'
    os.environ['SKIP_DB_CHECK'] = 'true'
    os.environ['MOCK_REDIS'] = 'true'
    
    print("🎭 Mock mode enabled:")
    print("  - Using in-memory cache instead of Redis")
    print("  - Using SQLite instead of PostgreSQL")
    print("  - All external APIs will return mock data")


def get_mock_redis():
    """Get mock Redis instance."""
    return MockRedis()


def get_mock_database_url():
    """Get SQLite database URL for development."""
    return "sqlite:///./roadtrip_dev.db"