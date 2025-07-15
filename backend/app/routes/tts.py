from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from google.cloud import texttospeech
from google.oauth2 import service_account
import base64

from app.services.tts_service import tts_synthesizer
from app.core.authorization import get_current_active_user, get_optional_user, UserRole
from app.database import get_db
from app.models import User
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Initialize Google Cloud TTS client
def get_tts_client():
    """Get Google Cloud TTS client with credentials"""
    try:
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
            return texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            # Use default credentials (for development/testing)
            return texttospeech.TextToSpeechClient()
    except Exception as e:
        logger.error(f"Failed to initialize TTS client: {str(e)}")
        return None


class TTSRequest(BaseModel):
    """Request model for text-to-speech synthesis."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice_name: Optional[str] = None
    language_code: Optional[str] = None
    permanent: bool = False
    watermark: Optional[str] = None


class TTSResponse(BaseModel):
    """Response model for text-to-speech synthesis."""
    audio_url: str
    expiration_minutes: int
    is_permanent: bool


@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    client_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Synthesize speech from text and return a URL to the audio file.
    
    This endpoint supports both authenticated and anonymous users, with 
    different rate limits and capabilities based on user status.
    """
    # Get client IP for security logging and URL restriction
    client_ip = client_request.client.host if client_request.client else None
    
    # Check for premium user features
    is_premium = current_user and (current_user.is_premium or current_user.role in [UserRole.PREMIUM, UserRole.ADMIN])
    
    # Set up user context
    user_id = current_user.id if current_user else None
    
    # Apply rate limiting for anonymous users
    if not current_user:
        # Basic rate limiting could be implemented with Redis
        # For now, just log the anonymous request
        logger.info(f"Anonymous TTS request from IP {client_ip}")
        
        # Restrict text length for anonymous users
        if len(request.text) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text length exceeds limit for anonymous users. Please sign in."
            )
            
        # Don't allow permanent storage for anonymous users
        if request.permanent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permanent storage is only available for authenticated users."
            )
    
    # Apply premium-only feature restrictions
    if not is_premium:
        # Restrict certain voices to premium users
        premium_voices = ["en-US-Neural2-F", "en-US-Neural2-J", "en-US-Studio-O"]
        if request.voice_name in premium_voices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This voice is only available for premium users."
            )
            
        # Limit text length for standard users
        if current_user and len(request.text) > 2000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text length exceeds limit for standard users. Please upgrade to premium."
            )
    
    # Add watermark for premium content if requested
    watermark = None
    if is_premium and request.watermark:
        watermark = request.watermark
        
    try:
        # Handle permanent vs temporary storage
        if request.permanent and current_user:
            # Store permanently (only for authenticated users)
            gcs_path = tts_synthesizer.synthesize_and_store_permanently(
                text=request.text,
                voice_name=request.voice_name,
                language_code=request.language_code,
                user_id=user_id,
                is_premium=is_premium,
                watermark=watermark
            )
            
            if not gcs_path:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to synthesize speech."
                )
                
            # Get a signed URL for the permanent object
            audio_url = tts_synthesizer.get_signed_url_for_gcs_path(
                gcs_path=gcs_path,
                expiration_hours=24 if is_premium else 1,
                user_id=user_id,
                ip_address=client_ip,
                is_premium=is_premium
            )
            
            if not audio_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate URL for audio."
                )
                
            return TTSResponse(
                audio_url=audio_url,
                expiration_minutes=24*60 if is_premium else 60,
                is_permanent=True
            )
            
        else:
            # Use temporary storage
            audio_url = tts_synthesizer.synthesize_and_upload(
                text=request.text,
                voice_name=request.voice_name,
                language_code=request.language_code,
                user_id=user_id,
                ip_address=client_ip,
                is_premium=is_premium,
                watermark=watermark
            )
            
            if not audio_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to synthesize speech."
                )
                
            # Calculate expiration time
            expiration_minutes = 60 if is_premium else 30
                
            return TTSResponse(
                audio_url=audio_url,
                expiration_minutes=expiration_minutes,
                is_permanent=False
            )
            
    except Exception as e:
        logger.error(f"Error in TTS endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during speech synthesis."
        )


@router.get("/voices", response_model=List[Dict[str, Any]])
async def list_voices(
    language: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List available TTS voices.
    
    Premium voices are only shown to premium users.
    """
    # Define available voices with their properties
    all_voices = [
        {
            "name": "en-US-Standard-B",
            "language_code": "en-US",
            "gender": "MALE",
            "premium": False,
            "description": "Standard male voice"
        },
        {
            "name": "en-US-Standard-C",
            "language_code": "en-US",
            "gender": "FEMALE",
            "premium": False,
            "description": "Standard female voice"
        },
        {
            "name": "en-US-Studio-O",
            "language_code": "en-US",
            "gender": "FEMALE",
            "premium": True,
            "description": "Premium high-quality female voice"
        },
        {
            "name": "en-US-Neural2-F",
            "language_code": "en-US",
            "gender": "FEMALE",
            "premium": True,
            "description": "Premium neural female voice"
        },
        {
            "name": "en-US-Neural2-J",
            "language_code": "en-US",
            "gender": "MALE",
            "premium": True,
            "description": "Premium neural male voice"
        }
    ]
    
    # Filter by language if specified
    if language:
        voices = [v for v in all_voices if v["language_code"] == language]
    else:
        voices = all_voices
    
    # Check if user is premium
    is_premium = current_user and (current_user.is_premium or current_user.role in [UserRole.PREMIUM, UserRole.ADMIN])
    
    # Filter out premium voices for non-premium users
    if not is_premium:
        voices = [v for v in voices if not v["premium"]]
    
    return voices


# Google Cloud TTS Integration

def get_tts_client():
    """Get Google Cloud TTS client with credentials"""
    try:
        if hasattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS') and settings.GOOGLE_APPLICATION_CREDENTIALS:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
            return texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            # Use default credentials (for development/testing)
            return texttospeech.TextToSpeechClient()
    except Exception as e:
        logger.error(f"Failed to initialize TTS client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize TTS client: {str(e)}"
        )


class GoogleTTSVoiceConfig(BaseModel):
    """Google Cloud TTS Voice configuration"""
    language_code: str = Field(default="en-US", description="Language code")
    name: Optional[str] = Field(default=None, description="Voice name")
    ssml_gender: str = Field(default="NEUTRAL", description="Voice gender")
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0, description="Speaking rate")
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0, description="Voice pitch")
    volume_gain_db: float = Field(default=0.0, ge=-96.0, le=16.0, description="Volume gain")


class GoogleTTSAudioConfig(BaseModel):
    """Google Cloud TTS Audio output configuration"""
    audio_encoding: str = Field(default="MP3", description="Audio encoding format")
    speaking_rate: Optional[float] = Field(default=None, description="Override speaking rate")
    pitch: Optional[float] = Field(default=None, description="Override pitch")
    volume_gain_db: Optional[float] = Field(default=None, description="Override volume")
    sample_rate_hertz: Optional[int] = Field(default=None, description="Sample rate")
    effects_profile_id: Optional[List[str]] = Field(
        default=["headphone-class-device"],
        description="Audio effects profile"
    )


class GoogleTTSInput(BaseModel):
    """Text input for Google Cloud TTS synthesis"""
    text: Optional[str] = Field(default=None, description="Plain text input")
    ssml: Optional[str] = Field(default=None, description="SSML markup input")


class GoogleTTSRequest(BaseModel):
    """Google Cloud Text-to-Speech synthesis request"""
    input: GoogleTTSInput
    voice: GoogleTTSVoiceConfig
    audio_config: GoogleTTSAudioConfig


class GoogleTTSResponse(BaseModel):
    """Google Cloud Text-to-Speech synthesis response"""
    audio_content: str = Field(description="Base64 encoded audio data")


@router.post("/google/synthesize", response_model=GoogleTTSResponse)
async def synthesize_speech_google(
    request: GoogleTTSRequest,
    current_user: User = Depends(get_current_active_user),
    tts_client = Depends(get_tts_client)
) -> GoogleTTSResponse:
    """
    Synthesize speech using Google Cloud Text-to-Speech
    
    - **input**: Text or SSML to synthesize
    - **voice**: Voice configuration including language, gender, and parameters
    - **audio_config**: Audio output configuration
    """
    try:
        # Prepare synthesis input
        if request.input.ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=request.input.ssml)
        elif request.input.text:
            synthesis_input = texttospeech.SynthesisInput(text=request.input.text)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either text or ssml must be provided"
            )
        
        # Configure voice parameters
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=request.voice.language_code,
            ssml_gender=getattr(
                texttospeech.SsmlVoiceGender,
                request.voice.ssml_gender.upper()
            )
        )
        
        # Add specific voice name if provided
        if request.voice.name:
            voice_params.name = request.voice.name
        
        # Configure audio output
        audio_encoding = getattr(
            texttospeech.AudioEncoding,
            request.audio_config.audio_encoding.upper()
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=request.audio_config.speaking_rate or request.voice.speaking_rate,
            pitch=request.audio_config.pitch or request.voice.pitch,
            volume_gain_db=request.audio_config.volume_gain_db or request.voice.volume_gain_db,
        )
        
        # Add optional audio parameters
        if request.audio_config.sample_rate_hertz:
            audio_config.sample_rate_hertz = request.audio_config.sample_rate_hertz
        
        if request.audio_config.effects_profile_id:
            audio_config.effects_profile_id = request.audio_config.effects_profile_id
        
        # Perform text-to-speech synthesis
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        
        # Convert audio bytes to base64
        audio_content = base64.b64encode(response.audio_content).decode('utf-8')
        
        return GoogleTTSResponse(audio_content=audio_content)
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )


# Personality-specific voice presets
PERSONALITY_PRESETS = {
    "navigator": {
        "name": "en-US-Neural2-J",
        "language_code": "en-US",
        "ssml_gender": "MALE",
        "speaking_rate": 1.0,
        "pitch": -2.0
    },
    "friendly-guide": {
        "name": "en-US-Neural2-F",
        "language_code": "en-US", 
        "ssml_gender": "FEMALE",
        "speaking_rate": 0.95,
        "pitch": 1.0
    },
    "educational-expert": {
        "name": "en-US-Neural2-D",
        "language_code": "en-US",
        "ssml_gender": "MALE",
        "speaking_rate": 0.9,
        "pitch": -1.0
    },
    "mickey-mouse": {
        "name": "en-US-Neural2-A",
        "language_code": "en-US",
        "ssml_gender": "MALE",
        "speaking_rate": 1.1,
        "pitch": 8.0
    },
    "santa-claus": {
        "name": "en-US-Neural2-B",
        "language_code": "en-US",
        "ssml_gender": "MALE",
        "speaking_rate": 0.85,
        "pitch": -4.0
    }
}


# Google Cloud TTS Models
class GoogleVoiceConfig(BaseModel):
    """Voice configuration for Google Cloud TTS"""
    language_code: str = Field(default="en-US", description="Language code")
    name: Optional[str] = Field(default=None, description="Voice name")
    ssml_gender: str = Field(default="NEUTRAL", description="Voice gender")
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0, description="Speaking rate")
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0, description="Voice pitch")
    volume_gain_db: float = Field(default=0.0, ge=-96.0, le=16.0, description="Volume gain")

class GoogleAudioConfig(BaseModel):
    """Audio output configuration"""
    audio_encoding: str = Field(default="MP3", description="Audio encoding format")
    speaking_rate: Optional[float] = Field(default=None, description="Override speaking rate")
    pitch: Optional[float] = Field(default=None, description="Override pitch")
    volume_gain_db: Optional[float] = Field(default=None, description="Override volume")
    sample_rate_hertz: Optional[int] = Field(default=None, description="Sample rate")
    effects_profile_id: Optional[List[str]] = Field(
        default=["headphone-class-device"],
        description="Audio effects profile"
    )

class GoogleTTSInput(BaseModel):
    """Text input for synthesis"""
    text: Optional[str] = Field(default=None, description="Plain text input")
    ssml: Optional[str] = Field(default=None, description="SSML markup input")

class GoogleTTSRequest(BaseModel):
    """Google Cloud TTS synthesis request"""
    input: GoogleTTSInput
    voice: GoogleVoiceConfig
    audio_config: GoogleAudioConfig
    personality_id: Optional[str] = Field(default=None, description="Personality ID for voice presets")

class GoogleTTSResponse(BaseModel):
    """Google Cloud TTS synthesis response"""
    audio_content: str = Field(description="Base64 encoded audio data")
    metadata: Dict[str, Any] = Field(default={}, description="Response metadata")

@router.post("/google/synthesize", response_model=GoogleTTSResponse)
async def synthesize_speech_google(
    request: GoogleTTSRequest,
    current_user: User = Depends(get_current_active_user)
) -> GoogleTTSResponse:
    """
    Synthesize speech using Google Cloud Text-to-Speech
    
    - **input**: Text or SSML to synthesize
    - **voice**: Voice configuration including language, gender, and parameters
    - **audio_config**: Audio output configuration
    - **personality_id**: Optional personality preset to use
    """
    tts_client = get_tts_client()
    if not tts_client:
        raise HTTPException(
            status_code=500,
            detail="Google Cloud TTS service unavailable"
        )
    
    try:
        # Apply personality preset if provided
        if request.personality_id and request.personality_id in PERSONALITY_PRESETS:
            preset = PERSONALITY_PRESETS[request.personality_id]
            request.voice.name = preset.get("name", request.voice.name)
            request.voice.language_code = preset.get("language_code", request.voice.language_code)
            request.voice.ssml_gender = preset.get("ssml_gender", request.voice.ssml_gender)
            request.voice.speaking_rate = preset.get("speaking_rate", request.voice.speaking_rate)
            request.voice.pitch = preset.get("pitch", request.voice.pitch)
        
        # Prepare synthesis input
        if request.input.ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=request.input.ssml)
        elif request.input.text:
            synthesis_input = texttospeech.SynthesisInput(text=request.input.text)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either text or ssml must be provided"
            )
        
        # Configure voice parameters
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=request.voice.language_code,
            ssml_gender=getattr(
                texttospeech.SsmlVoiceGender,
                request.voice.ssml_gender.upper()
            )
        )
        
        # Add specific voice name if provided
        if request.voice.name:
            voice_params.name = request.voice.name
        
        # Configure audio output
        audio_encoding = getattr(
            texttospeech.AudioEncoding,
            request.audio_config.audio_encoding.upper()
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=request.audio_config.speaking_rate or request.voice.speaking_rate,
            pitch=request.audio_config.pitch or request.voice.pitch,
            volume_gain_db=request.audio_config.volume_gain_db or request.voice.volume_gain_db,
        )
        
        # Add optional audio parameters
        if request.audio_config.sample_rate_hertz:
            audio_config.sample_rate_hertz = request.audio_config.sample_rate_hertz
        
        if request.audio_config.effects_profile_id:
            audio_config.effects_profile_id = request.audio_config.effects_profile_id
        
        # Perform text-to-speech synthesis
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        
        # Convert audio bytes to base64
        audio_content = base64.b64encode(response.audio_content).decode('utf-8')
        
        # Add metadata
        metadata = {
            "voice_name": request.voice.name or "default",
            "language_code": request.voice.language_code,
            "audio_encoding": request.audio_config.audio_encoding,
            "personality_id": request.personality_id
        }
        
        return GoogleTTSResponse(
            audio_content=audio_content,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Google TTS synthesis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )

@router.get("/google/personality-presets")
async def get_google_personality_presets(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get available personality voice presets for Google Cloud TTS"""
    return {"presets": PERSONALITY_PRESETS}

@router.post("/google/synthesize-test")
async def synthesize_speech_google_test(
    request: GoogleTTSRequest
) -> GoogleTTSResponse:
    """
    TEST ENDPOINT: Synthesize speech using Google Cloud Text-to-Speech without authentication
    
    WARNING: This endpoint is for testing only and should be removed in production.
    """
    logger.warning("Using test TTS endpoint without authentication")
    
    tts_client = get_tts_client()
    if not tts_client:
        # Return mock data if Google Cloud TTS is not configured
        logger.warning("Google Cloud TTS not configured, returning mock audio")
        mock_audio = "SUQzAwAAAAAAF1RJVDIAAAAFAAAAblVsbABUUEUxAAAABQAAAG5VbGwA//uSwAAAAAAAAAAAAAAAAAAAAAAA"
        return GoogleTTSResponse(
            audio_content=mock_audio,
            metadata={
                "voice_name": request.voice.name or "mock",
                "language_code": request.voice.language_code,
                "audio_encoding": request.audio_config.audio_encoding,
                "personality_id": request.personality_id,
                "is_mock": True
            }
        )
    
    try:
        # Apply personality preset if provided
        if request.personality_id and request.personality_id in PERSONALITY_PRESETS:
            preset = PERSONALITY_PRESETS[request.personality_id]
            request.voice.name = preset.get("name", request.voice.name)
            request.voice.language_code = preset.get("language_code", request.voice.language_code)
            request.voice.ssml_gender = preset.get("ssml_gender", request.voice.ssml_gender)
            request.voice.speaking_rate = preset.get("speaking_rate", request.voice.speaking_rate)
            request.voice.pitch = preset.get("pitch", request.voice.pitch)
        
        # Prepare synthesis input
        if request.input.ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=request.input.ssml)
        elif request.input.text:
            synthesis_input = texttospeech.SynthesisInput(text=request.input.text)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either text or ssml must be provided"
            )
        
        # Configure voice parameters
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=request.voice.language_code,
            ssml_gender=getattr(
                texttospeech.SsmlVoiceGender,
                request.voice.ssml_gender.upper()
            )
        )
        
        # Add specific voice name if provided
        if request.voice.name:
            voice_params.name = request.voice.name
        
        # Configure audio output
        audio_encoding = getattr(
            texttospeech.AudioEncoding,
            request.audio_config.audio_encoding.upper()
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=request.audio_config.speaking_rate or request.voice.speaking_rate,
            pitch=request.audio_config.pitch or request.voice.pitch,
            volume_gain_db=request.audio_config.volume_gain_db or request.voice.volume_gain_db,
        )
        
        # Add optional audio parameters
        if request.audio_config.sample_rate_hertz:
            audio_config.sample_rate_hertz = request.audio_config.sample_rate_hertz
        
        if request.audio_config.effects_profile_id:
            audio_config.effects_profile_id = request.audio_config.effects_profile_id
        
        # Perform text-to-speech synthesis
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        
        # Convert audio bytes to base64
        audio_content = base64.b64encode(response.audio_content).decode('utf-8')
        
        # Add metadata
        metadata = {
            "voice_name": request.voice.name or "default",
            "language_code": request.voice.language_code,
            "audio_encoding": request.audio_config.audio_encoding,
            "personality_id": request.personality_id
        }
        
        return GoogleTTSResponse(
            audio_content=audio_content,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Google TTS synthesis failed: {str(e)}")
        # Return mock data on error
        mock_audio = "SUQzAwAAAAAAF1RJVDIAAAAFAAAAblVsbABUUEUxAAAABQAAAG5VbGwA//uSwAAAAAAAAAAAAAAAAAAAAAAA"
        return GoogleTTSResponse(
            audio_content=mock_audio,
            metadata={
                "voice_name": "mock",
                "language_code": request.voice.language_code,
                "audio_encoding": request.audio_config.audio_encoding,
                "personality_id": request.personality_id,
                "is_mock": True,
                "error": str(e)
            }
        )