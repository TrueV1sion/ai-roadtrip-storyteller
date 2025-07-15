"""
Google Cloud Text-to-Speech API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from google.cloud import texttospeech
from google.oauth2 import service_account
import base64
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.auth import get_current_user
from app.models.user import User

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize TTS client: {str(e)}"
        )

class VoiceConfig(BaseModel):
    """Voice configuration"""
    language_code: str = Field(default="en-US", description="Language code")
    name: Optional[str] = Field(default=None, description="Voice name")
    ssml_gender: str = Field(default="NEUTRAL", description="Voice gender")
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0, description="Speaking rate")
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0, description="Voice pitch")
    volume_gain_db: float = Field(default=0.0, ge=-96.0, le=16.0, description="Volume gain")

class AudioConfig(BaseModel):
    """Audio output configuration"""
    audio_encoding: str = Field(default="MP3", description="Audio encoding format")
    speaking_rate: Optional[float] = Field(default=None, description="Override speaking rate")
    pitch: Optional[float] = Field(default=None, description="Override pitch")
    volume_gain_db: Optional[float] = Field(default=None, description="Override volume")
    sample_rate_hertz: Optional[int] = Field(default=None, description="Sample rate")
    effects_profile_id: Optional[list[str]] = Field(
        default=["headphone-class-device"],
        description="Audio effects profile"
    )

class TTSInput(BaseModel):
    """Text input for synthesis"""
    text: Optional[str] = Field(default=None, description="Plain text input")
    ssml: Optional[str] = Field(default=None, description="SSML markup input")

class TTSRequest(BaseModel):
    """Text-to-Speech synthesis request"""
    input: TTSInput
    voice: VoiceConfig
    audio_config: AudioConfig

class TTSResponse(BaseModel):
    """Text-to-Speech synthesis response"""
    audio_content: str = Field(description="Base64 encoded audio data")
    
@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
    tts_client = Depends(get_tts_client)
) -> TTSResponse:
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
        
        return TTSResponse(audio_content=audio_content)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )

@router.get("/voices")
async def list_voices(
    language_code: Optional[str] = "en-US",
    current_user: User = Depends(get_current_user),
    tts_client = Depends(get_tts_client)
) -> Dict[str, Any]:
    """
    List available voices for a given language
    
    - **language_code**: Language code to filter voices (default: en-US)
    """
    try:
        # List available voices
        response = tts_client.list_voices(language_code=language_code)
        
        voices = []
        for voice in response.voices:
            voices.append({
                "name": voice.name,
                "language_codes": voice.language_codes,
                "ssml_gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
            })
        
        return {
            "language_code": language_code,
            "voices": voices,
            "count": len(voices)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list voices: {str(e)}"
        )

@router.post("/validate-ssml")
async def validate_ssml(
    ssml: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate SSML markup
    
    - **ssml**: SSML markup to validate
    """
    try:
        # Basic SSML validation
        if not ssml.strip().startswith('<speak>'):
            return {
                "valid": False,
                "error": "SSML must start with <speak> tag"
            }
        
        if not ssml.strip().endswith('</speak>'):
            return {
                "valid": False,
                "error": "SSML must end with </speak> tag"
            }
        
        # Additional validation could be added here
        # For now, we'll do basic validation
        
        return {
            "valid": True,
            "message": "SSML appears to be valid"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }

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

@router.get("/personality-presets")
async def get_personality_presets(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get available personality voice presets"""
    return {"presets": PERSONALITY_PRESETS}