"""
Social sharing routes for journey videos and content
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.core.database_manager import get_db
from backend.app.core.auth import get_current_user
from backend.app.models import User
from backend.app.services.journey_video_service import journey_video_service
from backend.app.core.logger import logger


router = APIRouter(prefix="/api/social", tags=["social"])


@router.post("/journey-video/create")
async def create_journey_video(
    trip_id: str,
    options: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a shareable journey video
    
    Options:
    - duration: Video duration in seconds (30, 60, 90)
    - include_map: Include animated map
    - include_photos: Include user photos
    - include_stats: Include trip statistics
    - music_style: Background music style (upbeat, relaxed, epic, nostalgic)
    """
    try:
        # Validate options
        if options:
            duration = options.get('duration', 60)
            if duration not in [30, 60, 90]:
                raise HTTPException(400, "Duration must be 30, 60, or 90 seconds")
            
            music_style = options.get('music_style', 'upbeat')
            if music_style not in ['upbeat', 'relaxed', 'epic', 'nostalgic']:
                raise HTTPException(400, "Invalid music style")
        
        # Check if video already exists
        from backend.app.core.cache import cache_manager
        cached_video = await cache_manager.get(f"journey_video:{trip_id}")
        if cached_video:
            return {
                "status": "ready",
                "video": cached_video
            }
        
        # Start video generation in background
        background_tasks.add_task(
            journey_video_service.create_journey_video,
            trip_id,
            current_user.id,
            options
        )
        
        return {
            "status": "processing",
            "message": "Video generation started. Check status in 30-60 seconds.",
            "status_url": f"/api/social/journey-video/status/{trip_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating journey video: {str(e)}")
        raise HTTPException(500, "Failed to create journey video")


@router.get("/journey-video/status/{trip_id}")
async def get_video_status(
    trip_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check journey video generation status"""
    try:
        from backend.app.core.cache import cache_manager
        video_data = await cache_manager.get(f"journey_video:{trip_id}")
        
        if video_data:
            return {
                "status": "ready",
                "video": video_data
            }
        else:
            return {
                "status": "processing",
                "message": "Video is still being generated"
            }
            
    except Exception as e:
        logger.error(f"Error checking video status: {str(e)}")
        raise HTTPException(500, "Failed to check video status")


@router.post("/share/prepare")
async def prepare_share_content(
    trip_id: str,
    platform: str,
    include_video: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Prepare platform-specific share content
    
    Platforms: twitter, facebook, instagram, tiktok, whatsapp
    """
    if platform not in ['twitter', 'facebook', 'instagram', 'tiktok', 'whatsapp']:
        raise HTTPException(400, "Invalid platform")
    
    try:
        # Get trip data
        from backend.app.models import Trip
        trip = db.query(Trip).filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id
        ).first()
        
        if not trip:
            raise HTTPException(404, "Trip not found")
        
        # Platform-specific content
        content = {
            "platform": platform,
            "trip_id": trip_id
        }
        
        if platform == "twitter":
            content.update({
                "text": f"Just completed an amazing road trip from {trip.origin} to {trip.destination}! "
                       f"{trip.distance_miles} miles of incredible memories. Created with @RoadTripAI",
                "hashtags": ["RoadTrip", "Travel", "AITravel", "Adventure"],
                "max_length": 280,
                "media_type": "video" if include_video else "images"
            })
            
        elif platform == "facebook":
            content.update({
                "caption": f"🚗 Road Trip Adventure: {trip.origin} to {trip.destination}\n\n"
                          f"Just completed an incredible {trip.distance_miles} mile journey filled with "
                          f"unforgettable moments. From scenic stops to hidden gems, every mile told a story.\n\n"
                          f"Created with AI Road Trip Storyteller - transform your journeys into memories!",
                "media_type": "video" if include_video else "album"
            })
            
        elif platform == "instagram":
            content.update({
                "caption": f"From {trip.origin} to {trip.destination} 🚗✨\n\n"
                          f"📍 {trip.distance_miles} miles\n"
                          f"⏱️ {trip.duration_hours} hours\n"
                          f"📸 Countless memories\n\n"
                          f"Every journey tells a story. What's yours?\n\n"
                          f"#RoadTrip #Travel #Adventure #AITravel #Wanderlust",
                "media_type": "reel" if include_video else "carousel",
                "aspect_ratio": "9:16"  # Vertical for reels/stories
            })
            
        elif platform == "tiktok":
            content.update({
                "caption": f"POV: You just discovered the best way to road trip 🚗 "
                          f"#{trip.origin.replace(' ', '')} to #{trip.destination.replace(' ', '')} "
                          f"#RoadTrip #Travel #FYP #AITravel",
                "media_type": "video",
                "duration": 30,  # TikTok prefers shorter videos
                "trending_audio": "suggested_audio_id"
            })
            
        elif platform == "whatsapp":
            content.update({
                "message": f"Check out my road trip from {trip.origin} to {trip.destination}! "
                          f"🚗 {trip.distance_miles} miles of adventure. "
                          f"See the journey video here: ",
                "media_type": "link"
            })
        
        # Add video URL if available
        if include_video:
            from backend.app.core.cache import cache_manager
            video_data = await cache_manager.get(f"journey_video:{trip_id}")
            if video_data:
                content["video_url"] = video_data["video_url"]
                content["thumbnail_url"] = video_data["thumbnail_url"]
        
        return content
        
    except Exception as e:
        logger.error(f"Error preparing share content: {str(e)}")
        raise HTTPException(500, "Failed to prepare share content")


@router.post("/share/track")
async def track_share(
    trip_id: str,
    platform: str,
    shared: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Track social media shares for analytics"""
    try:
        # Log share event
        logger.info(f"User {current_user.id} shared trip {trip_id} on {platform}")
        
        # In production, would save to analytics database
        # Could also trigger rewards/achievements
        
        return {
            "status": "tracked",
            "message": "Share tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error tracking share: {str(e)}")
        # Don't fail the request if tracking fails
        return {
            "status": "error",
            "message": "Share tracking failed but share completed"
        }


@router.get("/templates")
async def get_share_templates(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get pre-made templates for social sharing"""
    return {
        "templates": [
            {
                "id": "adventure",
                "name": "Adventure",
                "preview": "🚗 Epic road trip adventure from [ORIGIN] to [DESTINATION]!",
                "platforms": ["twitter", "facebook", "instagram"]
            },
            {
                "id": "family",
                "name": "Family Trip",
                "preview": "👨‍👩‍👧‍👦 Making memories on our family road trip!",
                "platforms": ["facebook", "instagram", "whatsapp"]
            },
            {
                "id": "scenic",
                "name": "Scenic Journey",
                "preview": "📸 Breathtaking views on the road from [ORIGIN] to [DESTINATION]",
                "platforms": ["instagram", "twitter"]
            },
            {
                "id": "foodie",
                "name": "Foodie Adventure",
                "preview": "🍔 Tasting our way from [ORIGIN] to [DESTINATION]!",
                "platforms": ["instagram", "tiktok", "facebook"]
            }
        ]
    }


@router.get("/trending")
async def get_trending_content(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get trending routes and content for inspiration"""
    return {
        "trending_routes": [
            {
                "route": "LA to Vegas",
                "shares": 1250,
                "hashtags": ["RoadToVegas", "DesertDrive"],
                "season": "Year-round"
            },
            {
                "route": "Pacific Coast Highway",
                "shares": 3400,
                "hashtags": ["PCH", "CaliforniaCoast", "BigSur"],
                "season": "Summer"
            },
            {
                "route": "Route 66",
                "shares": 2100,
                "hashtags": ["Route66", "MotherRoad", "Americana"],
                "season": "Spring/Fall"
            }
        ],
        "trending_hashtags": [
            "#RoadTrip2025",
            "#AITravel",
            "#JourneyStories",
            "#TravelWithAI",
            "#RoadTripMemories"
        ],
        "viral_features": [
            "Time-lapse map animations",
            "Voice personality highlights",
            "Booking montages",
            "Sunset compilations"
        ]
    }