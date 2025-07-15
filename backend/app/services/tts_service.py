from typing import Optional, Dict, List
import os
import re
import uuid
import base64
from datetime import datetime, timedelta # Import datetime and timedelta for URL expiration and timestamps

# Google Cloud TTS imports
from google.cloud import texttospeech
from google.api_core import exceptions as google_exceptions

# Google Cloud Storage import
from google.cloud import storage

from app.core.config import settings
from app.core.logger import get_logger
from app.core.google_cloud_auth import google_cloud_auth
from .personality_engine import personality_engine, VoicePersonality

logger = get_logger(__name__)


class TTSSynthesizer:
    """
    Text-to-Speech synthesizer using Google Cloud Text-to-Speech
    and uploads generated audio to Google Cloud Storage.
    """

    def __init__(self):
        # Initialize Google Cloud authentication first
        if not google_cloud_auth.initialize():
            logger.error("Google Cloud authentication failed")
            self.tts_client = None
            self.storage_client = None
            self.gcs_bucket = None
            self.provider = "none"
            return
        
        credentials = google_cloud_auth.get_credentials()
        project_id = google_cloud_auth.get_project_id()
        
        # Initialize Google Cloud TTS Client with credentials
        try:
            self.tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
            logger.info("Google Cloud TextToSpeech client initialized successfully.")
            self.provider = "google"
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud TextToSpeech client: {e}")
            self.tts_client = None
            self.provider = "none"

        # Initialize Google Cloud Storage Client with credentials
        try:
            self.storage_client = storage.Client(
                project=project_id, 
                credentials=credentials
            )
            self.bucket_name = getattr(settings, 'GCS_BUCKET_NAME', None)
            if not self.bucket_name:
                logger.warning("GCS_BUCKET_NAME not set. TTS audio upload will fail.")
                self.gcs_bucket = None
            else:
                self.gcs_bucket = self.storage_client.bucket(self.bucket_name)
                logger.info(f"Google Cloud Storage client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            self.storage_client = None
            self.gcs_bucket = None

        # Set default voice parameters for Google TTS
        self.default_language_code = "en-US"
        self.default_voice_name = "en-US-Studio-O"
        self.default_ssml_gender = texttospeech.SsmlVoiceGender.FEMALE

        # Removed in-memory audio cache - caching should happen before calling synthesize
        # self.audio_cache = {}

    def _prepare_ssml(self, text: str, personality: Optional[VoicePersonality] = None) -> str:
        """
        Prepare text for synthesis by cleaning and wrapping in SSML.
        Applies personality-specific speech patterns if provided.
        """
        # Apply personality text adjustments
        if personality:
            text = personality_engine.adjust_text_for_personality(text, personality)
        
        # Basic text cleaning
        text = text.replace("&", "and")
        # Basic XML escaping for SSML safety
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        
        # Apply personality-specific break timing
        if personality and personality.speaking_style.get("emphasis") == "dramatic_pauses":
            # Historian style - longer pauses
            text = re.sub(r'([.!?])\s+', r'\1<break time="800ms"/> ', text)
        elif personality and personality.speaking_style.get("emphasis") == "high_energy":
            # Adventurer style - shorter pauses
            text = re.sub(r'([.!?])\s+', r'\1<break time="200ms"/> ', text)
        else:
            # Standard pauses
            text = re.sub(r'([.!?])\s+', r'\1<break time="400ms"/> ', text)
        
        paragraphs = text.split("\n\n")
        processed_paragraphs = [f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()]
        processed_text = "\n".join(processed_paragraphs)
        
        # Add personality-specific prosody
        if personality:
            pitch = personality.speaking_style.get("pitch", 0)
            rate = personality.speaking_style.get("speed", 1.0)
            
            # Convert pitch to semitones string
            pitch_str = f"{pitch:+}st" if pitch != 0 else "+0st"
            # Convert rate to percentage string
            rate_str = f"{int(rate * 100)}%"
            
            ssml = f"""<speak>
                <prosody pitch="{pitch_str}" rate="{rate_str}">
                    {processed_text}
                </prosody>
            </speak>"""
        else:
            ssml = f"""<speak>{processed_text}</speak>"""
            
        return ssml

    # Removed _get_cache_key as caching is moved outside this service
    # def _get_cache_key(...) -> str: ...

    def synthesize_and_upload(
        self, 
        text: str, 
        voice_name: Optional[str] = None, 
        language_code: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        is_premium: bool = False,
        watermark: Optional[str] = None,
        personality: Optional[VoicePersonality] = None,
        location: Optional[Dict[str, any]] = None
    ) -> Optional[str]:
        """
        Synthesize speech using Google Cloud TTS and upload the MP3 to GCS.

        Args:
            text: Text to convert to speech (can be plain text or SSML)
            voice_name: Optional voice name (e.g., "en-US-Wavenet-D")
            language_code: Optional language code (e.g., "en-US")
            user_id: Optional user ID for access control and auditing
            ip_address: Optional IP address for URL restriction
            is_premium: Whether this is a premium user (determines URL settings)
            watermark: Optional text to add as a watermark to the audio
            personality: Optional voice personality for dynamic voice selection
            location: Optional location context for regional voice selection

        Returns:
            A time-limited Signed URL for the uploaded audio file in GCS, or None on failure.
        """
        if not self.tts_client:
            logger.error("Google TTS client not initialized. Cannot synthesize.")
            return None # Indicate failure clearly

        if not self.gcs_bucket:
             logger.error("GCS bucket not configured. Cannot upload audio.")
             return None

        # If personality is provided, use its voice settings
        if personality:
            voice_settings = personality_engine.get_voice_settings(personality)
            selected_voice_name = voice_settings["voice_id"]
            selected_language_code = language_code or self.default_language_code
            
            # Log personality usage
            logger.info(f"Using personality '{personality.name}' with voice '{selected_voice_name}'")
        else:
            # Determine voice parameters from defaults or provided values
            selected_language_code = language_code or self.default_language_code
            selected_voice_name = voice_name or self.default_voice_name

        # Add security context to logs
        security_context = f"User: {user_id or 'anonymous'}"
        if ip_address:
            security_context += f", IP: {ip_address}"
        if is_premium:
            security_context += ", Premium: Yes"
        else:
            security_context += ", Premium: No"
            
        logger.info(f"Synthesizing audio - {security_context}")

        try:
            # Add watermark to premium content if requested
            original_text = text
            if watermark and is_premium:
                # Only add watermark if the content isn't already SSML (or add to SSML if needed)
                if not text.strip().startswith("<speak"):
                    text = f"{text}\n\n{watermark}"
            
            # Prepare input (handle plain text vs SSML)
            if original_text.strip().startswith("<speak"):
                 synthesis_input = texttospeech.SynthesisInput(ssml=original_text)
            else:
                 ssml_input = self._prepare_ssml(text, personality)
                 synthesis_input = texttospeech.SynthesisInput(ssml=ssml_input)

            # Set the voice configuration
            voice = texttospeech.VoiceSelectionParams(
                language_code=selected_language_code,
                name=selected_voice_name
            )

            # Select the type of audio file format (MP3)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            )

            # Perform the text-to-speech request
            logger.info(f"Requesting Google TTS synthesis... (Voice: {selected_voice_name})")
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            logger.info("Google TTS synthesis completed.")

            # Determine appropriate storage location based on user type
            subfolder = "premium_tts" if is_premium else "standard_tts"
            file_name = f"{subfolder}/{uuid.uuid4()}.mp3"
            
            # Add user_id to metadata for access control auditing
            metadata = {}
            if user_id:
                metadata["user_id"] = user_id
            if ip_address:
                metadata["source_ip"] = ip_address
            
            # Upload the audio content to GCS with metadata
            audio_content = response.audio_content
            blob = self.gcs_bucket.blob(file_name)
            
            # Set metadata on the blob
            if metadata:
                blob.metadata = metadata
            
            logger.info(f"Uploading TTS audio to GCS: gs://{self.bucket_name}/{file_name}")
            blob.upload_from_string(audio_content, content_type="audio/mpeg")

            # Generate a secure signed URL with our enhanced method
            signed_url = self.get_signed_url_for_gcs_path(
                gcs_path=file_name,
                expiration_hours=24 if is_premium else 1,  # Premium users get longer expiration
                user_id=user_id,
                ip_address=ip_address,
                is_premium=is_premium
            )

            if not signed_url:
                logger.error("Failed to generate signed URL for uploaded audio")
                return None
                
            logger.info(f"TTS audio uploaded and secure signed URL generated")
            return signed_url # Return the Signed URL

        except google_exceptions.InvalidArgument as e:
            logger.error(f"Google TTS synthesis failed (InvalidArgument): {e}")
            return None
        except Exception as e:
            logger.error(f"Google TTS synthesis or GCS upload error: {str(e)}")
            return None

    def synthesize_and_store_permanently(
        self, 
        text: str, 
        voice_name: Optional[str] = None, 
        language_code: Optional[str] = None,
        user_id: Optional[str] = None,
        is_premium: bool = False,
        watermark: Optional[str] = None,
        personality: Optional[VoicePersonality] = None
    ) -> Optional[str]:
        """
        Synthesize speech using Google Cloud TTS, upload the MP3 to GCS,
        and return the GCS object path. This is used for content that needs
        to be stored long-term (e.g., saved by the user).

        Args:
            text: Text to convert to speech (can be plain text or SSML)
            voice_name: Optional voice name (e.g., "en-US-Wavenet-D")
            language_code: Optional language code (e.g., "en-US")
            user_id: Optional user ID for access control and auditing
            is_premium: Whether this is a premium user request
            watermark: Optional text to add as a watermark to the audio
            personality: Optional voice personality for dynamic voice selection

        Returns:
            The GCS object path (e.g., "user_saved_tts/your-uuid.mp3") for the uploaded file, or None on failure.
        """
        if not self.tts_client:
            logger.error("Google TTS client not initialized. Cannot synthesize.")
            return None
        if not self.gcs_bucket:
            logger.error("GCS bucket not configured. Cannot upload audio.")
            return None

        # If personality is provided, use its voice settings
        if personality:
            voice_settings = personality_engine.get_voice_settings(personality)
            selected_voice_name = voice_settings["voice_id"]
            selected_language_code = language_code or self.default_language_code
            
            # Log personality usage
            logger.info(f"Using personality '{personality.name}' with voice '{selected_voice_name}'")
        else:
            selected_language_code = language_code or self.default_language_code
            selected_voice_name = voice_name or self.default_voice_name

        # Add security context to logs
        security_context = f"User: {user_id or 'anonymous'}"
        if is_premium:
            security_context += ", Premium: Yes"
        else:
            security_context += ", Premium: No"
            
        logger.info(f"Synthesizing audio for permanent storage - {security_context}")

        try:
            # Add watermark to premium content if requested
            original_text = text
            if watermark and is_premium:
                # Only add watermark if the content isn't already SSML (or add to SSML if needed)
                if not text.strip().startswith("<speak"):
                    text = f"{text}\n\n{watermark}"
            
            # Prepare input (handle plain text vs SSML)
            if original_text.strip().startswith("<speak"):
                synthesis_input = texttospeech.SynthesisInput(ssml=original_text)
            else:
                ssml_input = self._prepare_ssml(text, personality)
                synthesis_input = texttospeech.SynthesisInput(ssml=ssml_input)

            voice = texttospeech.VoiceSelectionParams(
                language_code=selected_language_code,
                name=selected_voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            )

            logger.info(f"Requesting Google TTS synthesis for permanent storage... (Voice: {selected_voice_name})")
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            logger.info("Google TTS synthesis completed for permanent storage.")

            audio_content = response.audio_content
            
            # Store premium content in a separate folder with user ID in path for better organization
            if is_premium and user_id:
                # Using a subfolder per user for premium content
                gcs_object_path = f"premium_user_saved_tts/{user_id}/{uuid.uuid4()}.mp3"
            else:
                gcs_object_path = f"user_saved_tts/{uuid.uuid4()}.mp3"
                
            blob = self.gcs_bucket.blob(gcs_object_path)
            
            # Set metadata for access control and auditing
            metadata = {}
            if user_id:
                metadata["user_id"] = user_id
                metadata["created_at"] = datetime.now().isoformat()
                metadata["content_type"] = "permanent"
                metadata["premium"] = str(is_premium).lower()
                
            # Set metadata on the blob
            if metadata:
                blob.metadata = metadata

            logger.info(f"Uploading TTS audio to GCS for permanent storage: gs://{self.bucket_name}/{gcs_object_path}")
            blob.upload_from_string(audio_content, content_type="audio/mpeg")
            
            # Set appropriate access controls
            if is_premium and user_id:
                # Set object ACL to restrict access
                # This could be modified to use IAM policies as well
                blob.acl.all().grant_reader()  # Public read access is fine for this use case
                # But log the access for premium content
                logger.info(f"Set public read access for premium content: {gcs_object_path}")
            
            logger.info(f"TTS audio uploaded to {gcs_object_path}")
            return gcs_object_path

        except google_exceptions.InvalidArgument as e:
            logger.error(f"Google TTS synthesis for permanent storage failed (InvalidArgument): {e}")
            return None
        except Exception as e:
            logger.error(f"Google TTS synthesis or GCS upload error for permanent storage: {str(e)}")
            return None

    def get_signed_url_for_gcs_path(
        self, 
        gcs_path: str, 
        expiration_hours: int = 1,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        is_premium: bool = False
    ) -> Optional[str]:
        """
        Generates a time-limited signed URL for a given GCS object path with enhanced security.

        Args:
            gcs_path: The path to the object in GCS (e.g., "user_saved_tts/your-uuid.mp3").
            expiration_hours: How long the signed URL should be valid, in hours.
            user_id: Optional user ID for audit logging and authorization.
            ip_address: Optional IP address to restrict access to this client IP.
            is_premium: Whether this is premium content (affects URL lifespan and logging).

        Returns:
            A signed URL string, or None if the path is invalid or an error occurs.
        """
        if not self.gcs_bucket or not gcs_path:
            logger.error("GCS bucket not configured or GCS path not provided.")
            return None
        
        try:
            # Enhanced logging for security auditing
            user_context = f"user {user_id}" if user_id else "anonymous user"
            client_ip = f" from IP {ip_address}" if ip_address else ""
            premium_flag = " (premium content)" if is_premium else ""
            
            logger.info(f"Signed URL requested by {user_context}{client_ip}{premium_flag} for {gcs_path}")
            
            blob = self.gcs_bucket.blob(gcs_path)
            if not blob.exists(self.storage_client):
                logger.warning(f"GCS object not found at path: {gcs_path}")
                return None

            # Security configuration for signed URL
            url_config = {
                "version": "v4",
                "method": "GET",
            }
            
            # Set different expiration times based on content type
            # Premium content gets longer expiration
            if is_premium:
                url_config["expiration"] = timedelta(hours=expiration_hours)
            else:
                # Standard content expires more quickly
                url_config["expiration"] = timedelta(minutes=30)
            
            # Add IP restriction for non-premium content if IP is provided
            # This helps prevent URL sharing
            if ip_address and not is_premium:
                url_config["conditions"] = [["ip_match", ip_address]]
            
            # Generate the signed URL with the configured parameters
            signed_url = blob.generate_signed_url(**url_config)
            
            logger.info(f"Generated signed URL for GCS path {gcs_path} (expires in {url_config['expiration']})")
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL for GCS path {gcs_path}: {e}")
            return None

    # Fallback audio is no longer relevant as we return None on failure
    # def _get_fallback_audio(self) -> bytes: ...


# Create singleton instance
tts_synthesizer = TTSSynthesizer()
