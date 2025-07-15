from google.cloud import speech
from google.api_core import exceptions as google_exceptions
from typing import Optional

from app.core.logger import get_logger
from app.core.config import settings # May need specific STT settings later

logger = get_logger(__name__)

class SpeechToTextService:
    """Service for transcribing audio using Google Cloud Speech-to-Text."""

    def __init__(self):
        try:
            self.client = speech.SpeechClient()
            logger.info("Google Cloud Speech client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Speech client: {e}")
            self.client = None

    def transcribe_audio(
        self,
        audio_content: bytes,
        language_code: str = "en-US",
        sample_rate_hertz: Optional[int] = None # Optional: API can often detect this
    ) -> Optional[str]:
        """
        Transcribes audio content using Google Cloud Speech-to-Text.

        Args:
            audio_content: The audio data bytes.
            language_code: The language of the speech in the audio.
            sample_rate_hertz: The sample rate in Hertz of the audio data.

        Returns:
            The transcribed text, or None if transcription fails.
        """
        if not self.client:
            logger.error("Speech client not initialized. Cannot transcribe.")
            return None

        try:
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                # encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, # Example, adjust based on actual audio format
                # sample_rate_hertz=sample_rate_hertz, # Provide if known, otherwise API attempts detection
                language_code=language_code,
                # Add other config options as needed (e.g., model selection, punctuation)
                enable_automatic_punctuation=True,
            )

            logger.info(f"Requesting Google STT transcription (lang: {language_code})...")
            response = self.client.recognize(config=config, audio=audio)
            logger.info("Google STT transcription completed.")

            # Process results - return the most likely transcript
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                logger.info(f"Transcript: {transcript} (Confidence: {confidence:.2f})")
                return transcript
            else:
                logger.warning("Google STT returned no results.")
                return None

        except google_exceptions.InvalidArgument as e:
            logger.error(f"Google STT transcription failed (InvalidArgument): {e}")
            return None
        except Exception as e:
            logger.error(f"Error during Google STT transcription: {e}")
            return None

# Create singleton instance
stt_service = SpeechToTextService()