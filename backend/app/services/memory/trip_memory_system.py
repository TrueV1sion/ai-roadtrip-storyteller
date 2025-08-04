"""
Trip Memory System - Hybrid approach combining Google's lifecycle patterns
with AI Road Trip Storyteller's narrative capabilities.
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.logger import logger
from app.core.cache import cache_manager
from app.models.user import User
from app.models.trip import Trip
from app.models.story import Story
from app.services.master_orchestration_agent import MasterOrchestrationAgent
from app.core.standardized_errors import handle_errors


class TripPhase(str, Enum):
    """Trip lifecycle phases inspired by Google's travel-concierge."""
    PRE_TRIP = "pre_trip"        # Planning and anticipation
    IN_TRIP = "in_trip"          # Active journey
    POST_TRIP = "post_trip"      # Memories and reflection
    ARCHIVED = "archived"         # Long-term storage


@dataclass
class TripMemory:
    """Structured memory for a trip segment."""
    trip_id: str
    phase: TripPhase
    timestamp: datetime
    location: Dict[str, float]  # lat, lng
    context: Dict[str, Any]
    narrative_elements: List[str] = field(default_factory=list)
    user_interactions: List[Dict] = field(default_factory=list)
    emotional_markers: Dict[str, float] = field(default_factory=dict)
    media_references: List[str] = field(default_factory=list)
    poi_visited: List[Dict] = field(default_factory=list)
    voice_personality_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "trip_id": self.trip_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "context": self.context,
            "narrative_elements": self.narrative_elements,
            "user_interactions": self.user_interactions,
            "emotional_markers": self.emotional_markers,
            "media_references": self.media_references,
            "poi_visited": self.poi_visited,
            "voice_personality_used": self.voice_personality_used
        }


class TripMemorySystem:
    """
    Manages trip memories across all phases, integrating Google's lifecycle
    approach with narrative storytelling.
    """
    
    def __init__(self, db: Session, orchestrator: MasterOrchestrationAgent):
        self.db = db
        self.orchestrator = orchestrator
        self.active_memories: Dict[str, List[TripMemory]] = {}
        self.memory_index: Dict[str, Set[str]] = {}  # Quick lookup by user
        
        # Memory configuration
        self.max_active_memories = 1000  # Per trip
        self.memory_ttl = 86400 * 30  # 30 days in cache
        self.consolidation_threshold = 100  # Memories before consolidation
        
        logger.info("Trip Memory System initialized")
    
    @handle_errors(default_error_code="MEMORY_CREATION_FAILED")
    async def create_trip_memory(
        self,
        trip_id: str,
        phase: TripPhase,
        context: Dict[str, Any],
        location: Optional[Dict[str, float]] = None
    ) -> TripMemory:
        """
        Create a new trip memory entry.
        
        Args:
            trip_id: Trip identifier
            phase: Current trip phase
            context: Memory context (POIs, weather, events, etc.)
            location: Current location
            
        Returns:
            Created TripMemory instance
        """
        memory = TripMemory(
            trip_id=trip_id,
            phase=phase,
            timestamp=datetime.utcnow(),
            location=location or {"lat": 0.0, "lng": 0.0},
            context=context
        )
        
        # Extract relevant information from context
        if "poi" in context:
            memory.poi_visited.append(context["poi"])
        
        if "narrative" in context:
            memory.narrative_elements.append(context["narrative"])
        
        if "voice_personality" in context:
            memory.voice_personality_used = context["voice_personality"]
        
        if "user_feedback" in context:
            memory.user_interactions.append({
                "type": "feedback",
                "value": context["user_feedback"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Store in active memory
        if trip_id not in self.active_memories:
            self.active_memories[trip_id] = []
        
        self.active_memories[trip_id].append(memory)
        
        # Check if consolidation needed
        if len(self.active_memories[trip_id]) >= self.consolidation_threshold:
            await self._consolidate_memories(trip_id)
        
        # Cache the memory
        cache_key = f"memory:{trip_id}:{memory.timestamp.timestamp()}"
        await cache_manager.setex(
            cache_key,
            self.memory_ttl,
            json.dumps(memory.to_dict())
        )
        
        logger.info(f"Created memory for trip {trip_id} in phase {phase}")
        return memory
    
    async def get_trip_memories(
        self,
        trip_id: str,
        phase: Optional[TripPhase] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TripMemory]:
        """
        Retrieve memories for a trip with optional filters.
        
        Args:
            trip_id: Trip identifier
            phase: Filter by trip phase
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum memories to return
            
        Returns:
            List of matching memories
        """
        # Check active memories first
        memories = self.active_memories.get(trip_id, [])
        
        # Apply filters
        if phase:
            memories = [m for m in memories if m.phase == phase]
        
        if start_time:
            memories = [m for m in memories if m.timestamp >= start_time]
        
        if end_time:
            memories = [m for m in memories if m.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        memories.sort(key=lambda x: x.timestamp, reverse=True)
        memories = memories[:limit]
        
        # If not enough in active memory, check cache/database
        if len(memories) < limit:
            additional = await self._load_archived_memories(
                trip_id, phase, start_time, end_time, 
                limit - len(memories)
            )
            memories.extend(additional)
        
        return memories
    
    async def transition_trip_phase(
        self,
        trip_id: str,
        new_phase: TripPhase
    ) -> Dict[str, Any]:
        """
        Transition a trip to a new phase with memory consolidation.
        
        Args:
            trip_id: Trip identifier
            new_phase: New trip phase
            
        Returns:
            Transition summary
        """
        # Get current memories
        current_memories = self.active_memories.get(trip_id, [])
        
        if not current_memories:
            logger.warning(f"No memories found for trip {trip_id}")
            return {"status": "no_memories", "trip_id": trip_id}
        
        # Determine current phase
        current_phase = current_memories[-1].phase if current_memories else TripPhase.PRE_TRIP
        
        # Consolidate memories for the ending phase
        phase_summary = await self._create_phase_summary(trip_id, current_phase)
        
        # Create transition memory
        transition_memory = await self.create_trip_memory(
            trip_id=trip_id,
            phase=new_phase,
            context={
                "transition": True,
                "from_phase": current_phase.value,
                "to_phase": new_phase.value,
                "phase_summary": phase_summary
            }
        )
        
        # Special handling for phase transitions
        if new_phase == TripPhase.POST_TRIP:
            # Generate trip highlights
            highlights = await self._generate_trip_highlights(trip_id)
            await self.create_trip_memory(
                trip_id=trip_id,
                phase=new_phase,
                context={"highlights": highlights}
            )
        
        elif new_phase == TripPhase.ARCHIVED:
            # Archive all memories
            await self._archive_trip_memories(trip_id)
        
        logger.info(f"Transitioned trip {trip_id} from {current_phase} to {new_phase}")
        
        return {
            "trip_id": trip_id,
            "previous_phase": current_phase.value,
            "new_phase": new_phase.value,
            "phase_summary": phase_summary,
            "transition_memory_id": transition_memory.timestamp.timestamp()
        }
    
    async def get_contextual_memories(
        self,
        trip_id: str,
        current_location: Dict[str, float],
        radius_km: float = 5.0,
        context_type: Optional[str] = None
    ) -> List[TripMemory]:
        """
        Get memories relevant to current context (location-based).
        
        Args:
            trip_id: Trip identifier
            current_location: Current lat/lng
            radius_km: Search radius in kilometers
            context_type: Filter by context type (poi, narrative, etc.)
            
        Returns:
            Relevant memories sorted by proximity and recency
        """
        memories = self.active_memories.get(trip_id, [])
        
        # Filter by location proximity
        relevant_memories = []
        for memory in memories:
            if memory.location:
                distance = self._calculate_distance(
                    current_location,
                    memory.location
                )
                if distance <= radius_km:
                    relevant_memories.append((memory, distance))
        
        # Sort by distance then recency
        relevant_memories.sort(key=lambda x: (x[1], -x[0].timestamp.timestamp()))
        
        # Filter by context type if specified
        if context_type:
            relevant_memories = [
                (m, d) for m, d in relevant_memories
                if context_type in m.context or any(context_type in n for n in m.narrative_elements)
            ]
        
        return [m for m, _ in relevant_memories[:20]]  # Return top 20
    
    async def generate_memory_narrative(
        self,
        trip_id: str,
        phase: Optional[TripPhase] = None,
        narrative_style: str = "nostalgic"
    ) -> Dict[str, Any]:
        """
        Generate a narrative summary from trip memories.
        
        Args:
            trip_id: Trip identifier
            phase: Specific phase to narrate
            narrative_style: Style of narrative
            
        Returns:
            Generated narrative with metadata
        """
        # Get relevant memories
        memories = await self.get_trip_memories(trip_id, phase)
        
        if not memories:
            return {
                "narrative": "No memories found for this trip.",
                "memory_count": 0
            }
        
        # Extract key elements for narrative
        narrative_context = {
            "locations": [m.location for m in memories if m.location],
            "pois": [poi for m in memories for poi in m.poi_visited],
            "emotional_journey": [m.emotional_markers for m in memories if m.emotional_markers],
            "key_moments": [m.context for m in memories if m.context.get("highlight")],
            "narrative_style": narrative_style,
            "phase": phase.value if phase else "full_trip"
        }
        
        # Use orchestrator to generate narrative
        narrative_response = await self.orchestrator.orchestrate(
            user_input=f"Generate a {narrative_style} narrative from trip memories",
            context=narrative_context,
            conversation_history=[]
        )
        
        return {
            "narrative": narrative_response.get("response", ""),
            "memory_count": len(memories),
            "locations_covered": len(set(str(m.location) for m in memories if m.location)),
            "phase": phase.value if phase else "full_trip",
            "style": narrative_style
        }
    
    async def _consolidate_memories(self, trip_id: str):
        """Consolidate memories when threshold reached."""
        memories = self.active_memories.get(trip_id, [])
        
        if len(memories) < self.consolidation_threshold:
            return
        
        # Group memories by time windows (e.g., hourly)
        time_windows = {}
        for memory in memories:
            window_key = memory.timestamp.replace(minute=0, second=0, microsecond=0)
            if window_key not in time_windows:
                time_windows[window_key] = []
            time_windows[window_key].append(memory)
        
        # Create consolidated memories
        consolidated = []
        for window, window_memories in time_windows.items():
            # Merge memories in the same time window
            consolidated_memory = TripMemory(
                trip_id=trip_id,
                phase=window_memories[0].phase,
                timestamp=window,
                location=self._average_location([m.location for m in window_memories if m.location]),
                context={"consolidated": True, "count": len(window_memories)}
            )
            
            # Merge narrative elements
            consolidated_memory.narrative_elements = list(set(
                elem for m in window_memories for elem in m.narrative_elements
            ))
            
            # Merge POIs
            consolidated_memory.poi_visited = list({
                json.dumps(poi, sort_keys=True): poi 
                for m in window_memories for poi in m.poi_visited
            }.values())
            
            # Average emotional markers
            if any(m.emotional_markers for m in window_memories):
                all_emotions = {}
                for m in window_memories:
                    for emotion, value in m.emotional_markers.items():
                        if emotion not in all_emotions:
                            all_emotions[emotion] = []
                        all_emotions[emotion].append(value)
                
                consolidated_memory.emotional_markers = {
                    emotion: sum(values) / len(values)
                    for emotion, values in all_emotions.items()
                }
            
            consolidated.append(consolidated_memory)
        
        # Replace active memories with consolidated version
        self.active_memories[trip_id] = consolidated[-50:]  # Keep last 50 consolidated
        
        # Archive older consolidated memories
        if len(consolidated) > 50:
            await self._archive_memories(trip_id, consolidated[:-50])
        
        logger.info(f"Consolidated {len(memories)} memories into {len(consolidated)} for trip {trip_id}")
    
    async def _create_phase_summary(
        self,
        trip_id: str,
        phase: TripPhase
    ) -> Dict[str, Any]:
        """Create a summary of a trip phase."""
        memories = await self.get_trip_memories(trip_id, phase)
        
        if not memories:
            return {"phase": phase.value, "summary": "No activities recorded"}
        
        # Analyze memories for patterns
        summary = {
            "phase": phase.value,
            "duration": (memories[0].timestamp - memories[-1].timestamp).total_seconds() / 3600,  # hours
            "memory_count": len(memories),
            "locations_visited": len(set(str(m.location) for m in memories if m.location)),
            "pois_visited": len(set(
                poi.get("name", "") for m in memories for poi in m.poi_visited
            )),
            "dominant_emotions": self._calculate_dominant_emotions(memories),
            "key_narratives": self._extract_key_narratives(memories),
            "user_engagement": self._calculate_engagement_score(memories)
        }
        
        return summary
    
    async def _generate_trip_highlights(self, trip_id: str) -> List[Dict[str, Any]]:
        """Generate highlights from the trip."""
        memories = await self.get_trip_memories(trip_id)
        
        highlights = []
        
        # Find memories with high emotional scores
        emotional_highlights = [
            m for m in memories 
            if any(v > 0.7 for v in m.emotional_markers.values())
        ]
        
        # Find memories with user interactions
        interaction_highlights = [
            m for m in memories
            if m.user_interactions
        ]
        
        # Find unique POIs
        unique_pois = {}
        for m in memories:
            for poi in m.poi_visited:
                poi_key = poi.get("name", "Unknown")
                if poi_key not in unique_pois:
                    unique_pois[poi_key] = m
        
        # Compile highlights
        for memory in emotional_highlights[:5]:
            highlights.append({
                "type": "emotional_moment",
                "timestamp": memory.timestamp.isoformat(),
                "location": memory.location,
                "description": f"High {max(memory.emotional_markers, key=memory.emotional_markers.get)} moment",
                "context": memory.context
            })
        
        for memory in interaction_highlights[:3]:
            highlights.append({
                "type": "user_interaction",
                "timestamp": memory.timestamp.isoformat(),
                "interaction": memory.user_interactions[0],
                "context": memory.context
            })
        
        for poi_name, memory in list(unique_pois.items())[:5]:
            highlights.append({
                "type": "poi_visit",
                "timestamp": memory.timestamp.isoformat(),
                "poi": poi_name,
                "location": memory.location,
                "narrative": memory.narrative_elements[0] if memory.narrative_elements else None
            })
        
        return highlights
    
    async def _archive_trip_memories(self, trip_id: str):
        """Archive all memories for a trip."""
        memories = self.active_memories.get(trip_id, [])
        
        if memories:
            # Store in database
            await self._store_memories_to_db(trip_id, memories)
            
            # Clear from active memory
            del self.active_memories[trip_id]
            
            # Clear from cache
            for memory in memories:
                cache_key = f"memory:{trip_id}:{memory.timestamp.timestamp()}"
                await cache_manager.delete(cache_key)
        
        logger.info(f"Archived {len(memories)} memories for trip {trip_id}")
    
    async def _load_archived_memories(
        self,
        trip_id: str,
        phase: Optional[TripPhase],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int
    ) -> List[TripMemory]:
        """Load archived memories from database."""
        # In production, implement database query
        # For now, return empty list
        return []
    
    async def _store_memories_to_db(self, trip_id: str, memories: List[TripMemory]):
        """Store memories to database."""
        # In production, implement database storage
        # This would store to a memories table
        pass
    
    def _calculate_distance(self, loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
        """Calculate distance between two locations in km."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = radians(loc1["lat"]), radians(loc1["lng"])
        lat2, lon2 = radians(loc2["lat"]), radians(loc2["lng"])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _average_location(self, locations: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate average location from multiple points."""
        if not locations:
            return {"lat": 0.0, "lng": 0.0}
        
        avg_lat = sum(loc["lat"] for loc in locations) / len(locations)
        avg_lng = sum(loc["lng"] for loc in locations) / len(locations)
        
        return {"lat": avg_lat, "lng": avg_lng}
    
    def _calculate_dominant_emotions(self, memories: List[TripMemory]) -> Dict[str, float]:
        """Calculate dominant emotions from memories."""
        emotion_totals = {}
        emotion_counts = {}
        
        for memory in memories:
            for emotion, value in memory.emotional_markers.items():
                if emotion not in emotion_totals:
                    emotion_totals[emotion] = 0
                    emotion_counts[emotion] = 0
                emotion_totals[emotion] += value
                emotion_counts[emotion] += 1
        
        # Calculate averages
        dominant_emotions = {
            emotion: emotion_totals[emotion] / emotion_counts[emotion]
            for emotion in emotion_totals
        }
        
        # Sort by value and return top 3
        sorted_emotions = sorted(dominant_emotions.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_emotions[:3])
    
    def _extract_key_narratives(self, memories: List[TripMemory]) -> List[str]:
        """Extract key narrative elements from memories."""
        # Count narrative occurrences
        narrative_counts = {}
        for memory in memories:
            for narrative in memory.narrative_elements:
                # Simple keyword extraction (in production, use NLP)
                key = narrative[:50]  # First 50 chars as key
                narrative_counts[key] = narrative_counts.get(key, 0) + 1
        
        # Return top narratives
        sorted_narratives = sorted(narrative_counts.items(), key=lambda x: x[1], reverse=True)
        return [narrative for narrative, _ in sorted_narratives[:5]]
    
    def _calculate_engagement_score(self, memories: List[TripMemory]) -> float:
        """Calculate user engagement score from memories."""
        if not memories:
            return 0.0
        
        # Factors: interactions, emotional markers, POIs visited
        interaction_count = sum(len(m.user_interactions) for m in memories)
        emotion_count = sum(len(m.emotional_markers) for m in memories)
        poi_count = sum(len(m.poi_visited) for m in memories)
        
        # Normalize by memory count
        engagement = (interaction_count * 2 + emotion_count + poi_count) / len(memories)
        
        # Cap at 10.0
        return min(engagement, 10.0)