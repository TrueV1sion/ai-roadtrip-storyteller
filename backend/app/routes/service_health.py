"""
Service-specific health check endpoint that tests external services.
This endpoint checks Google Maps and Gemini AI (Vertex AI) services.
"""
from typing import Dict, Any
from datetime import datetime
import time
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Service Health"])


async def check_google_maps_service() -> Dict[str, Any]:
    """Check Google Maps service availability."""
    try:
        start_time = time.time()
        
        # Check if API key is configured
        if not settings.GOOGLE_MAPS_API_KEY:
            return {
                "status": "not_configured",
                "message": "Google Maps API key not configured",
                "response_time_ms": None
            }
        
        # In a real implementation, you might want to make a simple geocoding request
        # For now, we'll just check configuration
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Google Maps health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_gemini_ai_service() -> Dict[str, Any]:
    """Check Gemini AI (Vertex AI) service availability."""
    try:
        start_time = time.time()
        
        # Check if project ID is configured
        if not settings.GOOGLE_AI_PROJECT_ID:
            return {
                "status": "not_configured",
                "message": "Google AI project ID not configured",
                "response_time_ms": None
            }
        
        # Try to import and initialize the client
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            # Initialize Vertex AI
            vertexai.init(
                project=settings.GOOGLE_AI_PROJECT_ID,
                location=settings.GOOGLE_AI_LOCATION,
            )
            
            # Try to load the model (this will fail with 403 if permissions are wrong)
            model = GenerativeModel(settings.GOOGLE_AI_MODEL)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2)
            }
            
        except Exception as e:
            error_str = str(e)
            response_time = (time.time() - start_time) * 1000
            
            # Check for common permission errors
            if "403" in error_str:
                return {
                    "status": "permission_denied",
                    "error": "403 Forbidden - Check Vertex AI permissions",
                    "details": {
                        "possible_causes": [
                            "Vertex AI API not enabled",
                            "Service account lacks 'Vertex AI User' role",
                            "Project billing not enabled",
                            "Invalid credentials"
                        ],
                        "project_id": settings.GOOGLE_AI_PROJECT_ID,
                        "location": settings.GOOGLE_AI_LOCATION,
                        "model": settings.GOOGLE_AI_MODEL
                    },
                    "response_time_ms": round(response_time, 2)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": error_str,
                    "response_time_ms": round(response_time, 2)
                }
        
    except Exception as e:
        logger.error(f"Gemini AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


@router.get("/health/services")
async def service_health_check():
    """
    Check health status of external services.
    Returns overall status as 'degraded' if any service has issues.
    """
    # Run health checks
    google_maps_health = await check_google_maps_service()
    gemini_ai_health = await check_gemini_ai_service()
    
    # Determine overall status
    overall_status = "healthy"
    
    # Check if any service is unhealthy or has permission issues
    if google_maps_health["status"] in ["unhealthy", "permission_denied"]:
        overall_status = "degraded"
    if gemini_ai_health["status"] in ["unhealthy", "permission_denied"]:
        overall_status = "degraded"
    
    # Build response
    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "google_maps": google_maps_health["status"],
            "gemini_ai": gemini_ai_health["status"]
        },
        "details": {
            "google_maps": google_maps_health,
            "gemini_ai": gemini_ai_health
        }
    }
    
    # Return appropriate status code
    if overall_status == "degraded":
        return JSONResponse(
            content=response_data,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return response_data


@router.get("/health/services/gemini-ai/diagnose")
async def diagnose_gemini_ai():
    """
    Detailed diagnosis of Gemini AI authentication issues.
    Helpful for debugging 403 errors.
    """
    import os
    
    diagnosis = {
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": {
            "project_id": settings.GOOGLE_AI_PROJECT_ID,
            "location": settings.GOOGLE_AI_LOCATION,
            "model": settings.GOOGLE_AI_MODEL,
            "project_id_configured": bool(settings.GOOGLE_AI_PROJECT_ID)
        },
        "environment": {
            "GOOGLE_APPLICATION_CREDENTIALS": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "running_on_gcp": bool(os.getenv("K_SERVICE") or os.getenv("GAE_ENV"))
        },
        "recommendations": []
    }
    
    # Check configuration
    if not settings.GOOGLE_AI_PROJECT_ID:
        diagnosis["recommendations"].append(
            "Set GOOGLE_AI_PROJECT_ID environment variable"
        )
    
    # Check authentication
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not diagnosis["environment"]["running_on_gcp"]:
        diagnosis["recommendations"].append(
            "Set GOOGLE_APPLICATION_CREDENTIALS to service account key file path"
        )
        diagnosis["recommendations"].append(
            "Or run: gcloud auth application-default login"
        )
    
    # Try to test the connection
    try:
        health = await check_gemini_ai_service()
        diagnosis["health_check"] = health
        
        if health["status"] == "permission_denied":
            diagnosis["recommendations"].extend([
                "Enable Vertex AI API: gcloud services enable aiplatform.googleapis.com",
                "Grant service account 'Vertex AI User' role",
                "Ensure project has billing enabled"
            ])
    except Exception as e:
        diagnosis["health_check"] = {
            "status": "error",
            "error": str(e)
        }
    
    return diagnosis