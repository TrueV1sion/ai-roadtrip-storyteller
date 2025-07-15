"""
MVP Voice Assistant Route - REAL implementation with Google AI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import os
from google.cloud import aiplatform
from google.cloud import texttospeech
from google.cloud import storage
import googlemaps
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mvp", tags=["MVP Voice"])

# Initialize Google Cloud clients
project_id = os.getenv("GOOGLE_AI_PROJECT_ID", "roadtrip-460720")
location = os.getenv("GOOGLE_AI_LOCATION", "us-central1")
bucket_name = os.getenv("GCS_BUCKET_NAME", "roadtrip-mvp-audio")
maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Log configuration
logger.info(f"Configuration loaded:")
logger.info(f"  Project ID: {project_id}")
logger.info(f"  Maps API Key: {'Set' if maps_api_key else 'Not Set'} (length: {len(maps_api_key)})")

# Initialize clients with lazy loading to avoid startup errors
tts_client = None
storage_client = None
gmaps = None

def init_clients():
    """Initialize Google Cloud clients when needed"""
    global tts_client, storage_client, gmaps
    
    if gmaps is None and maps_api_key:
        logger.info(f"Initializing Google Maps client with key: {maps_api_key[:10]}...")
        gmaps = googlemaps.Client(key=maps_api_key)
    elif not maps_api_key:
        logger.warning("No Google Maps API key found in environment")
    
    try:
        if tts_client is None:
            tts_client = texttospeech.TextToSpeechClient()
        if storage_client is None:
            storage_client = storage.Client()
        aiplatform.init(project=project_id, location=location)
    except Exception as e:
        logger.warning(f"Could not initialize Google Cloud clients: {e}")
        # Continue without these services


class MVPVoiceRequest(BaseModel):
    """Voice request for MVP"""
    user_input: str = Field(..., description="User's voice command as text")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current context (location, etc)")


class MVPVoiceResponse(BaseModel):
    """Voice response for MVP"""
    response: Dict[str, Any] = Field(..., description="Response data")
    audio_url: Optional[str] = Field(None, description="URL to audio file if TTS was generated")
    route: Optional[Dict[str, Any]] = Field(None, description="Navigation route with directions")


def generate_story_with_ai(prompt: str) -> str:
    """Generate story using Vertex AI with enhanced fallbacks"""
    try:
        init_clients()
        model = aiplatform.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"AI generation error: {str(e)}")
        # Enhanced location-specific fallbacks
        prompt_lower = prompt.lower()
        
        # Detroit
        if "detroit" in prompt_lower:
            stories = [
                "Welcome to the Motor City! Detroit gave birth to the American auto industry and Motown music. As you explore, you'll discover a city reinventing itself with innovative art, thriving neighborhoods, and the spirit that built America's industrial might.",
                "Detroit awaits with incredible stories! Home to the Henry Ford Museum and the birthplace of techno music, this resilient city showcases stunning Art Deco architecture and a food scene that rivals any major metropolis.",
                "Get ready to explore Detroit, where the Motown sound was born! From Berry Gordy's Hitsville U.S.A. to the magnificent Guardian Building, every corner tells a story of innovation, music, and American determination."
            ]
            import random
            return random.choice(stories)
        
        # Chicago
        elif "chicago" in prompt_lower:
            return "The Windy City beckons! Chicago's stunning skyline, world-class museums, and deep-dish pizza await. From the magnificent Mile to Millennium Park, you're about to experience one of America's greatest cities."
        
        # Nashville
        elif "nashville" in prompt_lower:
            return "Music City calls! Nashville is where country music lives and breathes. From the Grand Ole Opry to Broadway's honky-tonks, plus amazing hot chicken and Southern hospitality, your journey promises unforgettable melodies and flavors."
        
        # Miami
        elif "miami" in prompt_lower:
            return "Welcome to the Magic City! Miami's Art Deco architecture, pristine beaches, and vibrant Latin culture create an atmosphere unlike anywhere else. From South Beach to Little Havana, prepare for sunshine and salsa!"
        
        # Las Vegas
        elif "las vegas" in prompt_lower or "vegas" in prompt_lower:
            return "Viva Las Vegas! The Entertainment Capital awaits with dazzling lights, world-class shows, and endless excitement. From the Strip's grand casinos to stunning desert landscapes, your desert oasis adventure begins!"
        
        # New York
        elif "new york" in prompt_lower or "manhattan" in prompt_lower:
            return "The Big Apple awaits! From Times Square's electric energy to Central Park's green oasis, New York City offers endless discoveries. Broadway shows, world-class museums, and incredible food from every corner of the globe!"
        
        # San Francisco
        elif "golden gate" in prompt_lower or "san francisco" in prompt_lower:
            return "The Golden Gate Bridge awaits! This iconic marvel spans 1.7 miles across the San Francisco Bay. As you approach, you'll see why it's called the most photographed bridge in the world!"
        
        # Los Angeles/Disneyland
        elif "disneyland" in prompt_lower:
            return "Get ready for the Happiest Place on Earth! Disneyland awaits with magical adventures around every corner. Your journey to the Magic Kingdom is about to begin!"
        elif "los angeles" in prompt_lower or " la " in prompt_lower:
            return "Welcome to the City of Angels! From Hollywood's glamour to Santa Monica's beaches, LA's diverse neighborhoods each tell their own story. Prepare for perfect weather, amazing food, and star-studded adventures!"
        
        # National Parks
        elif "yosemite" in prompt_lower:
            return "Yosemite's majesty awaits! Prepare to witness towering granite cliffs, ancient giant sequoias, and waterfalls that will take your breath away. John Muir called it 'the grandest of all temples of nature'!"
        elif "grand canyon" in prompt_lower:
            return "The Grand Canyon beckons! You're about to witness 2 billion years of Earth's history carved into colorful rock layers. This natural wonder will leave you speechless with its immense scale and beauty."
        elif "yellowstone" in prompt_lower:
            return "America's first national park awaits! Yellowstone's geysers, hot springs, and abundant wildlife create a wonderland like nowhere else on Earth. Keep your eyes peeled for bison, elk, and maybe even a grizzly!"
        
        # Generic but contextual
        else:
            # Extract destination from prompt
            destination = "your destination"
            for phrase in ["traveling to", "travel to", "headed to", "going to"]:
                if phrase in prompt_lower:
                    parts = prompt_lower.split(phrase)
                    if len(parts) > 1:
                        dest_part = parts[1].split("from")[0].strip()
                        destination = dest_part.title()
                        break
            
            return f"What an exciting journey to {destination}! Every mile brings new discoveries and stories waiting to be told. This adventure promises memories that will last a lifetime!"


def generate_tts_audio(text: str) -> Optional[str]:
    """Generate TTS audio and upload to GCS"""
    try:
        init_clients()
        if not tts_client or not storage_client:
            logger.warning("TTS or Storage client not available")
            return None
        # Set the text input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-O"
        )
        
        # Select the type of audio file
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # Perform the text-to-speech request
        response = tts_client.synthesize_speech(
            input=synthesis_input, 
            voice=voice, 
            audio_config=audio_config
        )
        
        # Save to GCS
        file_name = f"mvp-audio/{uuid.uuid4()}.mp3"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.upload_from_string(response.audio_content, content_type="audio/mpeg")
        
        # Generate signed URL (1 hour expiration)
        url = blob.generate_signed_url(expiration=3600, method="GET")
        return url
        
    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return None


@router.post("/voice", response_model=MVPVoiceResponse)
async def mvp_voice_interaction(request: MVPVoiceRequest):
    """
    REAL voice interaction endpoint with AI and TTS.
    """
    try:
        init_clients()  # Initialize clients if not already done
        user_input = request.user_input.lower()
        location = request.context.get("location", {})
        location_name = request.context.get("location_name", "your current location")
        
        # Check if navigation command
        is_navigation = any(phrase in user_input for phrase in [
            "navigate to", "take me to", "go to", "drive to"
        ])
        
        if is_navigation:
            # Extract destination
            destination = None
            for phrase in ["navigate to", "take me to", "go to", "drive to"]:
                if phrase in user_input:
                    destination = user_input.split(phrase)[-1].strip()
                    break
            
            if destination:
                # Get navigation directions from Google Maps
                route_data = None
                if location.get('lat') and location.get('lng'):
                    init_clients()  # Ensure gmaps is initialized
                    logger.info(f"Google Maps client status: {gmaps is not None}")
                if gmaps and location.get('lat') and location.get('lng'):
                    try:
                        logger.info(f"Requesting directions from ({location['lat']}, {location['lng']}) to {destination}")
                        # Get directions
                        directions_result = gmaps.directions(
                            origin=(location['lat'], location['lng']),
                            destination=destination,
                            mode="driving",
                            units="imperial"
                        )
                        
                        if directions_result:
                            route = directions_result[0]
                            legs = route['legs'][0]
                            
                            # Extract route information
                            route_data = {
                                "distance": legs['distance']['text'],
                                "duration": legs['duration']['text'],
                                "start_address": legs['start_address'],
                                "end_address": legs['end_address'],
                                "steps": [
                                    {
                                        "instruction": step['html_instructions'].replace('<b>', '').replace('</b>', '').replace('<div style="font-size:0.9em">', ' ').replace('</div>', ''),
                                        "distance": step['distance']['text'],
                                        "duration": step['duration']['text']
                                    }
                                    for step in legs['steps'][:5]  # First 5 steps for MVP
                                ],
                                "overview_polyline": route['overview_polyline']['points']
                            }
                            
                            # Generate AI story with route context
                            prompt = f"""
                            Create an engaging story about traveling to {destination} from {location_name}.
                            The journey is {legs['distance']['text']} and will take about {legs['duration']['text']}.
                            The story should be:
                            - 2-3 sentences long
                            - Exciting and anticipatory
                            - Mention something interesting about {destination}
                            - Written in a friendly, conversational tone
                            
                            Current location: {location_name}
                            Destination: {destination}
                            Distance: {legs['distance']['text']}
                            Duration: {legs['duration']['text']}
                            """
                        else:
                            # Fallback if no route found
                            prompt = f"""
                            Create a brief, engaging story about traveling to {destination} from {location_name}.
                            The story should be:
                            - 2-3 sentences long
                            - Exciting and anticipatory
                            - Mention something interesting about {destination}
                            - Written in a friendly, conversational tone
                            
                            Current location: {location_name}
                            Destination: {destination}
                            """
                    except Exception as e:
                        logger.error(f"Google Maps error: {str(e)}")
                        prompt = f"""
                        Create a brief, engaging story about traveling to {destination} from {location_name}.
                        The story should be:
                        - 2-3 sentences long
                        - Exciting and anticipatory
                        - Mention something interesting about {destination}
                        - Written in a friendly, conversational tone
                        
                        Current location: {location_name}
                        Destination: {destination}
                        """
                else:
                    # No Maps API or location
                    prompt = f"""
                    Create a brief, engaging story about traveling to {destination} from {location_name}.
                    The story should be:
                    - 2-3 sentences long
                    - Exciting and anticipatory
                    - Mention something interesting about {destination}
                    - Written in a friendly, conversational tone
                    
                    Current location: {location_name}
                    Destination: {destination}
                    """
                
                story_text = generate_story_with_ai(prompt)
                
                # Generate TTS audio
                audio_url = generate_tts_audio(story_text)
                
                response_data = {
                    "type": "navigation",
                    "destination": destination,
                    "action": "start_navigation",
                    "text": story_text,
                    "has_route": route_data is not None
                }
            else:
                response_data = {
                    "type": "error",
                    "text": "I didn't catch the destination. Please say 'Navigate to' followed by where you'd like to go."
                }
                audio_url = None
        else:
            # Generate REAL location-based story
            prompt = f"""
            Tell an interesting fact or short story about {location_name}.
            The story should be:
            - 2-3 sentences long
            - Educational or entertaining
            - Based on real facts about the location
            - Written in a friendly, engaging tone
            
            Location: {location_name}
            Coordinates: {location.get('lat', 'unknown')}, {location.get('lng', 'unknown')}
            """
            
            story_text = generate_story_with_ai(prompt)
            
            # Generate TTS audio
            audio_url = generate_tts_audio(story_text)
            
            response_data = {
                "type": "story",
                "text": story_text
            }
        
        return MVPVoiceResponse(
            response=response_data,
            audio_url=audio_url,
            route=route_data if 'route_data' in locals() else None
        )
        
    except Exception as e:
        logger.error(f"MVP voice interaction error: {str(e)}")
        return MVPVoiceResponse(
            response={
                "type": "error",
                "text": f"Error: {str(e)}"
            },
            audio_url=None
        )


@router.get("/health")
async def mvp_health_check():
    """Health check for MVP endpoints"""
    return {
        "status": "healthy",
        "service": "mvp_voice_real",
        "ai_configured": bool(project_id),
        "tts_available": tts_client is not None,
        "storage_configured": bool(bucket_name),
        "maps_configured": gmaps is not None
    }