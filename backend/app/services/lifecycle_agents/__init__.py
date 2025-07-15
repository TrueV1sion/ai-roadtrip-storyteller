"""
Lifecycle Agents Package

This package contains the lifecycle-based agent implementations that integrate
Google's travel-concierge patterns with the AI Road Trip Storyteller.

The agents manage different phases of the trip lifecycle:
- PreTripAgent: Planning, itinerary creation, and narrative preparation
- InTripAgent: Real-time navigation, story generation, and dynamic adaptations
- PostTripAgent: Memory consolidation, highlights generation, and sharing

The LifecycleOrchestrator provides intelligent routing between lifecycle agents
and the existing master orchestration agent for seamless integration.

Each agent integrates with the existing master orchestration agent and uses
the trip memory system for state management.
"""

from .base_lifecycle_agent import BaseLifecycleAgent, LifecycleContext, LifecycleResponse, LifecycleState
from .pre_trip_agent import PreTripAgent
from .in_trip_agent import InTripAgent
from .post_trip_agent import PostTripAgent
from .lifecycle_orchestrator import LifecycleOrchestrator, OrchestrationRequest, OrchestrationResponse, OrchestrationMode

__all__ = [
    "BaseLifecycleAgent",
    "LifecycleContext", 
    "LifecycleResponse",
    "LifecycleState",
    "PreTripAgent",
    "InTripAgent", 
    "PostTripAgent",
    "LifecycleOrchestrator",
    "OrchestrationRequest",
    "OrchestrationResponse",
    "OrchestrationMode"
]