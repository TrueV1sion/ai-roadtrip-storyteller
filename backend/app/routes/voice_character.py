from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Dict, Any, Optional

from ..services.voice_character_system import VoiceCharacterSystem
from ..services.tts_service import TTSService
from ..core.enhanced_ai_client import get_enhanced_ai_client
from ..core.security import get_current_user
from ..models.user import User
from ..schemas.voice_character import (
    VoiceCharacter,
    VoiceCharacterCreate,
    VoiceCharacterUpdate,
    SpeechPromptCreate,
    SpeechResult,
    ThemeRequest,
    ContextualCharacterRequest
)

router = APIRouter(prefix="/voice-character", tags=["Voice Character"])

def get_voice_character_system(
    ai_client = Depends(get_enhanced_ai_client),
    tts_service: TTSService = Depends(lambda: TTSService())
) -> VoiceCharacterSystem:
    return VoiceCharacterSystem(ai_client=ai_client, tts_service=tts_service)

@router.get("/", response_model=List[VoiceCharacter])
async def get_all_characters(
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Get all available voice characters"""
    characters = voice_character_system.get_all_characters()
    return characters

@router.get("/{character_id}", response_model=VoiceCharacter)
async def get_character(
    character_id: str = Path(..., description="The ID of the voice character"),
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Get a specific voice character by ID"""
    character = voice_character_system.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

@router.post("/", response_model=VoiceCharacter)
async def create_character(
    character: VoiceCharacterCreate,
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Create a new voice character"""
    new_character = voice_character_system.create_character(character)
    return new_character

@router.patch("/{character_id}", response_model=VoiceCharacter)
async def update_character(
    character_update: VoiceCharacterUpdate,
    character_id: str = Path(..., description="The ID of the voice character to update"),
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Update an existing voice character"""
    updated_character = voice_character_system.update_character(
        character_id, character_update.dict(exclude_unset=True)
    )
    if not updated_character:
        raise HTTPException(status_code=404, detail="Character not found")
    return updated_character

@router.delete("/{character_id}")
async def delete_character(
    character_id: str = Path(..., description="The ID of the voice character to delete"),
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Delete a voice character"""
    success = voice_character_system.delete_character(character_id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"message": "Character deleted successfully"}

@router.post("/theme", response_model=List[VoiceCharacter])
async def get_characters_by_theme(
    request: ThemeRequest,
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Get voice characters that match a specific theme"""
    characters = voice_character_system.get_characters_by_theme(request.theme)
    return characters

@router.post("/contextual", response_model=VoiceCharacter)
async def get_character_by_context(
    request: ContextualCharacterRequest,
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Get the most appropriate character for a theme and context"""
    character = voice_character_system.get_character_by_theme_and_context(
        request.theme, request.context
    )
    if not character:
        raise HTTPException(status_code=404, detail="No suitable character found")
    return character

@router.post("/transform", response_model=Dict[str, str])
async def transform_text(
    prompt: SpeechPromptCreate,
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Transform text based on character's personality and context"""
    transformed_text = await voice_character_system.transform_text(prompt)
    if not transformed_text:
        raise HTTPException(status_code=400, detail="Failed to transform text")
    return {"original_text": prompt.text, "transformed_text": transformed_text}

@router.post("/speech", response_model=SpeechResult)
async def generate_speech(
    prompt: SpeechPromptCreate,
    current_user: User = Depends(get_current_user),
    voice_character_system: VoiceCharacterSystem = Depends(get_voice_character_system)
):
    """Generate speech audio for a character"""
    result = await voice_character_system.generate_speech(prompt)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to generate speech")
    return result