from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class VoiceAge(str, Enum):
    CHILD = "child"
    YOUNG = "young"
    ADULT = "adult"
    SENIOR = "senior"

class VoiceAccent(str, Enum):
    AMERICAN = "american"
    BRITISH = "british"
    AUSTRALIAN = "australian"
    INDIAN = "indian"
    FRENCH = "french"
    GERMAN = "german"
    SPANISH = "spanish"
    ITALIAN = "italian"
    JAPANESE = "japanese"
    KOREAN = "korean"
    CHINESE = "chinese"
    RUSSIAN = "russian"
    ARABIC = "arabic"
    OTHER = "other"
    NONE = "none"

class EmotionType(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"
    FEARFUL = "fearful"
    SURPRISED = "surprised"

class VoiceCharacterBase(BaseModel):
    """Base schema for voice character"""
    name: str
    description: str
    voice_id: str
    gender: VoiceGender
    age: VoiceAge
    accent: VoiceAccent
    speaking_style: str
    pitch: float = 1.0
    rate: float = 1.0
    base_emotion: EmotionType = EmotionType.NEUTRAL

class VoiceCharacterCreate(VoiceCharacterBase):
    """Schema for creating a voice character"""
    personality_traits: List[str] = Field(default_factory=list)
    speech_patterns: Dict[str, str] = Field(default_factory=dict)
    filler_words: List[str] = Field(default_factory=list)
    vocabulary_level: str = "standard"
    backstory: Optional[str] = None
    theme_affinity: List[str] = Field(default_factory=list)
    character_image_url: Optional[str] = None

class VoiceCharacter(VoiceCharacterBase):
    """Schema for voice character response"""
    id: str
    personality_traits: List[str] = Field(default_factory=list)
    speech_patterns: Dict[str, str] = Field(default_factory=dict)
    filler_words: List[str] = Field(default_factory=list)
    vocabulary_level: str = "standard"
    backstory: Optional[str] = None
    theme_affinity: List[str] = Field(default_factory=list)
    character_image_url: Optional[str] = None
    
    class Config:
        orm_mode = True

class VoiceCharacterUpdate(BaseModel):
    """Schema for updating a voice character"""
    name: Optional[str] = None
    description: Optional[str] = None
    voice_id: Optional[str] = None
    gender: Optional[VoiceGender] = None
    age: Optional[VoiceAge] = None
    accent: Optional[VoiceAccent] = None
    speaking_style: Optional[str] = None
    pitch: Optional[float] = None
    rate: Optional[float] = None
    base_emotion: Optional[EmotionType] = None
    personality_traits: Optional[List[str]] = None
    speech_patterns: Optional[Dict[str, str]] = None
    filler_words: Optional[List[str]] = None
    vocabulary_level: Optional[str] = None
    backstory: Optional[str] = None
    theme_affinity: Optional[List[str]] = None
    character_image_url: Optional[str] = None

class SpeechPromptBase(BaseModel):
    """Base schema for speech prompt"""
    text: str
    character_id: str

class SpeechPromptCreate(SpeechPromptBase):
    """Schema for creating a speech prompt"""
    context: Dict[str, Any] = Field(default_factory=dict)
    emotion: Optional[EmotionType] = None
    emphasis_words: List[str] = Field(default_factory=list)

class SpeechPrompt(SpeechPromptBase):
    """Schema for speech prompt response"""
    id: str
    context: Dict[str, Any]
    emotion: Optional[EmotionType] = None
    emphasis_words: List[str]
    
    class Config:
        orm_mode = True

class SpeechResult(BaseModel):
    """Schema for speech generation result"""
    original_text: str
    transformed_text: str
    audio_url: str
    duration: float
    character_id: str
    emotion: EmotionType
    
    class Config:
        orm_mode = True

class ThemeRequest(BaseModel):
    """Schema for getting characters by theme"""
    theme: str

class ContextualCharacterRequest(BaseModel):
    """Schema for getting a character by theme and context"""
    theme: str
    context: Dict[str, Any] = Field(default_factory=dict)