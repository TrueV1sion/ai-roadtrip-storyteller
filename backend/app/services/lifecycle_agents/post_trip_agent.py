"""
Post-Trip Agent - Handles trip memories, highlights generation, and sharing.

This agent manages the post-trip phase, focusing on:
- Trip memory consolidation and reflection
- Highlight generation and storytelling
- Sharing and social features
- Future trip planning inspiration
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from app.core.unified_ai_client import UnifiedAIClient
from app.services.memory.trip_memory_system import TripMemorySystem, TripPhase
from app.services.lifecycle_agents.base_lifecycle_agent import (
    BaseLifecycleAgent, LifecycleContext, LifecycleResponse, LifecycleState
)
from app.services.photo_storage_service import PhotoStorageService
from app.services.spotify_service import SpotifyService

logger = logging.getLogger(__name__)


@dataclass
class TripHighlights:
    """Structured trip highlights for post-trip experience."""
    best_stories: List[Dict[str, Any]]
    favorite_moments: List[Dict[str, Any]]
    memorable_places: List[Dict[str, Any]]
    photos_and_media: List[Dict[str, Any]]
    journey_statistics: Dict[str, Any]
    personal_growth: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    future_inspirations: List[Dict[str, Any]]


@dataclass
class ShareableContent:
    """Content prepared for sharing."""
    trip_recap: str
    highlight_reel: List[Dict[str, Any]]
    story_compilation: str
    photo_album: List[str]
    recommendations: List[str]
    travel_journal: str
    social_media_posts: List[Dict[str, Any]]


class PostTripAgent(BaseLifecycleAgent):
    """
    Specializes in post-trip memory processing and sharing.
    
    This agent helps users:
    - Reflect on their journey experiences
    - Generate comprehensive trip highlights
    - Create shareable content and memories
    - Plan future adventures based on learnings
    """
    
    def __init__(self, ai_client: UnifiedAIClient, memory_system: TripMemorySystem):
        super().__init__(ai_client, memory_system)
        
        # Initialize supporting services
        self.photo_service = PhotoStorageService()
        self.spotify_service = SpotifyService()
        
        # Post-trip specific configuration
        self.highlight_generation_limit = 50  # Top highlights to consider
        self.story_compilation_max_length = 5000  # Max chars for story compilation
        self.reflection_questions = [
            "What was your favorite moment?",
            "What surprised you most?",
            "What would you do differently?",
            "What places do you want to revisit?",
            "What new interests did you discover?"
        ]
        
        # Processing state
        self.processing_sessions = {}  # user_id -> processing_state
        
        logger.info("Post-Trip Agent initialized")
    
    def get_phase(self) -> TripPhase:
        """Return the post-trip phase."""
        return TripPhase.POST_TRIP
    
    async def initialize(self, context: LifecycleContext) -> LifecycleResponse:
        """Initialize post-trip processing."""
        try:
            await self.transition_to_state(LifecycleState.INITIALIZING, context)
            
            # Start processing session
            self.processing_sessions[context.user.id] = {
                "started": datetime.utcnow(),
                "trip_id": context.trip.id,
                "processing_stage": "initialization",
                "highlights_generated": False,
                "content_prepared": False
            }
            
            # Create initialization memory
            memory_id = await self.create_memory(context, {
                "post_trip_started": True,
                "trip_name": context.trip.name,
                "processing_started": datetime.utcnow().isoformat(),
                "trip_completed": True
            })
            
            # Generate welcome message
            welcome_message = await self._generate_post_trip_welcome(context)
            
            # Quick analysis of trip memories
            memory_count = len(await self.get_relevant_memories(context, lookback_hours=24*7))  # Week lookback
            
            await self.transition_to_state(LifecycleState.ACTIVE, context)
            
            return self.create_success_response(
                message=welcome_message,
                data={
                    "post_trip_active": True,
                    "memory_count": memory_count,
                    "processing_ready": True
                },
                memories=[memory_id],
                suggestions=[
                    "Generate my trip highlights",
                    "Create a trip recap",
                    "Show me my best moments",
                    "Help me reflect on the journey"
                ]
            )
            
        except Exception as e:
            logger.error(f"Post-trip initialization failed: {e}")
            return self.create_error_response(
                message="I'm setting up your post-trip experience. Thanks for an amazing journey!",
                error_data={"error": str(e)}
            )
    
    async def process_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Process user requests during post-trip phase."""
        try:
            # Analyze request type
            request_type = await self._analyze_post_trip_request(request, context)
            
            # Route to appropriate handler
            if request_type == "highlights_generation":
                return await self._handle_highlights_generation(request, context)
            elif request_type == "trip_recap":
                return await self._handle_trip_recap(request, context)
            elif request_type == "story_compilation":
                return await self._handle_story_compilation(request, context)
            elif request_type == "sharing_content":
                return await self._handle_sharing_content(request, context)
            elif request_type == "reflection":
                return await self._handle_reflection(request, context)
            elif request_type == "future_planning":
                return await self._handle_future_planning(request, context)
            elif request_type == "media_organization":
                return await self._handle_media_organization(request, context)
            else:
                return await self._handle_general_post_trip(request, context)
                
        except Exception as e:
            logger.error(f"Post-trip request processing failed: {e}")
            return self.create_error_response(
                message="I'm here to help you make the most of your trip memories. What would you like to do?",
                error_data={"error": str(e)}
            )
    
    async def finalize(self, context: LifecycleContext) -> LifecycleResponse:
        """Finalize post-trip processing."""
        try:
            await self.transition_to_state(LifecycleState.TRANSITIONING, context)
            
            # Generate final trip archive
            trip_archive = await self._generate_trip_archive(context)
            
            # Create completion memory
            memory_id = await self.create_memory(context, {
                "post_trip_completed": True,
                "archive_created": True,
                "completion_time": datetime.utcnow().isoformat(),
                "ready_for_archive": True
            })
            
            # Generate completion message
            completion_message = await self._generate_post_trip_completion(context, trip_archive)
            
            # Clean up processing session
            if context.user.id in self.processing_sessions:
                del self.processing_sessions[context.user.id]
            
            await self.transition_to_state(LifecycleState.COMPLETED, context)
            
            return self.create_success_response(
                message=completion_message,
                data={
                    "trip_archive": trip_archive,
                    "post_trip_completed": True,
                    "phase_transition": "archived"
                },
                memories=[memory_id],
                suggestions=[
                    "Plan another adventure",
                    "Share with friends",
                    "Explore similar destinations",
                    "Save favorite stories"
                ]
            )
            
        except Exception as e:
            logger.error(f"Post-trip finalization failed: {e}")
            return self.create_error_response(
                message="I'm wrapping up your trip memories. Thank you for sharing this journey with me!",
                error_data={"error": str(e)}
            )
    
    async def _handle_highlights_generation(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Generate comprehensive trip highlights."""
        try:
            # Get all trip memories
            memories = await self.get_relevant_memories(context, lookback_hours=24*30)  # Month lookback
            
            if not memories:
                return self.create_success_response(
                    message="I don't have enough trip memories to generate highlights. Did you have a recent journey?",
                    data={"no_memories": True},
                    suggestions=[
                        "Tell me about your recent trip",
                        "Upload photos from your journey",
                        "Share your favorite moments"
                    ]
                )
            
            # Generate highlights
            highlights = await self._generate_trip_highlights(memories, context)
            
            # Update processing session
            session = self.processing_sessions.get(context.user.id, {})
            session["highlights_generated"] = True
            session["highlights_data"] = highlights
            self.processing_sessions[context.user.id] = session
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "highlights_generated": True,
                "memory_count": len(memories),
                "highlights_count": len(highlights.best_stories) + len(highlights.favorite_moments)
            })
            
            # Generate response
            response_message = await self._generate_highlights_response(highlights, context)
            
            return self.create_success_response(
                message=response_message,
                data={
                    "highlights": {
                        "best_stories": highlights.best_stories[:5],
                        "favorite_moments": highlights.favorite_moments[:5],
                        "memorable_places": highlights.memorable_places[:5],
                        "statistics": highlights.journey_statistics
                    }
                },
                memories=[memory_id],
                suggestions=[
                    "Create a trip recap",
                    "Show me more stories",
                    "Generate shareable content",
                    "Reflect on the journey"
                ]
            )
            
        except Exception as e:
            logger.error(f"Highlights generation failed: {e}")
            return self.create_error_response(
                message="I'm working on your trip highlights. Let me gather all your memories together.",
                error_data={"error": str(e)}
            )
    
    async def _handle_trip_recap(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Generate comprehensive trip recap."""
        try:
            # Get session data
            session = self.processing_sessions.get(context.user.id, {})
            highlights = session.get("highlights_data")
            
            if not highlights:
                # Generate highlights first
                highlights_response = await self._handle_highlights_generation("generate highlights", context)
                if not highlights_response.success:
                    return highlights_response
                highlights = session.get("highlights_data")
            
            # Generate narrative trip recap
            trip_recap = await self._generate_narrative_recap(highlights, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "trip_recap_created": True,
                "recap_length": len(trip_recap),
                "includes_highlights": True
            })
            
            # Generate response
            response_message = await self._format_trip_recap_response(trip_recap, context)
            
            return self.create_success_response(
                message=response_message,
                data={"trip_recap": trip_recap},
                memories=[memory_id],
                suggestions=[
                    "Create shareable version",
                    "Add photos to recap",
                    "Share with friends",
                    "Save as journal entry"
                ]
            )
            
        except Exception as e:
            logger.error(f"Trip recap generation failed: {e}")
            return self.create_error_response(
                message="I'm creating your trip recap. This will be a beautiful summary of your journey!",
                error_data={"error": str(e)}
            )
    
    async def _handle_story_compilation(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Compile all stories from the trip."""
        try:
            # Get all story memories
            memories = await self.get_relevant_memories(context, lookback_hours=24*30)
            story_memories = [m for m in memories if "story_told" in m.context or "narrative" in m.context]
            
            if not story_memories:
                return self.create_success_response(
                    message="I don't have any stories from your trip to compile. Would you like me to generate some based on your journey?",
                    data={"no_stories": True},
                    suggestions=[
                        "Generate stories from my trip",
                        "Tell me about places I visited",
                        "Create narratives from my journey"
                    ]
                )
            
            # Compile stories
            story_compilation = await self._compile_trip_stories(story_memories, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "story_compilation_created": True,
                "stories_included": len(story_memories),
                "compilation_length": len(story_compilation)
            })
            
            # Generate response
            response_message = await self._format_story_compilation_response(story_compilation, context)
            
            return self.create_success_response(
                message=response_message,
                data={"story_compilation": story_compilation},
                memories=[memory_id],
                suggestions=[
                    "Create audio version",
                    "Share story collection",
                    "Add to travel journal",
                    "Generate more stories"
                ]
            )
            
        except Exception as e:
            logger.error(f"Story compilation failed: {e}")
            return self.create_error_response(
                message="I'm gathering all the stories from your journey. This will be a wonderful collection!",
                error_data={"error": str(e)}
            )
    
    async def _handle_sharing_content(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Generate content for sharing."""
        try:
            # Get session data
            session = self.processing_sessions.get(context.user.id, {})
            highlights = session.get("highlights_data")
            
            if not highlights:
                return self.create_success_response(
                    message="Let me generate your trip highlights first, then I can create shareable content.",
                    data={"needs_highlights": True},
                    suggestions=["Generate my trip highlights"]
                )
            
            # Generate shareable content
            shareable_content = await self._generate_shareable_content(highlights, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "shareable_content_created": True,
                "content_types": list(shareable_content.keys()),
                "ready_for_sharing": True
            })
            
            # Generate response
            response_message = await self._format_sharing_content_response(shareable_content, context)
            
            return self.create_success_response(
                message=response_message,
                data={"shareable_content": shareable_content},
                memories=[memory_id],
                suggestions=[
                    "Customize social media posts",
                    "Create photo album",
                    "Generate travel blog post",
                    "Share with specific friends"
                ]
            )
            
        except Exception as e:
            logger.error(f"Sharing content generation failed: {e}")
            return self.create_error_response(
                message="I'm creating shareable content from your trip. This will be perfect for sharing your adventure!",
                error_data={"error": str(e)}
            )
    
    async def _handle_reflection(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle reflection and personal growth analysis."""
        try:
            # Get trip memories for reflection
            memories = await self.get_relevant_memories(context, lookback_hours=24*30)
            
            # Generate reflection questions and insights
            reflection_insights = await self._generate_reflection_insights(memories, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "reflection_session": True,
                "insights_generated": True,
                "personal_growth_analyzed": True
            })
            
            # Generate response
            response_message = await self._format_reflection_response(reflection_insights, context)
            
            return self.create_success_response(
                message=response_message,
                data={"reflection_insights": reflection_insights},
                memories=[memory_id],
                suggestions=[
                    "Explore personal growth insights",
                    "Answer reflection questions",
                    "Plan future improvements",
                    "Set travel goals"
                ]
            )
            
        except Exception as e:
            logger.error(f"Reflection handling failed: {e}")
            return self.create_error_response(
                message="I'm helping you reflect on your journey. Travel often teaches us so much about ourselves!",
                error_data={"error": str(e)}
            )
    
    async def _handle_future_planning(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle future trip planning based on past experience."""
        try:
            # Get session data
            session = self.processing_sessions.get(context.user.id, {})
            highlights = session.get("highlights_data")
            
            if not highlights:
                return self.create_success_response(
                    message="Let me understand your recent trip first, then I can help plan future adventures based on what you enjoyed!",
                    data={"needs_highlights": True},
                    suggestions=["Generate my trip highlights"]
                )
            
            # Generate future planning suggestions
            future_suggestions = await self._generate_future_planning_suggestions(highlights, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "future_planning": True,
                "suggestions_generated": True,
                "based_on_past_trip": True
            })
            
            # Generate response
            response_message = await self._format_future_planning_response(future_suggestions, context)
            
            return self.create_success_response(
                message=response_message,
                data={"future_suggestions": future_suggestions},
                memories=[memory_id],
                suggestions=[
                    "Plan a similar trip",
                    "Explore new destinations",
                    "Try different travel styles",
                    "Book next adventure"
                ]
            )
            
        except Exception as e:
            logger.error(f"Future planning failed: {e}")
            return self.create_error_response(
                message="I'm excited to help you plan your next adventure based on what you loved about this trip!",
                error_data={"error": str(e)}
            )
    
    async def _handle_general_post_trip(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle general post-trip requests."""
        try:
            # Generate helpful response
            response_message = await self.ai_generate_response(
                f"Help the user with their post-trip request: {request}",
                context
            )
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "general_post_trip": True,
                "request": request
            })
            
            return self.create_success_response(
                message=response_message,
                data={"request_handled": True},
                memories=[memory_id],
                suggestions=[
                    "Generate trip highlights",
                    "Create trip recap",
                    "Compile stories",
                    "Plan future trips"
                ]
            )
            
        except Exception as e:
            logger.error(f"General post-trip handling failed: {e}")
            return self.create_error_response(
                message="I'm here to help you make the most of your trip memories. What would you like to do?",
                error_data={"error": str(e)}
            )
    
    async def _generate_trip_highlights(self, memories: List, context: LifecycleContext) -> TripHighlights:
        """Generate comprehensive trip highlights from memories."""
        # This would analyze memories and generate structured highlights
        # For now, return a mock structure
        return TripHighlights(
            best_stories=[],
            favorite_moments=[],
            memorable_places=[],
            photos_and_media=[],
            journey_statistics={},
            personal_growth={},
            recommendations=[],
            future_inspirations=[]
        )
    
    async def _generate_post_trip_welcome(self, context: LifecycleContext) -> str:
        """Generate welcome message for post-trip phase."""
        prompt = f"""
        Create a warm, reflective welcome message for someone who has just completed their road trip.
        
        Trip: {context.trip.name}
        
        The message should:
        1. Acknowledge the completion of their journey
        2. Express appreciation for sharing the adventure
        3. Offer to help process memories and highlights
        4. Maintain the supportive, friendly guide personality
        5. Set a reflective, celebratory tone
        
        Style: Warm, appreciative, excited to help preserve memories.
        """
        
        return await self.ai_generate_response(prompt, context)
    
    async def _generate_trip_archive(self, context: LifecycleContext) -> Dict[str, Any]:
        """Generate final trip archive."""
        session = self.processing_sessions.get(context.user.id, {})
        
        return {
            "trip_name": context.trip.name,
            "completion_date": datetime.utcnow().isoformat(),
            "highlights_generated": session.get("highlights_generated", False),
            "content_prepared": session.get("content_prepared", False),
            "archive_complete": True
        }
    
    # Additional helper methods would be implemented here for:
    # - _analyze_post_trip_request
    # - _generate_narrative_recap
    # - _compile_trip_stories
    # - _generate_shareable_content
    # - _generate_reflection_insights
    # - _generate_future_planning_suggestions
    # - Various formatting and response generation methods