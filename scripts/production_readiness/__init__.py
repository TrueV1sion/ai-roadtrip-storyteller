"""
Production Readiness Orchestration Framework

A comprehensive system for achieving production readiness through
coordinated agents that maintain codebase coherence and quality.
"""

from .orchestration_framework import (
    Task,
    TaskPriority,
    TaskStatus,
    SharedContext,
    BaseAgent,
    ContextCoordinatorAgent,
    CodeQualityAgent,
    TestingAgent,
    InfrastructureAgent,
    ImplementationAgent
)

from .specialized_agents import (
    CodebaseAnalyzerAgent,
    TestGeneratorAgent,
    ImplementationFixerAgent,
    ConfigurationAgent
)

__version__ = "1.0.0"

__all__ = [
    # Framework classes
    "Task",
    "TaskPriority", 
    "TaskStatus",
    "SharedContext",
    "BaseAgent",
    "ContextCoordinatorAgent",
    
    # Base agents
    "CodeQualityAgent",
    "TestingAgent",
    "InfrastructureAgent",
    "ImplementationAgent",
    
    # Specialized agents
    "CodebaseAnalyzerAgent",
    "TestGeneratorAgent",
    "ImplementationFixerAgent",
    "ConfigurationAgent"
]