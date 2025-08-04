"""
Asynchronous AI tasks for story generation and personality management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import Task, group, chord

from app.core.celery_app import celery_app
from app.core.database_manager import DatabaseManager
from app.services.master_orchestration_agent import MasterOrchestrationAgent
from app.services.personality_engine import PersonalityEngine
from app.services.event_journey_service import EventJourneyService
from app.core.logger import get_logger
from app.core.enhanced_cache import EnhancedCache

logger = get_logger(__name__)

class AITask(Task):
    """Base task class for AI operations."""
    
    _db_manager = None
    _master_agent = None
    _personality_engine = None
    _event_journey_service = None
    _cache = None
    
    @property
    def db_manager(self):
        if self._db_manager is None:
            self._db_manager = DatabaseManager()
        return self._db_manager
    
    @property
    def master_agent(self):
        if self._master_agent is None:
            self._master_agent = MasterOrchestrationAgent()
        return self._master_agent
    
    @property
    def personality_engine(self):
        if self._personality_engine is None:
            self._personality_engine = PersonalityEngine()
        return self._personality_engine
    
    @property
    def event_journey_service(self):
        if self._event_journey_service is None:
            self._event_journey_service = EventJourneyService()
        return self._event_journey_service
    
    @property
    def cache(self):
        if self._cache is None:
            self._cache = EnhancedCache()
        return self._cache


@celery_app.task(
    bind=True,
    base=AITask,
    name='ai.generate_story_async',
    max_retries=3,
    time_limit=120  # 2 minutes
)
def generate_story_async(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a story asynchronously for better performance.
    
    This is useful for pre-generating stories or handling complex generation
    that might take longer than typical API response times.
    """
    try:
        logger.info(f"Generating story for context: {context.get('destination')}")
        
        # Check cache first
        cache_key = f"story:{context.get('origin')}:{context.get('destination')}:{context.get('theme')}"
        cached_story = self.cache.get(cache_key)
        
        if cached_story:
            logger.info("Returning cached story")
            return cached_story
        
        # Generate story using master agent
        story_result = self.master_agent.generate_contextual_story(
            origin=context['origin'],
            destination=context['destination'],
            user_preferences=context.get('preferences', {}),
            journey_context=context.get('journey_context', {})
        )
        
        # Cache the result
        self.cache.set(cache_key, story_result, ttl=7200)  # 2 hours
        
        # If this is part of an event journey, generate additional content
        if context.get('event_id'):
            event_content = generate_event_journey_content.apply_async(
                args=[context['event_id'], story_result['story_id']]
            )
        
        return story_result
        
    except Exception as e:
        logger.error(f"Error generating story: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(
    bind=True,
    base=AITask,
    name='ai.generate_event_journey_content',
    max_retries=3
)
def generate_event_journey_content(self, event_id: str, story_id: str) -> Dict[str, Any]:
    """
    Generate event-specific journey content (anticipation, milestones, etc.).
    """
    try:
        logger.info(f"Generating event journey content for event {event_id}")
        
        # Get event details
        event_details = self.event_journey_service.get_event_details(event_id)
        
        if not event_details:
            logger.error(f"Event {event_id} not found")
            return {'success': False, 'error': 'Event not found'}
        
        # Generate content in parallel
        tasks = group(
            generate_anticipation_content.s(event_details),
            generate_journey_milestones.s(event_details),
            generate_venue_personality.s(event_details),
            generate_trivia_questions.s(event_details)
        )
        
        # Execute all tasks and collect results
        results = tasks.apply_async()
        content_results = results.get(timeout=60)
        
        # Combine results
        combined_content = {
            'event_id': event_id,
            'story_id': story_id,
            'anticipation': content_results[0],
            'milestones': content_results[1],
            'personality': content_results[2],
            'trivia': content_results[3],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Cache the combined content
        cache_key = f"event_journey:{event_id}"
        self.cache.set(cache_key, combined_content, ttl=86400)  # 24 hours
        
        return combined_content
        
    except Exception as e:
        logger.error(f"Error generating event journey content: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    base=AITask,
    name='ai.generate_anticipation_content'
)
def generate_anticipation_content(event_details: Dict[str, Any]) -> Dict[str, Any]:
    """Generate anticipation-building content for an event."""
    try:
        # This would use AI to generate exciting content about the upcoming event
        return {
            'countdown_messages': [
                f"Only {{days}} days until {event_details['name']}!",
                f"Get ready for an amazing experience at {event_details['venue']}!",
                "The excitement is building! Are you ready?"
            ],
            'fun_facts': [
                f"{event_details['venue']} hosts over 100 events per year",
                "This venue has been a landmark since 1970",
                "Over 1 million fans have experienced events here"
            ]
        }
    except Exception as e:
        logger.error(f"Error generating anticipation content: {str(e)}")
        return {}


@celery_app.task(
    base=AITask,
    name='ai.generate_journey_milestones'
)
def generate_journey_milestones(event_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate journey milestones for the event trip."""
    try:
        # This would use route data to create meaningful milestones
        return [
            {
                'distance': 0,
                'message': "Your adventure begins! Let's make this journey memorable!",
                'type': 'start'
            },
            {
                'distance': 50,
                'message': f"Halfway there! {event_details['name']} awaits!",
                'type': 'midpoint'
            },
            {
                'distance': 90,
                'message': "Almost there! Time to get excited!",
                'type': 'near_destination'
            }
        ]
    except Exception as e:
        logger.error(f"Error generating journey milestones: {str(e)}")
        return []


@celery_app.task(
    base=AITask,
    name='ai.generate_venue_personality'
)
def generate_venue_personality(event_details: Dict[str, Any]) -> Dict[str, Any]:
    """Select appropriate voice personality for the venue."""
    try:
        # Map venue type to personality
        personality_mapping = {
            'concert': 'rock_dj',
            'sports': 'sports_commentator',
            'theme_park': 'mickey',
            'theater': 'broadway_narrator'
        }
        
        event_type = event_details.get('type', 'general')
        selected_personality = personality_mapping.get(event_type, 'enthusiastic_guide')
        
        return {
            'personality': selected_personality,
            'greeting': f"Welcome to your {event_type} adventure!",
            'voice_settings': {
                'energy_level': 'high',
                'formality': 'casual',
                'humor': 'moderate'
            }
        }
    except Exception as e:
        logger.error(f"Error generating venue personality: {str(e)}")
        return {'personality': 'enthusiastic_guide'}


@celery_app.task(
    base=AITask,
    name='ai.generate_trivia_questions'
)
def generate_trivia_questions(event_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate trivia questions related to the event or venue."""
    try:
        # This would use AI to generate relevant trivia
        return [
            {
                'question': f"When was {event_details['venue']} built?",
                'options': ['1965', '1970', '1975', '1980'],
                'correct': 1,
                'explanation': "This iconic venue opened its doors in 1970!"
            },
            {
                'question': f"How many people can {event_details['venue']} hold?",
                'options': ['10,000', '15,000', '20,000', '25,000'],
                'correct': 2,
                'explanation': "The venue can accommodate 20,000 excited fans!"
            }
        ]
    except Exception as e:
        logger.error(f"Error generating trivia questions: {str(e)}")
        return []


@celery_app.task(
    bind=True,
    base=AITask,
    name='ai.update_seasonal_personalities',
    max_retries=2
)
def update_seasonal_personalities(self) -> Dict[str, Any]:
    """
    Periodic task to update seasonal voice personalities.
    """
    try:
        logger.info("Updating seasonal voice personalities")
        
        current_date = datetime.now()
        updated_personalities = []
        
        # Check for seasonal personalities to activate/deactivate
        seasonal_configs = {
            'santa': {
                'active_period': (datetime(current_date.year, 12, 1), 
                                datetime(current_date.year, 12, 26)),
                'personality': 'santa_claus'
            },
            'halloween': {
                'active_period': (datetime(current_date.year, 10, 15),
                                datetime(current_date.year, 11, 1)),
                'personality': 'spooky_narrator'
            },
            'summer': {
                'active_period': (datetime(current_date.year, 6, 1),
                                datetime(current_date.year, 8, 31)),
                'personality': 'beach_vibes_guide'
            }
        }
        
        for season, config in seasonal_configs.items():
            start_date, end_date = config['active_period']
            
            if start_date <= current_date <= end_date:
                # Activate seasonal personality
                self.personality_engine.activate_personality(config['personality'])
                updated_personalities.append({
                    'personality': config['personality'],
                    'action': 'activated',
                    'season': season
                })
            else:
                # Deactivate if outside date range
                self.personality_engine.deactivate_personality(config['personality'])
        
        logger.info(f"Updated {len(updated_personalities)} seasonal personalities")
        
        return {
            'success': True,
            'updated': updated_personalities,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating seasonal personalities: {str(e)}")
        raise self.retry(exc=e, countdown=3600)  # Retry in 1 hour


@celery_app.task(
    bind=True,
    base=AITask,
    name='ai.pregenerate_popular_routes',
    max_retries=2
)
def pregenerate_popular_routes(self) -> Dict[str, Any]:
    """
    Pre-generate stories for popular routes to improve response times.
    """
    try:
        logger.info("Pre-generating stories for popular routes")
        
        popular_routes = [
            {'origin': 'San Francisco, CA', 'destination': 'Los Angeles, CA'},
            {'origin': 'New York, NY', 'destination': 'Boston, MA'},
            {'origin': 'Chicago, IL', 'destination': 'Milwaukee, WI'},
            {'origin': 'Dallas, TX', 'destination': 'Austin, TX'},
            {'origin': 'Seattle, WA', 'destination': 'Portland, OR'},
            {'origin': 'Miami, FL', 'destination': 'Orlando, FL'},
            {'origin': 'Denver, CO', 'destination': 'Aspen, CO'},
            {'origin': 'Las Vegas, NV', 'destination': 'Los Angeles, CA'},
        ]
        
        themes = ['family', 'adventure', 'cultural', 'scenic', 'foodie']
        
        # Generate stories in parallel batches
        batch_size = 5
        generated_count = 0
        
        for i in range(0, len(popular_routes), batch_size):
            batch = popular_routes[i:i + batch_size]
            
            tasks = []
            for route in batch:
                for theme in themes:
                    context = {
                        'origin': route['origin'],
                        'destination': route['destination'],
                        'theme': theme,
                        'preferences': {'theme': theme}
                    }
                    tasks.append(generate_story_async.s(context))
            
            # Execute batch
            group_result = group(tasks).apply_async()
            results = group_result.get(timeout=300)  # 5 minutes
            
            generated_count += len(results)
        
        logger.info(f"Pre-generated {generated_count} stories")
        
        return {
            'success': True,
            'generated_count': generated_count,
            'routes': len(popular_routes),
            'themes': len(themes)
        }
        
    except Exception as e:
        logger.error(f"Error pre-generating routes: {str(e)}")
        raise self.retry(exc=e, countdown=3600)