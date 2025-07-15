"""
Multilingual Support Service
Enables voice interaction in multiple languages with seamless switching
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from datetime import datetime

from ..core.cache import cache_manager
from ..core.unified_ai_client import unified_ai_client

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"
    ARABIC = "ar"
    HINDI = "hi"
    RUSSIAN = "ru"


@dataclass
class LanguageConfig:
    """Configuration for a language"""
    code: str
    name: str
    native_name: str
    tts_voice: str
    stt_model: str
    personality_adaptations: Dict[str, str]
    cultural_context: Dict[str, Any]
    number_format: str
    date_format: str
    distance_unit: str  # km or miles
    temperature_unit: str  # celsius or fahrenheit


@dataclass
class TranslationCache:
    """Cache entry for translations"""
    original_text: str
    source_language: Language
    target_language: Language
    translated_text: str
    timestamp: datetime
    context: Optional[str] = None


class MultilingualService:
    """
    Comprehensive multilingual support service featuring:
    - Automatic language detection
    - Real-time translation
    - Cultural adaptation
    - Voice personality localization
    - Context-aware translations
    - Code-switching support
    """
    
    def __init__(self):
        self.ai_client = unified_ai_client
        self.current_language = Language.ENGLISH
        self.detected_languages: List[Tuple[Language, float]] = []
        self.translation_cache: Dict[str, TranslationCache] = {}
        
        # Language configurations
        self.language_configs = self._initialize_language_configs()
        
        # Personality translations
        self.personality_translations = self._initialize_personality_translations()
        
        # Common phrases cache
        self.common_phrases = self._load_common_phrases()
        
        logger.info("Multilingual Service initialized")
    
    async def detect_language(self, text: str) -> Tuple[Language, float]:
        """
        Detect language from text
        
        Returns:
            Tuple of (detected_language, confidence)
        """
        # Check cache first
        cache_key = f"lang_detect:{text[:100]}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return Language(cached["language"]), cached["confidence"]
        
        try:
            # Use AI for language detection
            prompt = f"""Detect the language of this text and return ONLY a JSON object:
            Text: "{text}"
            
            Format: {{"language": "language_code", "confidence": 0.95}}
            
            Language codes: en, es, fr, de, it, pt, ja, ko, zh, ar, hi, ru"""
            
            result = await self.ai_client.generate_json(prompt)
            
            language = Language(result.get("language", "en"))
            confidence = float(result.get("confidence", 0.8))
            
            # Cache result
            await cache_manager.set(cache_key, {
                "language": language.value,
                "confidence": confidence
            }, ttl=3600)
            
            # Track detected languages
            self.detected_languages.append((language, confidence))
            if len(self.detected_languages) > 10:
                self.detected_languages.pop(0)
            
            return language, confidence
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return Language.ENGLISH, 0.5
    
    async def translate(
        self,
        text: str,
        target_language: Language,
        source_language: Optional[Language] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_language: Target language
            source_language: Source language (auto-detect if None)
            context: Context for better translation
            
        Returns:
            Translated text
        """
        # Skip if already in target language
        if source_language == target_language:
            return text
        
        # Auto-detect source language if not provided
        if source_language is None:
            source_language, _ = await self.detect_language(text)
        
        # Check cache
        cache_key = f"translate:{source_language.value}:{target_language.value}:{text[:200]}"
        if context:
            cache_key += f":{context[:50]}"
        
        cached = self.translation_cache.get(cache_key)
        if cached and (datetime.now() - cached.timestamp).seconds < 3600:
            return cached.translated_text
        
        try:
            # Build translation prompt
            prompt = f"""Translate the following text from {source_language.value} to {target_language.value}.
            Maintain the tone and style. Consider this is for a road trip storytelling app.
            
            {"Context: " + context if context else ""}
            
            Text: "{text}"
            
            Return ONLY the translated text, nothing else."""
            
            translated = await self.ai_client.generate_response(prompt)
            
            # Cache translation
            self.translation_cache[cache_key] = TranslationCache(
                original_text=text,
                source_language=source_language,
                target_language=target_language,
                translated_text=translated,
                timestamp=datetime.now(),
                context=context
            )
            
            return translated
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Return original on failure
    
    async def localize_personality(
        self,
        personality: str,
        language: Language,
        cultural_adapt: bool = True
    ) -> Dict[str, Any]:
        """
        Localize voice personality for language and culture
        
        Args:
            personality: Base personality type
            language: Target language
            cultural_adapt: Apply cultural adaptations
            
        Returns:
            Localized personality configuration
        """
        config = self.language_configs.get(language, self.language_configs[Language.ENGLISH])
        
        # Get personality translation
        personality_key = f"{personality}_{language.value}"
        localized = self.personality_translations.get(
            personality_key,
            self.personality_translations.get(f"{personality}_en", {})
        )
        
        # Apply cultural adaptations
        if cultural_adapt:
            cultural_context = config.cultural_context
            
            # Adjust formality
            if cultural_context.get("high_formality", False):
                localized["formality"] = "formal"
            
            # Adjust interaction style
            if cultural_context.get("indirect_communication", False):
                localized["directness"] = "indirect"
            
            # Adjust humor level
            if cultural_context.get("humor_style") == "subtle":
                localized["humor_level"] = "subtle"
        
        return {
            "base_personality": personality,
            "language": language.value,
            "voice_config": {
                "voice": config.tts_voice,
                "speaking_rate": localized.get("speaking_rate", 1.0),
                "pitch": localized.get("pitch", 0)
            },
            "personality_traits": localized,
            "cultural_adaptations": cultural_context if cultural_adapt else {}
        }
    
    async def adapt_content(
        self,
        content: Dict[str, Any],
        language: Language
    ) -> Dict[str, Any]:
        """
        Adapt content for language and culture
        
        Args:
            content: Content to adapt (distances, temperatures, etc.)
            language: Target language
            
        Returns:
            Adapted content
        """
        config = self.language_configs.get(language, self.language_configs[Language.ENGLISH])
        adapted = content.copy()
        
        # Convert distances
        if "distance" in content:
            if config.distance_unit == "km" and content.get("distance_unit") == "miles":
                adapted["distance"] = content["distance"] * 1.60934
                adapted["distance_unit"] = "km"
            elif config.distance_unit == "miles" and content.get("distance_unit") == "km":
                adapted["distance"] = content["distance"] / 1.60934
                adapted["distance_unit"] = "miles"
        
        # Convert temperature
        if "temperature" in content:
            if config.temperature_unit == "celsius" and content.get("temp_unit") == "fahrenheit":
                adapted["temperature"] = (content["temperature"] - 32) * 5/9
                adapted["temp_unit"] = "celsius"
            elif config.temperature_unit == "fahrenheit" and content.get("temp_unit") == "celsius":
                adapted["temperature"] = content["temperature"] * 9/5 + 32
                adapted["temp_unit"] = "fahrenheit"
        
        # Format numbers
        if "number" in content:
            adapted["formatted_number"] = self._format_number(
                content["number"],
                config.number_format
            )
        
        # Format dates
        if "date" in content:
            adapted["formatted_date"] = self._format_date(
                content["date"],
                config.date_format
            )
        
        return adapted
    
    async def get_common_phrase(
        self,
        phrase_key: str,
        language: Language,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Get a common phrase in the specified language
        
        Args:
            phrase_key: Key for the phrase
            language: Target language
            variables: Variables to substitute in phrase
            
        Returns:
            Localized phrase
        """
        # Get phrase template
        phrase_templates = self.common_phrases.get(phrase_key, {})
        template = phrase_templates.get(language.value)
        
        if not template:
            # Fallback to English
            template = phrase_templates.get("en", phrase_key)
            
            # Translate if needed
            if language != Language.ENGLISH:
                template = await self.translate(template, language)
        
        # Substitute variables
        if variables:
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", value)
        
        return template
    
    async def switch_language(self, new_language: Language):
        """
        Switch the current interaction language
        
        Args:
            new_language: Language to switch to
        """
        old_language = self.current_language
        self.current_language = new_language
        
        logger.info(f"Language switched from {old_language.value} to {new_language.value}")
        
        # Clear caches that might be language-specific
        self.translation_cache.clear()
        
        # Notify about language change
        confirmation = await self.get_common_phrase(
            "language_switched",
            new_language,
            {"language": self.language_configs[new_language].native_name}
        )
        
        return confirmation
    
    def get_language_preferences(self) -> Dict[str, Any]:
        """Get current language preferences and statistics"""
        # Analyze detected languages
        language_counts = {}
        for lang, _ in self.detected_languages:
            language_counts[lang.value] = language_counts.get(lang.value, 0) + 1
        
        # Find most common languages
        preferred_languages = sorted(
            language_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "current_language": self.current_language.value,
            "detected_languages": language_counts,
            "preferred_languages": preferred_languages,
            "available_languages": [lang.value for lang in Language],
            "translation_cache_size": len(self.translation_cache)
        }
    
    # Private methods
    
    def _initialize_language_configs(self) -> Dict[Language, LanguageConfig]:
        """Initialize language configurations"""
        return {
            Language.ENGLISH: LanguageConfig(
                code="en",
                name="English",
                native_name="English",
                tts_voice="en-US-Neural2-D",
                stt_model="en-US",
                personality_adaptations={},
                cultural_context={"humor_style": "direct", "formality": "casual"},
                number_format="1,234.56",
                date_format="MM/DD/YYYY",
                distance_unit="miles",
                temperature_unit="fahrenheit"
            ),
            Language.SPANISH: LanguageConfig(
                code="es",
                name="Spanish",
                native_name="Español",
                tts_voice="es-ES-Neural2-B",
                stt_model="es-ES",
                personality_adaptations={"warmth": "high"},
                cultural_context={"humor_style": "playful", "formality": "moderate"},
                number_format="1.234,56",
                date_format="DD/MM/YYYY",
                distance_unit="km",
                temperature_unit="celsius"
            ),
            Language.FRENCH: LanguageConfig(
                code="fr",
                name="French",
                native_name="Français",
                tts_voice="fr-FR-Neural2-B",
                stt_model="fr-FR",
                personality_adaptations={"elegance": "high"},
                cultural_context={"humor_style": "witty", "formality": "formal"},
                number_format="1 234,56",
                date_format="DD/MM/YYYY",
                distance_unit="km",
                temperature_unit="celsius"
            ),
            Language.JAPANESE: LanguageConfig(
                code="ja",
                name="Japanese",
                native_name="日本語",
                tts_voice="ja-JP-Neural2-B",
                stt_model="ja-JP",
                personality_adaptations={"politeness": "very_high"},
                cultural_context={
                    "humor_style": "subtle",
                    "formality": "formal",
                    "high_formality": True,
                    "indirect_communication": True
                },
                number_format="1,234.56",
                date_format="YYYY/MM/DD",
                distance_unit="km",
                temperature_unit="celsius"
            ),
            # Add more languages...
        }
    
    def _initialize_personality_translations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize personality translations"""
        return {
            "wise_narrator_en": {
                "tone": "wise and thoughtful",
                "speaking_rate": 0.95,
                "formality": "moderate"
            },
            "wise_narrator_es": {
                "tone": "sabio y reflexivo",
                "speaking_rate": 0.98,
                "formality": "moderate",
                "warmth": "high"
            },
            "wise_narrator_ja": {
                "tone": "知恵深く思慮深い",
                "speaking_rate": 0.92,
                "formality": "formal",
                "politeness": "high"
            },
            "enthusiastic_buddy_en": {
                "tone": "excited and friendly",
                "speaking_rate": 1.1,
                "energy": "high"
            },
            "enthusiastic_buddy_es": {
                "tone": "emocionado y amigable",
                "speaking_rate": 1.15,
                "energy": "very_high",
                "warmth": "very_high"
            },
            # Add more personality translations...
        }
    
    def _load_common_phrases(self) -> Dict[str, Dict[str, str]]:
        """Load common phrases in all languages"""
        return {
            "greeting": {
                "en": "Hello! Ready for an adventure?",
                "es": "¡Hola! ¿Listos para una aventura?",
                "fr": "Bonjour! Prêt pour une aventure?",
                "ja": "こんにちは！冒険の準備はできていますか？",
                "de": "Hallo! Bereit für ein Abenteuer?",
                "it": "Ciao! Pronti per un'avventura?"
            },
            "language_switched": {
                "en": "I've switched to {language}",
                "es": "He cambiado a {language}",
                "fr": "J'ai changé pour {language}",
                "ja": "{language}に切り替えました",
                "de": "Ich habe zu {language} gewechselt",
                "it": "Sono passato a {language}"
            },
            "navigation_turn": {
                "en": "Turn {direction} in {distance} {unit}",
                "es": "Gira a la {direction} en {distance} {unit}",
                "fr": "Tournez à {direction} dans {distance} {unit}",
                "ja": "{distance}{unit}先で{direction}に曲がってください",
                "de": "In {distance} {unit} {direction} abbiegen",
                "it": "Gira a {direction} tra {distance} {unit}"
            },
            # Add more common phrases...
        }
    
    def _format_number(self, number: float, format_style: str) -> str:
        """Format number according to locale"""
        if format_style == "1,234.56":
            return f"{number:,.2f}"
        elif format_style == "1.234,56":
            return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        elif format_style == "1 234,56":
            return f"{number:,.2f}".replace(",", " ").replace(".", ",")
        return str(number)
    
    def _format_date(self, date: datetime, format_style: str) -> str:
        """Format date according to locale"""
        format_map = {
            "MM/DD/YYYY": "%m/%d/%Y",
            "DD/MM/YYYY": "%d/%m/%Y",
            "YYYY/MM/DD": "%Y/%m/%d"
        }
        return date.strftime(format_map.get(format_style, "%Y-%m-%d"))


# Global instance
multilingual_service = MultilingualService()