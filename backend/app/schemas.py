from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class StoryRequest(BaseModel):
    prompt: str = Field(..., example="Tell me a story about a brave adventurer.")

class UserInterests(BaseModel):
    history: bool = False
    nature: bool = False
    science: bool = False
    culture: bool = False
    music: bool = False
    food: bool = False
    architecture: bool = False
    folklore: bool = False

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    interests: UserInterests
    created_at: datetime
    updated_at: datetime

class TripContext(BaseModel):
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    speed: Optional[float] = None
    road_type: Optional[str] = None

class LocationStory(BaseModel):
    id: str
    location: Dict[str, float]
    story_text: str
    interests: List[str]
    context: Optional[TripContext] = None
    created_at: datetime

class StoryResponse(BaseModel):
    status: str
    story: str
    location: Dict[str, float]
    context: Optional[TripContext] = None

    class Config:
        orm_mode = True 