"""
Enhanced MVP Voice Route with Disney Imagineering Storytelling

Quick implementation to demonstrate improved storytelling for the MVP.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

try:
    from ..services.disney_imagineering_prompts import create_imagineering_story_prompt
except ImportError:
    # Fallback if the file doesn't exist yet
    def create_imagineering_story_prompt(location, story_theme, duration):
        return f"Create an immersive Disney Imagineering-style story about {location.get('name')} with theme {story_theme}"

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mvp", tags=["mvp-enhanced"])


class VoiceRequest(BaseModel):
    user_input: str
    context: Optional[Dict[str, Any]] = None


class VoiceResponse(BaseModel):
    response: Dict[str, Any]
    audio_url: Optional[str] = None
    route: Optional[Dict[str, Any]] = None


def extract_destination(user_input: str) -> Optional[str]:
    """Extract destination from user input"""
    user_input_lower = user_input.lower()
    
    # Common patterns
    patterns = [
        "navigate to ", "navigate me to ", "take me to ", 
        "i want to go to ", "directions to ", "drive to ",
        "route to ", "go to ", "find "
    ]
    
    for pattern in patterns:
        if pattern in user_input_lower:
            destination = user_input_lower.split(pattern)[1].strip()
            # Clean up common endings
            destination = destination.replace("please", "").strip()
            destination = destination.rstrip(".,!?")
            return destination
    
    return None


@router.post("/voice-enhanced", response_model=VoiceResponse)
async def process_voice_enhanced(request: VoiceRequest):
    """
    Enhanced MVP voice endpoint with Disney Imagineering storytelling.
    
    This endpoint demonstrates the improved, longer, more immersive responses.
    """
    try:
        # Extract destination
        destination = extract_destination(request.user_input)
        
        if not destination:
            return VoiceResponse(
                response={
                    "type": "error",
                    "text": "I'd love to help you navigate! Please tell me where you'd like to go. For example, say 'Navigate to Golden Gate Bridge' or 'Take me to Central Park'.",
                    "action": "request_destination"
                }
            )
        
        # Create location context
        location = {
            "name": destination.title(),
            "type": determine_location_type(destination),
            "region": "your area"  # Would be determined by GPS in production
        }
        
        # Determine story theme based on destination
        story_theme = determine_story_theme(destination)
        
        # Create the enhanced prompt
        story_prompt = create_imagineering_story_prompt(
            location=location,
            story_theme=story_theme,
            duration="medium"  # 4-6 minutes of content
        )
        
        # Add specific instruction for immediate response
        enhanced_prompt = f"""
        {story_prompt}
        
        IMPORTANT: The user is navigating to {destination}. Begin with an acknowledgment 
        of their destination, then launch into your immersive story. Make them excited 
        about their journey from the very first words!
        """
        
        # Generate the story (using mock for MVP demo)
        # In production, this would use the actual AI client
        story = await generate_enhanced_story(enhanced_prompt, destination)
        
        # Create response
        response = {
            "type": "navigation",
            "destination": destination,
            "action": "start_navigation",
            "text": story,
            "personality": determine_personality(destination),
            "has_route": True,
            "metadata": {
                "story_style": "disney_imagineering",
                "duration_estimate": "4-6 minutes",
                "enhanced": True
            }
        }
        
        return VoiceResponse(response=response)
        
    except Exception as e:
        logger.error(f"Error in enhanced voice processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def determine_location_type(destination: str) -> str:
    """Determine the type of location from destination name"""
    destination_lower = destination.lower()
    
    if any(word in destination_lower for word in ["bridge", "golden gate", "brooklyn"]):
        return "landmark"
    elif any(word in destination_lower for word in ["park", "garden", "trail", "canyon", "mountain"]):
        return "natural"
    elif any(word in destination_lower for word in ["museum", "gallery", "theater"]):
        return "cultural"
    elif any(word in destination_lower for word in ["disney", "universal", "six flags"]):
        return "theme_park"
    elif any(word in destination_lower for word in ["beach", "ocean", "coast"]):
        return "coastal"
    else:
        return "general"


def determine_story_theme(destination: str) -> str:
    """Determine the best story theme for the destination"""
    destination_lower = destination.lower()
    
    if any(word in destination_lower for word in ["historic", "battlefield", "monument", "memorial"]):
        return "historical"
    elif any(word in destination_lower for word in ["park", "canyon", "mountain", "forest", "nature"]):
        return "natural"
    elif any(word in destination_lower for word in ["museum", "cultural", "art", "theater"]):
        return "cultural"
    elif any(word in destination_lower for word in ["haunted", "ghost", "cemetery", "asylum"]):
        return "haunted"
    elif any(word in destination_lower for word in ["observatory", "science", "lab", "research"]):
        return "scientific"
    else:
        return "general"


def determine_personality(destination: str) -> str:
    """Select the best personality for the destination"""
    destination_lower = destination.lower()
    
    if "disney" in destination_lower:
        return "Mickey Mouse"
    elif any(word in destination_lower for word in ["park", "nature", "canyon", "forest"]):
        return "Nature Guide"
    elif any(word in destination_lower for word in ["historic", "museum", "monument"]):
        return "Local Historian"
    else:
        return "Friendly Guide"


async def generate_enhanced_story(prompt: str, destination: str) -> str:
    """
    Generate an enhanced story. For MVP demo, returns crafted examples.
    In production, this would use the AI client.
    """
    
    # Demo stories showcasing the Disney Imagineering style
    demo_stories = {
        "golden gate bridge": """
        Welcome, adventurers, to one of the most magnificent journeys in San Francisco! As you approach the Golden Gate Bridge, 
        I want you to know you've chosen the perfect moment for this crossing. Do you feel that gentle breeze? That's the same 
        Pacific wind that challenged engineers for years, telling them this bridge could never be built.

        But let me take you back to a foggy morning in 1933. Picture this: Joseph Strauss, the chief engineer, standing right 
        where you are now, staring at an impossible gap. The Navy said it couldn't be done. The Southern Pacific Railroad 
        laughed at the idea. But Strauss saw something else – he saw what you're about to experience – a gateway that would 
        unite communities and inspire the world.

        As you begin your approach, notice how the towers seem to grow from the sea itself, those Art Deco masterpieces 
        rising 746 feet into the sky. That's taller than a 70-story building! And here's something magical – those towers 
        are painted in a color called International Orange. It wasn't the original choice. The Navy wanted black with yellow 
        stripes like a giant bumblebee! But architect Irving Morrow fell in love with the red lead primer and convinced 
        everyone that this warm, welcoming color would complement the natural surroundings and pierce through the fog.

        In about 30 seconds, you'll feel the bridge deck beneath you – and what a deck it is! It's suspended by cables that, 
        if laid end to end, would circle the Earth three times. Each of those main cables is made of 27,572 individual wires. 
        Imagine that – 27,572 stories of steel, each one critical to your safe passage.

        Oh, and as you cross, you're joining an exclusive club! You're one of approximately 112,000 vehicles that cross daily, 
        but here's what makes your crossing special – you're doing it with eyes wide open to the wonder. Most people rush 
        across, but you... you're savoring the magic.

        Look to your right – that's the Pacific Ocean stretching to the horizon, the same waters that have welcomed ships 
        from around the world for centuries. To your left, the San Francisco Bay sparkles like a jewel box, cradling 
        Alcatraz Island – which has its own incredible stories to tell.

        Now, here's my favorite secret about the bridge: it actually sings! On windy days, the cables create an ethereal 
        humming sound. Scientists discovered this in 2020, but locals have been whispering about the bridge's voice for 
        decades. If you crack your window just a bit, you might hear it – the Golden Gate's own symphony.

        As you reach the midpoint of your crossing, you're suspended 245 feet above the water – that's high enough to 
        stack the Statue of Liberty underneath you with room to spare! And right now, you're at the exact spot where 
        the bridge flexes the most. Yes, it moves! In strong winds, the center span can sway up to 27 feet. Don't worry 
        – that's exactly what it's designed to do. Like a dancer, the bridge moves with nature rather than against it.

        And here's something that will give you goosebumps: during construction, a safety net was installed under the bridge – 
        the first time in history for a project of this magnitude. That net saved 19 lives, and those men formed an exclusive 
        club called the "Halfway to Hell Club." Their legacy? A revolution in construction safety that protects workers to 
        this day.

        As you complete your crossing, take a moment to appreciate what you've just experienced. You've traveled the same path 
        as presidents and poets, moviestars and everyday dreamers. You've crossed not just a bridge, but an icon of human 
        achievement, a testament to the power of imagination over impossibility.

        And the most magical part? Tomorrow, the bridge will be here, waiting to inspire someone else, just as it's inspired 
        you today. As you continue your journey, carry a piece of that magic with you – the knowledge that sometimes, the 
        impossible is just waiting for someone brave enough to build it.

        Safe travels, my friend. You've just created a memory that will last a lifetime.
        """,
        
        "default": f"""
        Oh, what an incredible journey awaits you as you head toward {destination}! You've chosen a destination that holds 
        more stories than most people ever discover. Let me be your guide to the magic that awaits.

        Right now, as you begin this adventure, I want you to notice something special about this moment. The journey itself 
        is about to become part of your story. Every mile ahead is sprinkled with hidden wonders, and I'm here to help you 
        discover them all.

        {destination} isn't just a point on a map – it's a living, breathing place with a personality all its own. As you 
        travel, you're following paths carved by dreamers, builders, and everyday people who've made this route special. 
        Some came seeking adventure, others seeking peace, but all of them left a little bit of their story behind.

        The landscape you're passing through has been shaped by millions of years of patient artistry. Every hill, every 
        curve in the road has a tale to tell. And today, you get to be part of that continuing story.

        As you draw closer to {destination}, keep your eyes open for the subtle magic – the way the light changes, the way 
        the air feels different, the way the very atmosphere seems to shift as you approach somewhere special. These are 
        the details that transform a simple trip into an unforgettable journey.

        Your destination is waiting to welcome you with open arms. And between here and there? A tapestry of moments just 
        waiting to become memories. Let's discover them together!
        """
    }
    
    # Return appropriate story
    for key, story in demo_stories.items():
        if key in destination.lower():
            return story.strip()
    
    return demo_stories["default"].strip()


# Quick test endpoint
@router.get("/test-enhanced")
async def test_enhanced():
    """Test endpoint to verify enhanced storytelling is working"""
    return {
        "status": "ready",
        "message": "Enhanced Disney Imagineering storytelling is active!",
        "try": "POST to /api/mvp/voice-enhanced with user_input: 'Navigate to Golden Gate Bridge'"
    }