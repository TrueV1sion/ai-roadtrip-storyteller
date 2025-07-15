"""
Spatial Audio Routes - Endpoints for 3D audio coordination
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional
import logging

from ..schemas.spatial_audio import (
    SpatialAudioRequest,
    SpatialAudioResponse,
    EnvironmentUpdateRequest,
    AudioSourceUpdate
)
from ..services.master_orchestration_agent import MasterOrchestrationAgent
from ..services.spatial_audio_engine import spatial_audio_engine
from ..core.auth import get_current_user
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orchestration/spatial-audio", response_model=SpatialAudioResponse)
async def coordinate_spatial_audio(
    request: SpatialAudioRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(lambda: MasterOrchestrationAgent(None))
):
    """
    Coordinate spatial audio processing with the backend engine.
    
    This endpoint:
    - Determines appropriate audio environment
    - Creates immersive soundscapes
    - Positions audio sources in 3D space
    - Returns configuration for client-side processing
    """
    try:
        # Get spatial audio coordination from orchestrator
        result = await orchestrator.coordinate_spatial_audio(
            request.audio_type,
            request.location_context,
            request.audio_metadata
        )
        
        if result['status'] != 'success':
            raise HTTPException(
                status_code=500, 
                detail=result.get('message', 'Spatial audio coordination failed')
            )
        
        return SpatialAudioResponse(
            status=result['status'],
            environment=result['environment'],
            active_sources=result['active_sources'],
            soundscape=result['soundscape'],
            processing_config=result['processing_config']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error coordinating spatial audio: {e}")
        raise HTTPException(status_code=500, detail="Failed to coordinate spatial audio")


@router.post("/spatial-audio/environment")
async def update_environment(
    request: EnvironmentUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update the current audio environment"""
    try:
        await spatial_audio_engine.set_environment(request.environment)
        
        # Generate transition if needed
        if request.generate_transition and request.from_environment:
            transition = await spatial_audio_engine.generate_transition_effect(
                request.from_environment,
                request.environment,
                request.transition_duration or 2.0
            )
            
            return {
                "status": "success",
                "environment": request.environment.value,
                "transition_generated": True
            }
        
        return {
            "status": "success",
            "environment": request.environment.value,
            "transition_generated": False
        }
        
    except Exception as e:
        logger.error(f"Error updating environment: {e}")
        raise HTTPException(status_code=500, detail="Failed to update environment")


@router.post("/spatial-audio/source/update")
async def update_audio_source(
    update: AudioSourceUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update position or properties of an audio source"""
    try:
        if update.position:
            await spatial_audio_engine.update_source_position(
                update.source_id,
                update.position
            )
        
        # Could add volume, priority updates here
        
        return {
            "status": "success",
            "source_id": update.source_id,
            "updated": True
        }
        
    except Exception as e:
        logger.error(f"Error updating audio source: {e}")
        raise HTTPException(status_code=500, detail="Failed to update audio source")


@router.get("/spatial-audio/debug")
async def get_spatial_audio_debug(
    current_user: User = Depends(get_current_user)
):
    """Get debug information about spatial audio state"""
    try:
        debug_info = spatial_audio_engine.get_debug_info()
        return debug_info
        
    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get debug info")


@router.post("/spatial-audio/preferences")
async def update_spatial_preferences(
    preferences: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(lambda: MasterOrchestrationAgent(None))
):
    """Update user's spatial audio preferences"""
    try:
        await orchestrator.update_spatial_audio_preferences(preferences)
        
        return {
            "status": "success",
            "message": "Spatial audio preferences updated"
        }
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")