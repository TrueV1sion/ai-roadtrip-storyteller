"""
Contextual Awareness Agent - Provides situational awareness and proactive suggestions

This agent monitors journey context and proactively identifies opportunities,
needs, and relevant information based on time, location, and user state.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from ..core.unified_ai_client import UnifiedAIClient

logger = logging.getLogger(__name__)


class ContextType(Enum):
    TIME_BASED = "time_based"
    LOCATION_BASED = "location_based" 
    JOURNEY_STAGE = "journey_stage"
    WEATHER_BASED = "weather_based"
    USER_STATE = "user_state"
    GENERAL = "general"


class SuggestionPriority(Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class JourneyStage(Enum):
    STARTING = "starting"
    EARLY_JOURNEY = "early_journey"
    MID_JOURNEY = "mid_journey"
    APPROACHING_DESTINATION = "approaching_destination"
    ARRIVED = "arrived"


class ContextualAwarenessAgent:
    """
    Agent that maintains awareness of journey context and provides proactive assistance.
    
    This agent:
    - Monitors time-based needs (meals, breaks, fuel)
    - Tracks journey progress and milestones
    - Considers weather and environmental factors
    - Anticipates user needs based on patterns
    - Provides timely, relevant suggestions
    """
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        logger.info("Contextual Awareness Agent initialized")
    
    async def assess_situation(self, journey_context: Dict[str, Any],
                             conversation_history: str,
                             assessment_focus: str = "general") -> Dict[str, Any]:
        """
        Assess current situation and provide contextual suggestions.
        
        Args:
            journey_context: Current journey information
            conversation_history: Recent conversation context
            assessment_focus: Specific area to focus on
            
        Returns:
            Dictionary containing suggestions and contextual insights
        """
        try:
            # Analyze multiple context dimensions
            time_context = self._analyze_time_context(journey_context)
            location_context = await self._analyze_location_context(journey_context)
            journey_stage = self._determine_journey_stage(journey_context)
            user_state = await self._infer_user_state(journey_context, conversation_history)
            
            # Generate contextual insights
            insights = await self._generate_contextual_insights(
                time_context, location_context, journey_stage, user_state, journey_context
            )
            
            # Generate proactive suggestions
            suggestions = await self._generate_suggestions(
                insights, journey_context, assessment_focus
            )
            
            # Prioritize suggestions
            prioritized_suggestions = self._prioritize_suggestions(suggestions, journey_context)
            
            return {
                "suggestions": prioritized_suggestions,
                "context_analysis": {
                    "time_factors": time_context,
                    "location_factors": location_context,
                    "journey_stage": journey_stage.value,
                    "user_state": user_state
                },
                "insights": insights,
                "proactive_alerts": self._generate_proactive_alerts(insights, journey_context)
            }
            
        except Exception as e:
            logger.error(f"Situation assessment failed: {e}")
            return self._create_fallback_assessment()
    
    def _analyze_time_context(self, journey_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze time-based contextual factors"""
        
        current_time = journey_context.get('current_time', datetime.now())
        journey_start = journey_context.get('journey_start_time', current_time)
        
        # Calculate journey duration
        journey_duration = (current_time - journey_start).total_seconds() / 3600  # hours
        
        # Determine time-based needs
        hour = current_time.hour
        
        time_factors = {
            "current_hour": hour,
            "journey_duration_hours": journey_duration,
            "time_of_day": self._categorize_time_of_day(hour),
            "meal_time": self._is_meal_time(hour),
            "break_needed": journey_duration > 2 and journey_duration % 2 < 0.5,
            "fatigue_risk": self._assess_fatigue_risk(hour, journey_duration),
            "sunset_approaching": self._check_sunset_approaching(current_time),
            "business_hours": 9 <= hour <= 17
        }
        
        return time_factors
    
    async def _analyze_location_context(self, journey_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze location-based contextual factors"""
        
        current_location = journey_context.get('current_location', {})
        route_info = journey_context.get('route_info', {})
        
        location_factors = {
            "location_type": current_location.get('type', 'unknown'),
            "urban_rural": self._determine_area_type(current_location),
            "services_nearby": await self._check_nearby_services(current_location),
            "next_services_distance": self._find_next_services_distance(route_info),
            "interesting_nearby": await self._find_interesting_locations(current_location),
            "elevation_change": route_info.get('elevation_change', 'minimal'),
            "scenic_area": self._is_scenic_area(current_location)
        }
        
        return location_factors
    
    def _determine_journey_stage(self, journey_context: Dict[str, Any]) -> JourneyStage:
        """Determine current stage of journey"""
        
        route_info = journey_context.get('route_info', {})
        total_distance = route_info.get('total_distance_miles', 100)
        remaining_distance = route_info.get('remaining_distance_miles', 50)
        
        if remaining_distance > total_distance * 0.9:
            return JourneyStage.STARTING
        elif remaining_distance > total_distance * 0.6:
            return JourneyStage.EARLY_JOURNEY
        elif remaining_distance > total_distance * 0.2:
            return JourneyStage.MID_JOURNEY
        elif remaining_distance > 5:
            return JourneyStage.APPROACHING_DESTINATION
        else:
            return JourneyStage.ARRIVED
    
    async def _infer_user_state(self, journey_context: Dict[str, Any],
                               conversation_history: str) -> Dict[str, Any]:
        """Infer user's current state from context and conversation"""
        
        inference_prompt = f"""
        Based on this journey context and conversation, infer the user's current state:
        
        Journey duration: {journey_context.get('journey_duration_hours', 0):.1f} hours
        Current time: {journey_context.get('current_time', datetime.now()).strftime('%I:%M %p')}
        Weather: {journey_context.get('weather', {}).get('conditions', 'clear')}
        Recent conversation: {conversation_history[-500:] if conversation_history else 'No recent conversation'}
        
        Assess:
        1. Energy level (energetic, normal, tired)
        2. Engagement level (highly engaged, moderate, low)
        3. Mood (positive, neutral, stressed)
        4. Needs (hungry, thirsty, restroom, rest, entertainment)
        5. Interest areas based on conversation
        
        Consider subtle cues in the conversation and journey patterns.
        """
        
        try:
            response = await self.ai_client.generate_structured_response(
                inference_prompt, expected_format="user_state"
            )
            
            return {
                "energy_level": response.get("energy_level", "normal"),
                "engagement_level": response.get("engagement_level", "moderate"),
                "mood": response.get("mood", "neutral"),
                "potential_needs": response.get("needs", []),
                "interests_shown": response.get("interests", [])
            }
            
        except Exception as e:
            logger.error(f"User state inference failed: {e}")
            return {
                "energy_level": "normal",
                "engagement_level": "moderate",
                "mood": "neutral",
                "potential_needs": [],
                "interests_shown": []
            }
    
    async def _generate_contextual_insights(self, time_context: Dict[str, Any],
                                          location_context: Dict[str, Any],
                                          journey_stage: JourneyStage,
                                          user_state: Dict[str, Any],
                                          journey_context: Dict[str, Any]) -> List[str]:
        """Generate insights from contextual analysis"""
        
        insights = []
        
        # Time-based insights
        if time_context['meal_time']:
            meal_type = self._get_meal_type(time_context['current_hour'])
            insights.append(f"It's {meal_type} time - might be good to find a place to eat")
        
        if time_context['break_needed']:
            insights.append("You've been driving for a while - a short break would be refreshing")
        
        if time_context['fatigue_risk'] == 'high':
            insights.append("Long journey during challenging hours - stay alert and consider rest")
        
        # Location-based insights
        if location_context['next_services_distance'] > 30:
            insights.append("Limited services ahead for the next 30+ miles")
        
        if location_context['scenic_area']:
            insights.append("You're in a scenic area with potential photo opportunities")
        
        # Journey stage insights
        if journey_stage == JourneyStage.APPROACHING_DESTINATION:
            insights.append("Approaching your destination - prepare for arrival")
        
        # User state insights
        if "hungry" in user_state.get('potential_needs', []):
            insights.append("You might be getting hungry based on the time and journey duration")
        
        # Weather insights
        weather = journey_context.get('weather', {})
        if weather.get('conditions') in ['rain', 'snow']:
            insights.append(f"Current weather: {weather['conditions']} - drive carefully")
        
        return insights
    
    async def _generate_suggestions(self, insights: List[str],
                                  journey_context: Dict[str, Any],
                                  focus_area: str) -> List[Dict[str, Any]]:
        """Generate proactive suggestions based on insights"""
        
        suggestions = []
        
        # Generate suggestions for each insight
        for insight in insights:
            if "meal time" in insight.lower():
                suggestions.extend(await self._generate_meal_suggestions(journey_context))
            elif "break" in insight.lower():
                suggestions.extend(await self._generate_break_suggestions(journey_context))
            elif "limited services" in insight.lower():
                suggestions.extend(await self._generate_service_suggestions(journey_context))
            elif "scenic" in insight.lower():
                suggestions.extend(await self._generate_scenic_suggestions(journey_context))
            elif "destination" in insight.lower():
                suggestions.extend(await self._generate_arrival_suggestions(journey_context))
        
        # Add general suggestions based on context
        if focus_area == "entertainment":
            suggestions.extend(await self._generate_entertainment_suggestions(journey_context))
        
        return suggestions
    
    async def _generate_meal_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate meal-related suggestions"""
        
        current_location = journey_context.get('current_location', {})
        meal_type = self._get_meal_type(journey_context.get('current_time', datetime.now()).hour)
        
        return [
            {
                "type": "meal_suggestion",
                "priority": SuggestionPriority.HIGH.value,
                "suggestion": f"Find a place for {meal_type}",
                "reasoning": f"It's {meal_type} time and there are good options nearby",
                "action": {
                    "type": "search_restaurants",
                    "meal_type": meal_type,
                    "location": current_location
                }
            }
        ]
    
    async def _generate_break_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate break-related suggestions"""
        
        return [
            {
                "type": "break_suggestion",
                "priority": SuggestionPriority.HIGH.value,
                "suggestion": "Take a 10-minute rest break",
                "reasoning": "You've been driving for over 2 hours",
                "action": {
                    "type": "find_rest_area",
                    "duration_minutes": 10
                }
            },
            {
                "type": "break_suggestion", 
                "priority": SuggestionPriority.MEDIUM.value,
                "suggestion": "Stretch your legs at the next scenic viewpoint",
                "reasoning": "Combine a break with a nice view",
                "action": {
                    "type": "find_scenic_stop"
                }
            }
        ]
    
    async def _generate_service_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate service-related suggestions"""
        
        vehicle_info = journey_context.get('vehicle_info', {})
        fuel_level = vehicle_info.get('fuel_level_percent', 50)
        
        suggestions = []
        
        if fuel_level < 30:
            suggestions.append({
                "type": "fuel_suggestion",
                "priority": SuggestionPriority.URGENT.value,
                "suggestion": "Refuel soon - limited stations ahead",
                "reasoning": "Fuel level low with limited services for next 30+ miles",
                "action": {
                    "type": "find_gas_station",
                    "urgency": "high"
                }
            })
        
        return suggestions
    
    async def _generate_scenic_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate scenic-related suggestions"""
        
        return [
            {
                "type": "scenic_suggestion",
                "priority": SuggestionPriority.LOW.value,
                "suggestion": "Photo opportunity at scenic overlook ahead",
                "reasoning": "Beautiful vista point coming up in 2 miles",
                "action": {
                    "type": "add_scenic_stop",
                    "duration_minutes": 5
                }
            }
        ]
    
    async def _generate_arrival_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate arrival-related suggestions"""
        
        return [
            {
                "type": "arrival_suggestion",
                "priority": SuggestionPriority.MEDIUM.value,
                "suggestion": "Review parking options near destination",
                "reasoning": "Arriving soon - good to plan parking",
                "action": {
                    "type": "search_parking"
                }
            },
            {
                "type": "arrival_suggestion",
                "priority": SuggestionPriority.LOW.value,
                "suggestion": "Check destination hours and entry requirements",
                "reasoning": "Ensure smooth arrival experience",
                "action": {
                    "type": "check_destination_info"
                }
            }
        ]
    
    async def _generate_entertainment_suggestions(self, journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate entertainment-related suggestions"""
        
        return [
            {
                "type": "entertainment_suggestion",
                "priority": SuggestionPriority.LOW.value,
                "suggestion": "Try a road trip trivia game",
                "reasoning": "Keep everyone engaged during this stretch",
                "action": {
                    "type": "start_trivia_game",
                    "theme": "local_history"
                }
            }
        ]
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]],
                              journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize suggestions based on context and urgency"""
        
        # Sort by priority
        priority_order = {
            SuggestionPriority.URGENT.value: 0,
            SuggestionPriority.HIGH.value: 1,
            SuggestionPriority.MEDIUM.value: 2,
            SuggestionPriority.LOW.value: 3
        }
        
        sorted_suggestions = sorted(
            suggestions,
            key=lambda x: priority_order.get(x.get('priority', 'low'), 3)
        )
        
        # Limit to top 5 suggestions
        return sorted_suggestions[:5]
    
    def _generate_proactive_alerts(self, insights: List[str],
                                 journey_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate proactive alerts for important conditions"""
        
        alerts = []
        
        # Check for critical conditions
        vehicle_info = journey_context.get('vehicle_info', {})
        fuel_level = vehicle_info.get('fuel_level_percent', 50)
        
        if fuel_level < 20:
            alerts.append({
                "type": "fuel_critical",
                "message": "Low fuel warning - find station immediately",
                "severity": "high"
            })
        
        weather = journey_context.get('weather', {})
        if weather.get('conditions') in ['severe_storm', 'blizzard']:
            alerts.append({
                "type": "weather_warning",
                "message": f"Severe weather alert: {weather['conditions']}",
                "severity": "high"
            })
        
        return alerts
    
    # Helper methods
    
    def _categorize_time_of_day(self, hour: int) -> str:
        """Categorize time of day"""
        if 5 <= hour < 9:
            return "early_morning"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "midday"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening"
        elif 20 <= hour < 23:
            return "night"
        else:
            return "late_night"
    
    def _is_meal_time(self, hour: int) -> bool:
        """Check if current time is a typical meal time"""
        breakfast = 6 <= hour <= 9
        lunch = 11 <= hour <= 14
        dinner = 17 <= hour <= 20
        return breakfast or lunch or dinner
    
    def _get_meal_type(self, hour: int) -> str:
        """Get type of meal based on hour"""
        if 6 <= hour <= 9:
            return "breakfast"
        elif 11 <= hour <= 14:
            return "lunch"
        elif 17 <= hour <= 20:
            return "dinner"
        else:
            return "snack"
    
    def _assess_fatigue_risk(self, hour: int, journey_hours: float) -> str:
        """Assess driver fatigue risk"""
        if journey_hours > 4:
            return "high"
        elif journey_hours > 2 and (hour < 6 or hour > 22):
            return "high"
        elif journey_hours > 2:
            return "medium"
        else:
            return "low"
    
    def _check_sunset_approaching(self, current_time: datetime) -> bool:
        """Check if sunset is approaching (simplified)"""
        hour = current_time.hour
        month = current_time.month
        
        # Simplified sunset times by season
        if 3 <= month <= 9:  # Spring/Summer
            sunset_hour = 19
        else:  # Fall/Winter
            sunset_hour = 17
        
        return sunset_hour - 1 <= hour <= sunset_hour + 1
    
    def _determine_area_type(self, location: Dict[str, Any]) -> str:
        """Determine if area is urban, suburban, or rural"""
        # Placeholder - would use actual location data
        return location.get('area_type', 'suburban')
    
    async def _check_nearby_services(self, location: Dict[str, Any]) -> Dict[str, bool]:
        """Check what services are available nearby"""
        # Placeholder - would query actual services
        return {
            "gas_stations": True,
            "restaurants": True,
            "rest_areas": False,
            "hotels": True,
            "attractions": False
        }
    
    def _find_next_services_distance(self, route_info: Dict[str, Any]) -> float:
        """Find distance to next service area"""
        # Placeholder - would analyze route
        return route_info.get('next_services_miles', 15.0)
    
    async def _find_interesting_locations(self, location: Dict[str, Any]) -> List[str]:
        """Find interesting locations nearby"""
        # Placeholder - would query POI database
        return ["Historic Downtown", "State Park", "Scenic Overlook"]
    
    def _is_scenic_area(self, location: Dict[str, Any]) -> bool:
        """Determine if current area is scenic"""
        # Placeholder - would use actual scenic rating data
        return location.get('scenic_rating', 3) > 3
    
    def _create_fallback_assessment(self) -> Dict[str, Any]:
        """Create fallback assessment when analysis fails"""
        return {
            "suggestions": [
                {
                    "type": "general",
                    "priority": "medium",
                    "suggestion": "Enjoy your journey!",
                    "reasoning": "Keep having a great trip",
                    "action": {}
                }
            ],
            "context_analysis": {},
            "insights": ["Continue enjoying your road trip"],
            "proactive_alerts": []
        }