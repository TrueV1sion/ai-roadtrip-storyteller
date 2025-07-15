from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64

from app.services.stt_service import stt_service # Import the new service
from app.core.logger import get_logger
from app.core.csrf import set_csrf_cookie, get_csrf_token_from_header

logger = get_logger(__name__)
router = APIRouter()

class TranscriptionRequest(BaseModel):
    audio_base64: str # Expect base64 encoded audio string
    language_code: str = "en-US"
    # Add other parameters like sample_rate if needed by the client

class TranscriptionResponse(BaseModel):
    transcript: Optional[str]
    error: Optional[str] = None

@router.post("/stt/transcribe", response_model=TranscriptionResponse, tags=["Utilities"])
async def transcribe_audio_endpoint(
    request_body: TranscriptionRequest = Body(...)
    # Alternatively, use UploadFile: audio_file: UploadFile = File(...)
):
    """
    Receives base64 encoded audio data and returns the transcription.
    """
    try:
        # Decode base64 audio data
        try:
            audio_content = base64.b64decode(request_body.audio_base64)
        except Exception as decode_error:
            logger.error(f"Base64 decoding failed: {decode_error}")
            raise HTTPException(status_code=400, detail="Invalid base64 audio data")

        # Transcribe using the service
        transcript = stt_service.transcribe_audio(
            audio_content=audio_content,
            language_code=request_body.language_code
            # Pass sample_rate_hertz if provided and needed
        )

        if transcript is None:
            # Service handles logging errors, return a generic failure message
            return TranscriptionResponse(transcript=None, error="Transcription failed")

        return TranscriptionResponse(transcript=transcript)

    except HTTPException as http_exc:
        raise http_exc # Re-raise client errors
    except Exception as e:
        logger.error(f"Error during transcription endpoint processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during transcription")

# TODO: Add this router to main.py

# --- Directions Endpoint ---

# Import the service and potentially request/response schemas
from app.services.directions_service import directions_service
# from pydantic import BaseModel # Already imported
from typing import List, Optional, Any # Already imported

class DirectionsRequest(BaseModel):
    origin: str
    destination: str
    mode: Optional[str] = "driving"
    waypoints: Optional[List[str]] = None
    optimize_waypoints: Optional[bool] = False
    # Add departure_time if needed, handle datetime parsing

class DirectionsResponse(BaseModel):
    # Return the raw response from Google Maps API for flexibility on the client
    # Alternatively, define a stricter schema for legs, steps, polylines etc.
    routes: List[Dict[str, Any]]


@router.post("/directions", response_model=DirectionsResponse, tags=["Utilities"])
async def get_directions_endpoint(request_body: DirectionsRequest):
    """
    Get directions between two points using Google Maps Directions API.
    """
    try:
        directions_result = directions_service.get_directions(
            origin=request_body.origin,
            destination=request_body.destination,
            mode=request_body.mode,
            waypoints=request_body.waypoints,
            optimize_waypoints=request_body.optimize_waypoints
        )

        if directions_result is None:
            # Service logs the specific error
            raise HTTPException(status_code=500, detail="Failed to retrieve directions from provider.")
        if not directions_result: # Empty list means no route found
             raise HTTPException(status_code=404, detail="No route found between the specified points.")

        # Return the raw directions result (list of routes)
        return DirectionsResponse(routes=directions_result)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in directions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching directions.")
        
class CSRFTokenResponse(BaseModel):
    success: bool

class CSRFTokenResponseWithToken(CSRFTokenResponse):
    csrf_token: str

@router.get("/csrf-token", response_model=CSRFTokenResponseWithToken, tags=["Security"])
async def get_csrf_token(response: Response):
    """
    Generate and return a new CSRF token as an HTTP-only cookie and in response body.
    The frontend should make a GET request to this endpoint before submitting any forms.
    This endpoint supports both web and mobile clients by providing the token in multiple ways.
    """
    try:
        from app.core.csrf import generate_csrf_token, CSRF_HEADER_NAME
        
        # Generate token
        token = generate_csrf_token()
        
        # Set in cookie for web clients
        set_csrf_cookie(response)
        
        # Also set in header for mobile clients
        response.headers[CSRF_HEADER_NAME] = token
        
        # Return token in body as well for maximum compatibility
        return CSRFTokenResponseWithToken(success=True, csrf_token=token)
    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate CSRF token.")