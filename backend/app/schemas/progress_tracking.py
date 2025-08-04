"""
Pydantic schemas for progress tracking system
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class NoteType(str, Enum):
    """Types of progress notes"""
    UPDATE = "update"
    PROGRESS = "progress" 
    BLOCKER = "blocker"
    COMPLETED = "completed"
    QUESTION = "question"
    INSIGHT = "insight"
    MILESTONE = "milestone"


class EmotionState(BaseModel):
    """Emotion state from voice analysis"""
    primary: str = Field(..., description="Primary emotion detected")
    intensity: float = Field(..., ge=0, le=1, description="Emotion intensity 0-1")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence 0-1")
    secondary: Optional[str] = None
    raw_scores: Optional[Dict[str, float]] = None


class ProgressNoteBase(BaseModel):
    """Base schema for progress notes"""
    task_id: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)
    note_type: NoteType = NoteType.UPDATE
    voice_transcript: Optional[str] = None
    emotion_state: Optional[EmotionState] = None
    metadata: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    mentions: Optional[List[str]] = []


class ProgressNoteCreate(ProgressNoteBase):
    """Schema for creating progress notes"""
    urgency_level: Optional[int] = Field(0, ge=0, le=4)
    
    @validator('mentions')
    def validate_mentions(cls, v):
        """Validate mention format"""
        if v:
            for mention in v:
                if not mention.startswith('@'):
                    raise ValueError(f"Mention must start with @: {mention}")
        return v


class ProgressNoteUpdate(BaseModel):
    """Schema for updating progress notes"""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    note_type: Optional[NoteType] = None
    tags: Optional[List[str]] = None
    urgency_level: Optional[int] = Field(None, ge=0, le=4)


class ProgressNoteResponse(ProgressNoteBase):
    """Schema for progress note responses"""
    id: str
    user_id: str
    team_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sentiment_score: Optional[float] = None
    urgency_level: int = 0
    insights: Optional[Dict[str, Any]] = {}
    reactions: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        orm_mode = True


class TeamMemberBase(BaseModel):
    """Base schema for team members"""
    team_id: str
    user_id: str
    role: str = "member"


class TeamMemberCreate(TeamMemberBase):
    """Schema for adding team members"""
    can_create_notes: bool = True
    can_edit_others: bool = False
    can_delete: bool = False


class TeamMemberResponse(TeamMemberBase):
    """Schema for team member responses"""
    id: str
    joined_at: datetime
    last_active: Optional[datetime] = None
    notes_created: int = 0
    
    class Config:
        orm_mode = True


class TaskProgressBase(BaseModel):
    """Base schema for task progress"""
    task_id: str
    completion_percentage: float = Field(0.0, ge=0, le=100)
    status: str = "not_started"


class TaskProgressCreate(TaskProgressBase):
    """Schema for creating task progress"""
    estimated_hours: Optional[float] = None
    milestones: Optional[List[Dict[str, Any]]] = []


class TaskProgressUpdate(BaseModel):
    """Schema for updating task progress"""
    completion_percentage: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    actual_hours: Optional[float] = None
    blockers: Optional[List[str]] = None
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status values"""
        valid_statuses = ['not_started', 'in_progress', 'blocked', 'completed', 'on_hold']
        if v and v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class TaskProgressResponse(TaskProgressBase):
    """Schema for task progress responses"""
    id: str
    estimated_hours: Optional[float] = None
    actual_hours: float = 0.0
    blockers: List[str] = []
    milestones: List[Dict[str, Any]] = []
    defects_found: int = 0
    defects_resolved: int = 0
    test_coverage: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime
    
    class Config:
        orm_mode = True


class VoiceProgressNoteCreate(BaseModel):
    """Schema for creating progress notes from voice"""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    task_id: Optional[str] = None
    team_id: Optional[str] = None


class ProgressAnalytics(BaseModel):
    """Schema for progress analytics response"""
    total_notes: int
    notes_per_day: float
    active_contributors: int
    task_coverage: int
    sentiment_analysis: Dict[str, float]
    velocity_trend: List[float]
    collaboration_score: float
    six_sigma_metrics: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "total_notes": 150,
                "notes_per_day": 21.4,
                "active_contributors": 8,
                "task_coverage": 15,
                "sentiment_analysis": {
                    "positive": 0.65,
                    "neutral": 0.25,
                    "negative": 0.10
                },
                "velocity_trend": [15, 18, 22, 20, 25, 23, 21],
                "collaboration_score": 85.5,
                "six_sigma_metrics": {
                    "dpmo": 6210,
                    "cycle_time": 4.5,
                    "yield": 92.5,
                    "sigma_level": 4.0
                }
            }
        }


class TeamBase(BaseModel):
    """Base schema for teams"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating teams"""
    settings: Optional[Dict[str, Any]] = {}
    track_velocity: bool = True
    track_sentiment: bool = True
    track_collaboration: bool = True


class TeamResponse(TeamBase):
    """Schema for team responses"""
    id: str
    settings: Dict[str, Any]
    track_velocity: bool
    track_sentiment: bool
    track_collaboration: bool
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0
    
    class Config:
        orm_mode = True


class ProgressSearchQuery(BaseModel):
    """Schema for searching progress notes"""
    query: Optional[str] = None
    task_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    team_ids: Optional[List[str]] = None
    note_types: Optional[List[NoteType]] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sentiment: Optional[str] = None
    urgency_min: Optional[int] = Field(None, ge=0, le=4)
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class ReactionCreate(BaseModel):
    """Schema for creating reactions"""
    progress_note_id: str
    reaction_type: str = Field(..., regex="^[\\u263a-\\U0001f645]$")  # Emoji validation


class ReactionResponse(BaseModel):
    """Schema for reaction responses"""
    id: str
    progress_note_id: str
    user_id: str
    reaction_type: str
    created_at: datetime
    
    class Config:
        orm_mode = True