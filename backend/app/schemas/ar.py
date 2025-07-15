from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ARPointBase(BaseModel):
    """Base schema for AR point data"""
    title: str
    description: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    type: str
    
class ARPointCreate(ARPointBase):
    """Schema for creating a new AR point"""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class ARPoint(ARPointBase):
    """Schema for AR point response"""
    id: str
    metadata: Dict[str, Any]
    
    class Config:
        orm_mode = True
        
class HistoricalARPointCreate(ARPointCreate):
    """Schema for creating a historical AR point"""
    year: int
    historical_context: str
    image_url: Optional[str] = None
    
class HistoricalARPoint(ARPoint):
    """Schema for historical AR point response"""
    year: int
    historical_context: str
    image_url: Optional[str] = None
    
class NavigationARPointCreate(ARPointCreate):
    """Schema for creating a navigation AR point"""
    distance: float
    eta: Optional[int] = None
    direction: str
    
class NavigationARPoint(ARPoint):
    """Schema for navigation AR point response"""
    distance: float
    eta: Optional[int] = None
    direction: str
    
class NatureARPointCreate(ARPointCreate):
    """Schema for creating a nature AR point"""
    species: Optional[str] = None
    ecosystem_info: Optional[str] = None
    conservation_status: Optional[str] = None
    
class NatureARPoint(ARPoint):
    """Schema for nature AR point response"""
    species: Optional[str] = None
    ecosystem_info: Optional[str] = None
    conservation_status: Optional[str] = None
    
class ARPointRequest(BaseModel):
    """Schema for requesting AR points"""
    latitude: float
    longitude: float
    radius: Optional[float] = 500
    types: Optional[List[str]] = None
    
class ARRenderSettingsUpdate(BaseModel):
    """Schema for updating AR render settings"""
    distance_scale: Optional[float] = None
    opacity: Optional[float] = None
    color_scheme: Optional[str] = None
    show_labels: Optional[bool] = None
    show_distances: Optional[bool] = None
    show_arrows: Optional[bool] = None
    animation_speed: Optional[float] = None
    detail_level: Optional[int] = None
    accessibility_mode: Optional[bool] = None
    
class HistoricalOverlayRequest(BaseModel):
    """Schema for requesting a historical overlay"""
    latitude: float
    longitude: float
    year: Optional[int] = None
    
class HistoricalOverlayResponse(BaseModel):
    """Schema for historical overlay response"""
    title: str
    year: int
    description: str
    key_features: List[str]
    daily_life: str
    image_url: Optional[str] = None
    latitude: float
    longitude: float
    
class ARViewParameters(BaseModel):
    """Schema for AR view parameters"""
    device_heading: float
    device_pitch: float
    camera_fov: Optional[float] = 60.0
    
class RenderableARElement(BaseModel):
    """Schema for renderable AR element"""
    id: str
    source_point_id: str
    view_x: float
    view_y: float
    view_z: float
    scale: float
    opacity: float
    visible: bool
    appearance: Dict[str, Any]
    interaction: Dict[str, Any]
    
class ARRenderResponse(BaseModel):
    """Schema for AR render response"""
    elements: List[RenderableARElement]
    settings: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)