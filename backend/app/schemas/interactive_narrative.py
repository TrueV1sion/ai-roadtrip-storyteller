from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4

class NarrativeChoiceBase(BaseModel):
    """Base schema for narrative choices"""
    text: str
    description: str

class NarrativeChoiceCreate(NarrativeChoiceBase):
    """Schema for creating a narrative choice"""
    consequences: Dict[str, Any] = Field(default_factory=dict)

class NarrativeChoice(NarrativeChoiceBase):
    """Schema for a narrative choice response"""
    id: str
    consequences: Dict[str, Any]

    class Config:
        orm_mode = True

class NarrativeNodeBase(BaseModel):
    """Base schema for narrative nodes"""
    title: str
    content: str
    image_prompt: Optional[str] = None
    audio_prompt: Optional[str] = None

class NarrativeNodeCreate(NarrativeNodeBase):
    """Schema for creating a narrative node"""
    choices: List[NarrativeChoiceCreate] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NarrativeNode(NarrativeNodeBase):
    """Schema for a narrative node response"""
    id: str
    choices: List[NarrativeChoice]
    metadata: Dict[str, Any]

    class Config:
        orm_mode = True

class NarrativeStateBase(BaseModel):
    """Base schema for narrative state"""
    current_node_id: str
    visited_nodes: List[str] = Field(default_factory=list)
    inventory: Dict[str, Any] = Field(default_factory=dict)
    character_traits: Dict[str, float] = Field(default_factory=dict)
    story_variables: Dict[str, Any] = Field(default_factory=dict)

class NarrativeStateCreate(NarrativeStateBase):
    """Schema for creating a narrative state"""
    pass

class NarrativeState(NarrativeStateBase):
    """Schema for a narrative state response"""
    id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        orm_mode = True

class StoryMetadataBase(BaseModel):
    """Base schema for story metadata"""
    title: str
    description: str
    theme: str
    location_type: str
    duration: str
    tags: List[str] = Field(default_factory=list)

class StoryMetadataCreate(StoryMetadataBase):
    """Schema for creating story metadata"""
    pass

class StoryMetadata(StoryMetadataBase):
    """Schema for story metadata response"""
    id: str
    created_at: datetime

    class Config:
        orm_mode = True

class NarrativeGraphBase(BaseModel):
    """Base schema for narrative graphs"""
    metadata: StoryMetadataCreate
    initial_node_id: str

class NarrativeGraphCreate(NarrativeGraphBase):
    """Schema for creating a narrative graph"""
    nodes: Dict[str, NarrativeNodeCreate]

class NarrativeGraph(NarrativeGraphBase):
    """Schema for a narrative graph response"""
    id: str
    metadata: StoryMetadata
    nodes: Dict[str, NarrativeNode]

    class Config:
        orm_mode = True

# Request/Response schemas for API operations

class CreateNarrativeRequest(BaseModel):
    """Request schema for creating a new narrative"""
    location: Dict[str, Any]
    theme: str
    duration: str = "medium"
    complexity: int = 2

class MakeChoiceRequest(BaseModel):
    """Request schema for making a choice in a narrative"""
    narrative_id: str
    state_id: str
    choice_id: str

class NodeContentRequest(BaseModel):
    """Request schema for getting personalized node content"""
    narrative_id: str
    state_id: str
    node_id: str

class NodeResponse(BaseModel):
    """Response schema for a narrative node with personalized content"""
    node: NarrativeNode
    personalized_content: Dict[str, Any]
    available_choices: List[NarrativeChoice]

class NarrativeProgressResponse(BaseModel):
    """Response schema for narrative progress"""
    narrative_id: str
    state: NarrativeState
    current_node: Optional[NodeResponse]
    completion_percentage: float
    choices_made: int