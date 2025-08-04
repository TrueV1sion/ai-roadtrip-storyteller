"""
Simple info endpoint to debug Vertex AI access
"""

from fastapi import FastAPI
import os
import json

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "RoadTrip MVP Backend", "version": "1.0.0-mvp"}

@app.get("/info")
async def info():
    """Show environment and configuration info"""
    return {
        "environment": {
            "GOOGLE_AI_PROJECT_ID": os.getenv("GOOGLE_AI_PROJECT_ID", "not set"),
            "GOOGLE_AI_LOCATION": os.getenv("GOOGLE_AI_LOCATION", "not set"),
            "GOOGLE_APPLICATION_CREDENTIALS": "set" if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") else "not set",
            "PROJECT_ID": os.getenv("PROJECT_ID", "not set"),
            "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "not set"),
        },
        "service_account": {
            "available": os.path.exists("/var/run/secrets/cloud.google.com/service-account/key.json") if os.getenv("K_SERVICE") else False
        },
        "recommendations": [
            "Use google-cloud-aiplatform library directly",
            "Model name should be 'gemini-pro' without project path",
            "Ensure service account has Vertex AI User role",
            "Consider using ADC (Application Default Credentials)"
        ]
    }

@app.get("/health")
async def health():
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": "2025-07-21T12:00:00Z",
        "message": "Backend is running with Vertex AI configuration"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)