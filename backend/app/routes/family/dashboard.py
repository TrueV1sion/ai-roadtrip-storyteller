from fastapi import APIRouter, HTTPException
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from backend.app.services.family_facilities import family_facilities
from backend.app.services.family_gamification import family_gamification
from backend.app.services.family_experience import family_experience

router = APIRouter()


@router.get("/dashboard/{trip_id}", tags=["Family"])
async def get_parent_dashboard(
    trip_id: str,
    current_location: Dict[str, float],
    include_facilities: bool = True,
    facilities_radius_km: float = 5.0
) -> Dict:
    """
    Get comprehensive dashboard for parents managing the family trip.
    
    Features:
    - Journey progress and upcoming milestones
    - Nearby family-friendly facilities
    - Active challenges and rewards
    - Schedule management
    - Safety and comfort metrics
    """
    try:
        # Get session info and progress
        session = await family_experience.get_session(trip_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Trip session not found"
            )

        # Calculate time windows and breaks
        now = datetime.now()
        next_break_time = now + timedelta(hours=2)  # Example timing
        
        # Get nearby facilities if requested
        nearby_facilities = {}
        if include_facilities:
            facilities_tasks = [
                family_facilities.find_facilities(
                    current_location,
                    facilities_radius_km,
                    facility_type
                )
                for facility_type in ["rest_stop", "restaurant", "playground"]
            ]
            
            for facility_type, facilities in zip(
                ["rest_stops", "restaurants", "playgrounds"],
                facilities_tasks
            ):
                nearby_facilities[facility_type] = await facilities

        # Get active challenges and collectibles
        challenges = await family_gamification.get_family_challenges(
            trip_id,
            current_location,
            session["preferences"].get("children_ages", [])
        )
        
        collectibles = await family_gamification.get_collectibles(
            current_location,
            facilities_radius_km
        )

        # Build schedule recommendations
        schedule = _build_schedule_recommendations(
            session,
            next_break_time,
            nearby_facilities
        )

        # Compile safety and comfort metrics
        comfort_metrics = _get_comfort_metrics(session, nearby_facilities)

        return {
            "journey_status": {
                "trip_id": trip_id,
                "started_at": session["start_time"],
                "distance_covered": session.get("distance_covered", 0),
                "points_earned": session.get("points", 0),
                "next_break": next_break_time.isoformat(),
                "estimated_arrival": "2024-02-20T18:00:00Z"  # Example
            },
            "facilities": nearby_facilities,
            "gamification": {
                "active_challenges": challenges,
                "nearby_collectibles": collectibles,
                "achievements": session.get("achievements", [])
            },
            "schedule": schedule,
            "comfort_metrics": comfort_metrics,
            "alerts": _get_important_alerts(session, nearby_facilities),
            "next_update_in": 300  # 5 minutes
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching dashboard: {str(e)}"
        )


def _build_schedule_recommendations(
    session: Dict,
    next_break: datetime,
    facilities: Dict
) -> Dict:
    """Build schedule recommendations based on journey context."""
    return {
        "current_activity": "Driving",
        "next_break": {
            "time": next_break.isoformat(),
            "duration": "30 minutes",
            "suggested_activities": [
                {
                    "type": "rest_stop",
                    "location": "Nearby Rest Area",
                    "duration": "15 min"
                },
                {
                    "type": "meal",
                    "location": "Family Restaurant",
                    "duration": "45 min"
                }
            ]
        },
        "upcoming_activities": [
            {
                "type": "landmark_visit",
                "name": "Historic Site",
                "time": "14:30",
                "duration": "1 hour"
            }
        ]
    }


def _get_comfort_metrics(session: Dict, facilities: Dict) -> Dict:
    """Calculate comfort and well-being metrics."""
    return {
        "rest_stops": {
            "last_break": "2 hours ago",
            "next_recommended": "30 minutes",
            "nearby_options": len(facilities.get("rest_stops", []))
        },
        "meal_times": {
            "last_meal": "1 hour ago",
            "next_meal_in": "2 hours",
            "nearby_restaurants": len(facilities.get("restaurants", []))
        },
        "activity_level": {
            "status": "Good",
            "last_activity": "30 minutes ago",
            "suggested_next": "Short walk at next stop"
        },
        "weather_comfort": {
            "current": "Comfortable",
            "temperature": "72°F",
            "next_rest_stop_weather": "Sunny"
        }
    }


def _get_important_alerts(session: Dict, facilities: Dict) -> List[Dict]:
    """Get priority alerts for parents."""
    return [
        {
            "type": "break_reminder",
            "priority": "high",
            "message": "Recommended break in 30 minutes",
            "action_required": False
        },
        {
            "type": "weather_alert",
            "priority": "medium",
            "message": "Rain expected in 2 hours",
            "action_required": False
        }
    ] 