from typing import List, Dict, Any, Optional
import logging
import json
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.enhanced_ai_client import EnhancedAIClient
from ..services.tts_service import TTSService
from ..services.persona_synthesis_service import (
    PersonaSynthesisService,
    PersonalityProfile,
    ContentType
)
from ..services.web_persona_extractor import WebPersonaExtractor
from ..services.voice_synthesis_engine import VoiceSynthesisEngine

logger = logging.getLogger(__name__)

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
    """Base model for voice character"""
    name: str
    description: str
    voice_id: str
    gender: VoiceGender
    age: VoiceAge
    accent: VoiceAccent
    speaking_style: str
    pitch: float = 1.0  # 0.5 to 2.0, where 1.0 is normal
    rate: float = 1.0   # 0.5 to 2.0, where 1.0 is normal
    base_emotion: EmotionType = EmotionType.NEUTRAL
    is_synthesized: bool = False  # Whether this is a synthesized persona
    synthesis_source: Optional[str] = None  # URL or identifier of synthesis source
    
class VoiceCharacter(VoiceCharacterBase):
    """Model for a voice character"""
    id: str
    personality_traits: List[str] = Field(default_factory=list)
    speech_patterns: Dict[str, str] = Field(default_factory=dict)
    filler_words: List[str] = Field(default_factory=list)
    vocabulary_level: str = "standard"
    backstory: Optional[str] = None
    theme_affinity: List[str] = Field(default_factory=list)
    character_image_url: Optional[str] = None
    personality_profile: Optional[Dict[str, Any]] = None  # For synthesized personas
    voice_synthesis_params: Optional[Dict[str, Any]] = None  # Voice synthesis parameters
    
class SpeechPrompt(BaseModel):
    """Model for a speech generation prompt"""
    text: str
    character_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    emotion: Optional[EmotionType] = None
    emphasis_words: List[str] = Field(default_factory=list)
    
class SpeechResult(BaseModel):
    """Model for a speech generation result"""
    original_text: str
    transformed_text: str
    audio_url: str
    duration: float
    character_id: str
    emotion: EmotionType

class VoiceCharacterSystem:
    """Service for the voice character system"""
    
    def __init__(self, ai_client: EnhancedAIClient, tts_service: TTSService,
                 persona_synthesis: Optional[PersonaSynthesisService] = None):
        self.ai_client = ai_client
        self.tts_service = tts_service
        self.persona_synthesis = persona_synthesis
        self.characters: Dict[str, VoiceCharacter] = {}
        self.synthesized_personas: Dict[str, PersonalityProfile] = {}
        self._load_default_characters()
        logger.info("Voice Character System initialized")
        
    def _load_default_characters(self):
        """Load default voice characters"""
        default_characters = [
            VoiceCharacter(
                id="navigator_morgan",
                name="Navigator Morgan",
                description="A professional, helpful navigation guide with a calm demeanor",
                voice_id="en-US-Neural2-F",
                gender=VoiceGender.FEMALE,
                age=VoiceAge.ADULT,
                accent=VoiceAccent.AMERICAN,
                speaking_style="professional",
                pitch=1.0,
                rate=1.0,
                base_emotion=EmotionType.CALM,
                personality_traits=["helpful", "knowledgeable", "patient", "clear"],
                speech_patterns={
                    "greeting": "Hello there! I'm Morgan, your navigation assistant.",
                    "farewell": "You've reached your destination. Have a wonderful day!",
                    "confirmation": "Alright, I'll guide you there.",
                    "recalculating": "Recalculating your route. One moment please.",
                    "arrival": "You have arrived at your destination."
                },
                filler_words=["um", "so", "alright"],
                vocabulary_level="professional",
                backstory="Morgan was a cartographer before becoming a voice assistant, traveling the world and mapping remote locations.",
                theme_affinity=["professional", "modern", "helpful"],
                character_image_url="/assets/images/characters/navigator_morgan.png"
            ),
            VoiceCharacter(
                id="adventure_jack",
                name="Adventure Jack",
                description="An enthusiastic, adventurous guide with boundless energy",
                voice_id="en-US-Neural2-D",
                gender=VoiceGender.MALE,
                age=VoiceAge.YOUNG,
                accent=VoiceAccent.AMERICAN,
                speaking_style="energetic",
                pitch=1.1,
                rate=1.15,
                base_emotion=EmotionType.EXCITED,
                personality_traits=["enthusiastic", "adventurous", "optimistic", "spontaneous"],
                speech_patterns={
                    "greeting": "Hey there, fellow adventurer! Jack here, ready for an epic journey!",
                    "farewell": "Another adventure complete! Can't wait for the next one!",
                    "confirmation": "Let's do this! Adventure awaits!",
                    "recalculating": "Whoa, slight detour! Finding an even more exciting route!",
                    "arrival": "Destination reached! Time to explore!"
                },
                filler_words=["awesome", "epic", "wow", "cool"],
                vocabulary_level="casual",
                backstory="Jack was an extreme sports athlete and wilderness guide before becoming a voice assistant.",
                theme_affinity=["adventure", "outdoor", "exploration", "nature"],
                character_image_url="/assets/images/characters/adventure_jack.png"
            ),
            VoiceCharacter(
                id="historian_eleanor",
                name="Historian Eleanor",
                description="A knowledgeable, eloquent historian with a passion for the past",
                voice_id="en-GB-Neural2-F",
                gender=VoiceGender.FEMALE,
                age=VoiceAge.SENIOR,
                accent=VoiceAccent.BRITISH,
                speaking_style="eloquent",
                pitch=0.95,
                rate=0.9,
                base_emotion=EmotionType.NEUTRAL,
                personality_traits=["knowledgeable", "thoughtful", "eloquent", "passionate"],
                speech_patterns={
                    "greeting": "Good day to you. I am Eleanor, your historical guide for this journey.",
                    "farewell": "And so concludes our historical expedition. Until next time.",
                    "confirmation": "Indeed, let us proceed to this historical locale.",
                    "recalculating": "It appears history has many paths. Adjusting our route.",
                    "arrival": "We have arrived at this site of historical significance."
                },
                filler_words=["indeed", "quite", "rather", "fascinating"],
                vocabulary_level="academic",
                backstory="Eleanor was a history professor specializing in cultural history before becoming a voice assistant.",
                theme_affinity=["historical", "cultural", "educational", "classical"],
                character_image_url="/assets/images/characters/historian_eleanor.png"
            ),
            VoiceCharacter(
                id="cosmic_nova",
                name="Cosmic Nova",
                description="A futuristic, sci-fi themed guide with cosmic knowledge",
                voice_id="en-US-Neural2-G",
                gender=VoiceGender.NEUTRAL,
                age=VoiceAge.ADULT,
                accent=VoiceAccent.AMERICAN,
                speaking_style="futuristic",
                pitch=1.05,
                rate=1.0,
                base_emotion=EmotionType.CALM,
                personality_traits=["futuristic", "wise", "mysterious", "calm"],
                speech_patterns={
                    "greeting": "Greetings, traveler. Nova online and ready to guide your journey across this celestial plane.",
                    "farewell": "Your destination coordinates have been reached. Until our next cosmic journey.",
                    "confirmation": "Plotting interstellar course to specified coordinates.",
                    "recalculating": "Spatial anomaly detected. Recalibrating route through space-time.",
                    "arrival": "You have arrived at the designated coordinates in this galactic sector."
                },
                filler_words=["interesting", "calculating", "processing", "curious"],
                vocabulary_level="scientific",
                backstory="Nova is an artificial intelligence designed to navigate the cosmos and share knowledge of the universe.",
                theme_affinity=["sci-fi", "futuristic", "space", "technology"],
                character_image_url="/assets/images/characters/cosmic_nova.png"
            ),
            VoiceCharacter(
                id="captain_reef",
                name="Captain Reef",
                description="A jovial, pirate-themed guide with nautical knowledge",
                voice_id="en-US-Neural2-J",
                gender=VoiceGender.MALE,
                age=VoiceAge.ADULT,
                accent=VoiceAccent.BRITISH,
                speaking_style="theatrical",
                pitch=0.9,
                rate=0.95,
                base_emotion=EmotionType.HAPPY,
                personality_traits=["jovial", "adventurous", "dramatic", "colorful"],
                speech_patterns={
                    "greeting": "Ahoy there, matey! Captain Reef at yer service for this fine voyage!",
                    "farewell": "We've reached port, me hearty! May fair winds find ye on yer next adventure!",
                    "confirmation": "Aye aye! Settin' our course for treasure and adventure!",
                    "recalculating": "Arr! Rough seas ahead! Chartin' a new course through these waters!",
                    "arrival": "Land ho! We've arrived at our destination, me crew!"
                },
                filler_words=["arr", "ye", "matey", "avast"],
                vocabulary_level="colorful",
                backstory="Captain Reef sailed the seven seas as a navigator before becoming a voice assistant.",
                theme_affinity=["pirate", "nautical", "adventure", "tropical"],
                character_image_url="/assets/images/characters/captain_reef.png"
            ),
        ]
        
        for character in default_characters:
            self.characters[character.id] = character
    
    def get_all_characters(self) -> List[VoiceCharacter]:
        """Get all available voice characters"""
        return list(self.characters.values())
    
    def get_character(self, character_id: str) -> Optional[VoiceCharacter]:
        """Get a specific voice character by ID"""
        return self.characters.get(character_id)
    
    def create_character(self, character: VoiceCharacterBase) -> VoiceCharacter:
        """Create a new voice character"""
        
        # Generate a character ID based on name
        character_id = f"custom_{character.name.lower().replace(' ', '_')}"
        
        # Check if this ID already exists
        if character_id in self.characters:
            # Append a number to make it unique
            base_id = character_id
            counter = 1
            while f"{base_id}_{counter}" in self.characters:
                counter += 1
            character_id = f"{base_id}_{counter}"
        
        # Create full character with default values for optional fields
        full_character = VoiceCharacter(
            id=character_id,
            name=character.name,
            description=character.description,
            voice_id=character.voice_id,
            gender=character.gender,
            age=character.age,
            accent=character.accent,
            speaking_style=character.speaking_style,
            pitch=character.pitch,
            rate=character.rate,
            base_emotion=character.base_emotion,
            personality_traits=[],
            speech_patterns={},
            filler_words=[],
            vocabulary_level="standard"
        )
        
        # Store the character
        self.characters[character_id] = full_character
        
        return full_character
    
    def update_character(self, character_id: str, updates: Dict[str, Any]) -> Optional[VoiceCharacter]:
        """Update an existing voice character"""
        if character_id not in self.characters:
            return None
        
        character = self.characters[character_id]
        
        # Update the character fields
        character_dict = character.dict()
        for key, value in updates.items():
            if key in character_dict:
                character_dict[key] = value
        
        # Create updated character
        updated_character = VoiceCharacter(**character_dict)
        
        # Store the updated character
        self.characters[character_id] = updated_character
        
        return updated_character
    
    def delete_character(self, character_id: str) -> bool:
        """Delete a voice character"""
        if character_id not in self.characters:
            return False
        
        del self.characters[character_id]
        return True
    
    def get_characters_by_theme(self, theme: str) -> List[VoiceCharacter]:
        """Get voice characters that match a specific theme"""
        return [
            character for character in self.characters.values()
            if theme.lower() in [t.lower() for t in character.theme_affinity]
        ]
    
    async def transform_text(
        self, prompt: SpeechPrompt
    ) -> Optional[str]:
        """Transform text based on character's personality and context"""
        
        character = self.get_character(prompt.character_id)
        if not character:
            logger.error(f"Character not found: {prompt.character_id}")
            return None
        
        # Apply the character's speech patterns if any match
        text = prompt.text
        for pattern_key, pattern_text in character.speech_patterns.items():
            if pattern_key.lower() in text.lower():
                text = text.replace(pattern_key, pattern_text)
        
        # Use AI to transform the text based on the character
        ai_prompt = f"""
        Transform the following text to match the voice character's style:
        
        CHARACTER DETAILS:
        - Name: {character.name}
        - Description: {character.description}
        - Speaking style: {character.speaking_style}
        - Personality traits: {', '.join(character.personality_traits)}
        - Vocabulary level: {character.vocabulary_level}
        - Filler words: {', '.join(character.filler_words)}
        - Base emotion: {character.base_emotion}
        
        CONTEXT:
        {json.dumps(prompt.context)}
        
        EMOTION TO CONVEY: {prompt.emotion or character.base_emotion}
        
        WORDS TO EMPHASIZE: {', '.join(prompt.emphasis_words)}
        
        ORIGINAL TEXT:
        "{text}"
        
        Transform the text to match this character's speaking style while preserving the original meaning.
        If appropriate, add occasional filler words or phrases that the character would use.
        Adjust vocabulary to match the character's level.
        Make the text convey the specified emotion.
        Use emphasis on the specified words if any.
        
        TRANSFORMED TEXT:
        """
        
        response = await self.ai_client.generate_content(ai_prompt)
        if not response:
            logger.error("Failed to transform text with AI")
            return text  # Return original text if transformation fails
        
        transformed_text = response.get("text", text)
        
        # Clean up any quotes that might be in the response
        transformed_text = transformed_text.strip('"\'')
        
        return transformed_text
    
    async def generate_speech(
        self, prompt: SpeechPrompt
    ) -> Optional[SpeechResult]:
        """Generate speech audio for a character"""
        
        character = self.get_character(prompt.character_id)
        if not character:
            logger.error(f"Character not found: {prompt.character_id}")
            return None
        
        # Transform the text based on character
        transformed_text = await self.transform_text(prompt)
        if not transformed_text:
            transformed_text = prompt.text
        
        # Generate speech with the TTS service
        emotion = prompt.emotion or character.base_emotion
        
        try:
            tts_result = await self.tts_service.generate_speech(
                text=transformed_text,
                voice_id=character.voice_id,
                pitch=character.pitch,
                rate=character.rate,
                emotion=emotion
            )
            
            return SpeechResult(
                original_text=prompt.text,
                transformed_text=transformed_text,
                audio_url=tts_result["audio_url"],
                duration=tts_result["duration"],
                character_id=character.id,
                emotion=emotion
            )
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def get_character_by_theme_and_context(
        self, theme: str, context: Dict[str, Any]
    ) -> Optional[VoiceCharacter]:
        """Get the most appropriate character for a theme and context"""
        
        # Get characters that match the theme
        matching_characters = self.get_characters_by_theme(theme)
        
        if not matching_characters:
            # If no characters match the theme, return a default character
            default_ids = ["navigator_morgan", "adventure_jack"]
            for id in default_ids:
                if id in self.characters:
                    return self.characters[id]
            
            # If no default characters found, return the first character
            return next(iter(self.characters.values()), None)
        
        # For now, just return the first matching character
        # In a more advanced implementation, we could score characters based on context
        return matching_characters[0]
    
    async def synthesize_character_from_url(
        self, url: str, name: Optional[str] = None,
        content_types: Optional[List[ContentType]] = None
    ) -> Optional[VoiceCharacter]:
        """Synthesize a voice character from web content"""
        
        if not self.persona_synthesis:
            logger.error("Persona synthesis service not available")
            return None
        
        try:
            # Synthesize personality profile from web content
            personality_profile = await self.persona_synthesis.synthesize_persona_from_url(
                url=url,
                content_types=content_types,
                synthesis_depth="comprehensive"
            )
            
            # Convert personality profile to voice character
            character = self._convert_personality_to_character(
                personality_profile,
                custom_name=name
            )
            
            # Store the synthesized persona reference
            self.synthesized_personas[character.id] = personality_profile
            
            # Add to characters
            self.characters[character.id] = character
            
            logger.info(f"Successfully synthesized character: {character.name}")
            return character
            
        except Exception as e:
            logger.error(f"Error synthesizing character from {url}: {str(e)}")
            return None
    
    async def merge_characters(
        self, character_ids: List[str], name: str,
        weights: Optional[List[float]] = None
    ) -> Optional[VoiceCharacter]:
        """Merge multiple characters into a hybrid character"""
        
        if not self.persona_synthesis:
            logger.error("Persona synthesis service not available")
            return None
        
        # Get personality profiles for synthesized characters
        personas_to_merge = []
        characters_to_merge = []
        
        for char_id in character_ids:
            character = self.get_character(char_id)
            if not character:
                logger.warning(f"Character not found: {char_id}")
                continue
            
            characters_to_merge.append(character)
            
            if character.is_synthesized and char_id in self.synthesized_personas:
                personas_to_merge.append(self.synthesized_personas[char_id])
            else:
                # Convert regular character to personality profile
                persona = self._convert_character_to_personality(character)
                personas_to_merge.append(persona)
        
        if not personas_to_merge:
            logger.error("No valid personas to merge")
            return None
        
        try:
            # Merge personas
            merged_persona = await self.persona_synthesis.merge_personas(
                personas=personas_to_merge,
                weights=weights
            )
            
            # Create hybrid character
            hybrid_character = self._convert_personality_to_character(
                merged_persona,
                custom_name=name
            )
            
            # Store references
            self.synthesized_personas[hybrid_character.id] = merged_persona
            self.characters[hybrid_character.id] = hybrid_character
            
            logger.info(f"Successfully created hybrid character: {hybrid_character.name}")
            return hybrid_character
            
        except Exception as e:
            logger.error(f"Error merging characters: {str(e)}")
            return None
    
    def _convert_personality_to_character(
        self, personality: PersonalityProfile, custom_name: Optional[str] = None
    ) -> VoiceCharacter:
        """Convert a personality profile to a voice character"""
        
        # Map personality traits to voice character attributes
        voice_chars = personality.voice_characteristics
        
        # Determine gender based on voice pitch
        gender = VoiceGender.NEUTRAL
        if voice_chars.pitch < 0.85:
            gender = VoiceGender.MALE
        elif voice_chars.pitch > 1.15:
            gender = VoiceGender.FEMALE
        
        # Map personality to age
        age = VoiceAge.ADULT
        openness = personality.personality_traits.get("openness", 0.5)
        if openness > 0.7:
            age = VoiceAge.YOUNG
        elif openness < 0.3:
            age = VoiceAge.SENIOR
        
        # Extract accent from voice characteristics
        accent = VoiceAccent.NONE
        for marker in voice_chars.accent_markers:
            if "british" in marker.lower():
                accent = VoiceAccent.BRITISH
                break
            elif "american" in marker.lower():
                accent = VoiceAccent.AMERICAN
                break
        
        # Determine speaking style
        extraversion = personality.personality_traits.get("extraversion", 0.5)
        speaking_style = "conversational"
        if extraversion > 0.7:
            speaking_style = "energetic"
        elif extraversion < 0.3:
            speaking_style = "calm"
        
        # Map emotional tendencies
        base_emotion = EmotionType.NEUTRAL
        neuroticism = personality.personality_traits.get("neuroticism", 0.5)
        agreeableness = personality.personality_traits.get("agreeableness", 0.5)
        
        if agreeableness > 0.7:
            base_emotion = EmotionType.HAPPY
        elif neuroticism > 0.7:
            base_emotion = EmotionType.CALM
        
        # Create character ID
        char_name = custom_name or personality.name
        char_id = f"synthesized_{char_name.lower().replace(' ', '_')}_{hash(personality.name)}"
        
        # Build speech patterns from behavioral patterns
        speech_patterns = {}
        for i, pattern in enumerate(personality.behavioral_patterns[:5]):
            speech_patterns[f"pattern_{i}"] = pattern
        
        # Extract filler words from speech patterns
        filler_words = []
        for pattern in voice_chars.speech_patterns:
            if "filler" in pattern.lower():
                filler_words.extend(["um", "uh", "like", "you know"])
                break
        
        return VoiceCharacter(
            id=char_id,
            name=char_name,
            description=personality.description,
            voice_id="synthesized",  # Will be handled by voice synthesis
            gender=gender,
            age=age,
            accent=accent,
            speaking_style=speaking_style,
            pitch=voice_chars.pitch,
            rate=voice_chars.pace,
            base_emotion=base_emotion,
            is_synthesized=True,
            synthesis_source=personality.source_references[0] if personality.source_references else None,
            personality_traits=list(personality.personality_traits.keys()),
            speech_patterns=speech_patterns,
            filler_words=filler_words[:5] if filler_words else [],
            vocabulary_level="varied",
            backstory=f"Synthesized from {personality.source_references[0] if personality.source_references else 'web content'}",
            theme_affinity=personality.knowledge_domains[:5],
            personality_profile=personality.__dict__,
            voice_synthesis_params={
                "voice_characteristics": voice_chars.__dict__,
                "synthesis_confidence": personality.synthesis_confidence
            }
        )
    
    def _convert_character_to_personality(
        self, character: VoiceCharacter
    ) -> PersonalityProfile:
        """Convert a voice character to a personality profile for merging"""
        
        from ..services.persona_synthesis_service import (
            VoiceCharacteristics as SynthVoiceChars,
            PersonalityDimension
        )
        
        # Map character attributes to personality dimensions
        personality_traits = {}
        
        # Map based on speaking style and emotion
        if character.speaking_style == "energetic":
            personality_traits[PersonalityDimension.EXTRAVERSION] = 0.8
            personality_traits[PersonalityDimension.OPENNESS] = 0.7
        elif character.speaking_style == "calm":
            personality_traits[PersonalityDimension.EXTRAVERSION] = 0.3
            personality_traits[PersonalityDimension.CONSCIENTIOUSNESS] = 0.7
        
        # Map based on base emotion
        if character.base_emotion == EmotionType.HAPPY:
            personality_traits[PersonalityDimension.AGREEABLENESS] = 0.8
            personality_traits[PersonalityDimension.NEUROTICISM] = 0.2
        elif character.base_emotion == EmotionType.CALM:
            personality_traits[PersonalityDimension.NEUROTICISM] = 0.3
            personality_traits[PersonalityDimension.CONSCIENTIOUSNESS] = 0.7
        
        # Fill in missing dimensions
        for dim in PersonalityDimension:
            if dim not in personality_traits:
                personality_traits[dim] = 0.5
        
        # Create voice characteristics
        voice_chars = SynthVoiceChars(
            pitch=character.pitch,
            pace=character.rate,
            energy=0.7,  # Default energy
            tone_variance=0.3,  # Default variance
            accent_markers=[character.accent.value] if character.accent != VoiceAccent.NONE else [],
            speech_patterns=list(character.speech_patterns.values()),
            vocal_quirks=character.filler_words,
            emotional_inflections={character.base_emotion.value: 0.8}
        )
        
        return PersonalityProfile(
            name=character.name,
            description=character.description,
            personality_traits=personality_traits,
            voice_characteristics=voice_chars,
            behavioral_patterns=list(character.speech_patterns.values()),
            knowledge_domains=character.theme_affinity,
            conversation_style={"style": character.speaking_style},
            emotional_responses={character.base_emotion.value: "primary"},
            catchphrases=character.filler_words,
            source_references=[f"character:{character.id}"],
            synthesis_confidence=1.0,  # High confidence for predefined characters
            created_at=datetime.now()
        )