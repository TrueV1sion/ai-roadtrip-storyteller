#!/usr/bin/env python3
"""
Diagnose Gemini AI / Vertex AI authentication issues.
This script checks for common authentication problems that cause 403 errors.
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check environment variables and authentication setup."""
    print("=== Gemini AI / Vertex AI Authentication Diagnosis ===\n")
    
    # Check for Google Cloud project ID
    project_vars = [
        "GOOGLE_AI_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT_ID", 
        "GCP_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT"
    ]
    
    project_id = None
    for var in project_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
            project_id = value
        else:
            print(f"✗ {var}: Not set")
    
    if not project_id:
        print("\n❌ ERROR: No Google Cloud project ID found!")
        print("Set one of: GOOGLE_AI_PROJECT_ID, GOOGLE_CLOUD_PROJECT_ID, or GCP_PROJECT_ID")
        return False
    
    print("\n--- Authentication Methods ---")
    
    # Check for service account key file
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_file:
        print(f"✓ GOOGLE_APPLICATION_CREDENTIALS: {creds_file}")
        if os.path.exists(creds_file):
            print("  ✓ File exists")
        else:
            print("  ❌ File does not exist!")
    else:
        print("✗ GOOGLE_APPLICATION_CREDENTIALS: Not set")
        print("  (Will attempt to use default credentials)")
    
    # Check if running on Google Cloud
    metadata_server = os.getenv("GCE_METADATA_HOST", "metadata.google.internal")
    print(f"\n--- Google Cloud Environment ---")
    
    # Try to detect if we're on Google Cloud
    try:
        import requests
        response = requests.get(
            f"http://{metadata_server}/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=1
        )
        if response.status_code == 200:
            print("✓ Running on Google Cloud (metadata service available)")
        else:
            print("✗ Not running on Google Cloud")
    except:
        print("✗ Not running on Google Cloud (metadata service not reachable)")
    
    # Check for ADC (Application Default Credentials)
    print("\n--- Application Default Credentials ---")
    adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    if adc_path.exists():
        print(f"✓ ADC file exists: {adc_path}")
    else:
        print("✗ No ADC file found")
        print("  Run: gcloud auth application-default login")
    
    return True

def test_vertex_ai_connection():
    """Test actual Vertex AI connection."""
    print("\n--- Testing Vertex AI Connection ---")
    
    try:
        from app.core.config import settings
        print(f"Project ID from settings: {settings.GOOGLE_AI_PROJECT_ID}")
        print(f"Location: {settings.GOOGLE_AI_LOCATION}")
        print(f"Model: {settings.GOOGLE_AI_MODEL}")
        
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        # Initialize Vertex AI
        vertexai.init(
            project=settings.GOOGLE_AI_PROJECT_ID,
            location=settings.GOOGLE_AI_LOCATION,
        )
        
        # Try to load the model
        model = GenerativeModel(settings.GOOGLE_AI_MODEL)
        print("✓ Successfully initialized Vertex AI client")
        
        # Try a simple generation
        print("\nTesting model generation...")
        response = model.generate_content("Say 'Hello, World!'")
        print(f"✓ Model responded: {response.text[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        
        if "403" in str(e):
            print("\n🔍 403 Permission Denied - Common causes:")
            print("1. Service account lacks 'Vertex AI User' role")
            print("2. Vertex AI API is not enabled in the project")
            print("3. Project billing is not enabled")
            print("4. Wrong project ID or credentials")
            print("\n📋 To fix:")
            print("1. Enable Vertex AI API:")
            print("   gcloud services enable aiplatform.googleapis.com")
            print("2. Grant service account permissions:")
            print("   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \\")
            print("     --member='serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com' \\")
            print("     --role='roles/aiplatform.user'")
            print("3. Ensure billing is enabled for the project")
        
        return False

def main():
    """Run all diagnostics."""
    if not check_environment():
        sys.exit(1)
    
    if not test_vertex_ai_connection():
        sys.exit(1)
    
    print("\n✅ All checks passed! Vertex AI should be working.")

if __name__ == "__main__":
    main()