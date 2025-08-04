from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from datetime import datetime

from app.core.ai_client import ai_client
from app.services.music_service import music_service
from app.services.tts_service import tts_synthesizer

router = APIRouter()

@router.post("/family-journey", tags=["Experience"])
async def get_family_journey(payload: Dict):
    """
    Generate a family-friendly journey experience that combines:
    - Age-appropriate stories about locations
    - Educational trivia tied to the route
    - Kid-friendly music playlists
    - Gamified progress tracking
    - Points of interest for families
    
    Expected payload:
    {
        "trip_id": "abc123",
        "current_location": {
            "latitude": 12.34,
            "longitude": 56.78
        },
        "next_stop": {
            "latitude": 12.35,
            "longitude": 56.79
        },
        "children_ages": [5, 8],  # Optional
        "interests": ["nature", "history", "animals"],
        "time_until_stop": 30  # minutes
    }
    """
    try:
        # Validate required fields
        for field in ["trip_id", "current_location", "next_stop"]:
            if field not in payload:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )

        # Generate age-appropriate story about the upcoming location
        story = await ai_client.generate_story_with_session(
            payload["trip_id"],
            payload["next_stop"],
            payload.get("interests", ["nature", "history"]),
            {"children_ages": payload.get("children_ages", [5, 8])}
        )

        # Get kid-friendly music playlist
        playlist = music_service.get_playlist(
            time_of_day=datetime.now().strftime("%H:%M"),
            location=payload["current_location"],
            mood="family"
        )

        # Generate audio for the story
        audio_bytes = tts_synthesizer.synthesize(story)

        # Calculate journey progress and rewards
        progress = {
            "distance_covered": 0,  # To be calculated
            "points_earned": 100,
            "next_milestone": "30 minutes to next stop!",
            "achievements": [
                "Road Trip Explorer",
                "History Detective"
            ]
        }

        # Get nearby family-friendly points of interest
        poi = [
            {
                "name": "Family Restaurant",
                "type": "food",
                "kid_friendly": True,
                "distance": "5 min detour"
            },
            {
                "name": "Adventure Park",
                "type": "activity",
                "kid_friendly": True,
                "distance": "10 min detour"
            }
        ]

        # Get age-appropriate trivia for the current segment
        trivia = [
            {
                "question": "What type of trees are we passing?",
                "options": ["Pine", "Oak", "Maple"],
                "correct": "Pine",
                "fun_fact": "Pine trees stay green all year round!"
            },
            {
                "question": "What state are we entering?",
                "options": ["Texas", "Oklahoma", "Kansas"],
                "correct": "Texas",
                "fun_fact": "Texas is the second largest state!"
            }
        ]

        return {
            "story": {
                "text": story,
                "audio": audio_bytes
            },
            "playlist": playlist,
            "progress": progress,
            "points_of_interest": poi,
            "trivia": trivia,
            "next_update_in": 15  # minutes
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating family journey: {str(e)}"
        ) 