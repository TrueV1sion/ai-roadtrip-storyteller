from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..services.ar import AREngine, ARRenderer
from ..schemas.ar import (
    ARPointRequest, ARPoint, HistoricalARPoint, NavigationARPoint, NatureARPoint,
    ARRenderSettingsUpdate, HistoricalOverlayRequest, HistoricalOverlayResponse,
    ARViewParameters, RenderableARElement, ARRenderResponse
)
from ..core.security import get_current_user
from ..models.user import User
from ..core.enhanced_ai_client import get_enhanced_ai_client
from ..services.locationService import get_location_service
from ..services.historical_service import get_historical_service

router = APIRouter(prefix="/ar", tags=["ar"])

def get_ar_engine():
    """Dependency to get AR engine instance"""
    location_service = get_location_service()
    historical_service = get_historical_service()
    ai_client = get_enhanced_ai_client()
    return AREngine(location_service, historical_service, ai_client)

def get_ar_renderer():
    """Dependency to get AR renderer instance"""
    return ARRenderer()

@router.post("/points", response_model=List[ARPoint])
async def get_ar_points(
    request: ARPointRequest,
    current_user: User = Depends(get_current_user),
    ar_engine: AREngine = Depends(get_ar_engine)
):
    """Get AR points around the user's location"""
    try:
        ar_points = await ar_engine.get_ar_points(
            user=current_user,
            latitude=request.latitude,
            longitude=request.longitude,
            radius=request.radius,
            types=request.types
        )
        
        # Convert to response model
        response = []
        for point in ar_points:
            if point.type == "historical":
                response.append(HistoricalARPoint(**point.dict()))
            elif point.type == "navigation":
                response.append(NavigationARPoint(**point.dict()))
            elif point.type == "nature":
                response.append(NatureARPoint(**point.dict()))
            else:
                response.append(ARPoint(**point.dict()))
                
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting AR points: {str(e)}")

@router.post("/render", response_model=ARRenderResponse)
async def render_ar_view(
    request: ARPointRequest,
    view_params: ARViewParameters,
    current_user: User = Depends(get_current_user),
    ar_engine: AREngine = Depends(get_ar_engine),
    ar_renderer: ARRenderer = Depends(get_ar_renderer)
):
    """Render AR points for display"""
    try:
        # Get AR points
        ar_points = await ar_engine.get_ar_points(
            user=current_user,
            latitude=request.latitude,
            longitude=request.longitude,
            radius=request.radius,
            types=request.types
        )
        
        # Prepare for rendering
        renderable_elements = ar_renderer.prepare_for_rendering(
            ar_points=ar_points,
            device_heading=view_params.device_heading,
            device_pitch=view_params.device_pitch,
            camera_fov=view_params.camera_fov
        )
        
        # Convert to response format
        elements = []
        for elem in renderable_elements:
            elements.append(RenderableARElement(
                id=elem.id,
                source_point_id=elem.source_point.id,
                view_x=elem.view_x,
                view_y=elem.view_y,
                view_z=elem.view_z,
                scale=elem.scale,
                opacity=elem.opacity,
                visible=elem.visible,
                appearance=elem.appearance,
                interaction=elem.interaction
            ))
            
        return ARRenderResponse(
            elements=elements,
            settings=ar_renderer.settings.dict(),
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering AR view: {str(e)}")

@router.patch("/render/settings", response_model=Dict[str, Any])
async def update_render_settings(
    settings: ARRenderSettingsUpdate,
    current_user: User = Depends(get_current_user),
    ar_renderer: ARRenderer = Depends(get_ar_renderer)
):
    """Update AR rendering settings"""
    try:
        updated_settings = ar_renderer.update_settings(settings.dict(exclude_unset=True))
        return updated_settings.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating AR settings: {str(e)}")

@router.post("/historical/overlay", response_model=HistoricalOverlayResponse)
async def get_historical_overlay(
    request: HistoricalOverlayRequest,
    current_user: User = Depends(get_current_user),
    ar_engine: AREngine = Depends(get_ar_engine)
):
    """Generate a historical overlay for a location"""
    try:
        overlay = await ar_engine.generate_historical_overlay(
            user=current_user,
            latitude=request.latitude,
            longitude=request.longitude,
            year=request.year
        )
        
        return HistoricalOverlayResponse(**overlay)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating historical overlay: {str(e)}")