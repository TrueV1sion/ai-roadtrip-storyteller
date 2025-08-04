#!/usr/bin/env python3
"""
Fix script for Gemini AI 403 permission errors.
This script provides instructions and commands to resolve the issue.
"""
import os
import subprocess
import sys

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def run_command(cmd, description):
    """Run a command and show the result."""
    print(f"Running: {description}")
    print(f"Command: {cmd}\n")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run command: {e}")
        return False

def main():
    print_section("Gemini AI / Vertex AI 403 Error Fix")
    
    # Get project ID from environment
    project_id = os.getenv("GOOGLE_AI_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    
    if not project_id:
        print("❌ ERROR: No Google Cloud project ID found!")
        print("\nPlease set one of these environment variables:")
        print("  - GOOGLE_AI_PROJECT_ID")
        print("  - GOOGLE_CLOUD_PROJECT_ID")
        print("\nExample:")
        print("  export GOOGLE_AI_PROJECT_ID=your-project-id")
        sys.exit(1)
    
    print(f"✓ Using Google Cloud Project: {project_id}")
    
    print_section("Step 1: Enable Required APIs")
    
    print("The following command will enable the Vertex AI API:")
    print(f"\ngcloud services enable aiplatform.googleapis.com --project={project_id}\n")
    
    response = input("Run this command? (y/n): ")
    if response.lower() == 'y':
        success = run_command(
            f"gcloud services enable aiplatform.googleapis.com --project={project_id}",
            "Enabling Vertex AI API"
        )
        if success:
            print("✓ Vertex AI API enabled successfully")
        else:
            print("⚠️  Failed to enable API. You may need to run this manually.")
    
    print_section("Step 2: Check Authentication")
    
    # Check for service account
    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_file:
        print(f"✓ Using service account: {creds_file}")
        if os.path.exists(creds_file):
            print("  ✓ File exists")
            
            # Extract service account email
            try:
                import json
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                    sa_email = creds.get('client_email')
                    if sa_email:
                        print(f"  ✓ Service account: {sa_email}")
                        
                        print("\nTo grant Vertex AI permissions to this service account:")
                        print(f"\ngcloud projects add-iam-policy-binding {project_id} \\")
                        print(f"  --member='serviceAccount:{sa_email}' \\")
                        print(f"  --role='roles/aiplatform.user'\n")
            except Exception as e:
                print(f"  ⚠️  Could not read service account file: {e}")
        else:
            print("  ❌ File does not exist!")
    else:
        print("⚠️  No service account configured")
        print("\nFor local development, run:")
        print("  gcloud auth application-default login")
        print("\nFor production, set GOOGLE_APPLICATION_CREDENTIALS to a service account key file")
    
    print_section("Step 3: Test Vertex AI Access")
    
    print("Testing Vertex AI connection...")
    test_script = """
import vertexai
from vertexai.generative_models import GenerativeModel

try:
    vertexai.init(project='""" + project_id + """', location='us-central1')
    model = GenerativeModel('gemini-2.0-pro-exp')
    response = model.generate_content('Say hello')
    print('✓ SUCCESS: Vertex AI is working!')
    print(f'  Response: {response.text[:50]}...')
except Exception as e:
    print(f'❌ ERROR: {e}')
    if '403' in str(e):
        print('\\n⚠️  This is a permission error. Please follow the steps above.')
"""
    
    try:
        exec(test_script)
    except ImportError:
        print("⚠️  Vertex AI SDK not installed. Install with: pip install google-cloud-aiplatform")
    
    print_section("Summary of Required Actions")
    
    print("1. Enable Vertex AI API:")
    print(f"   gcloud services enable aiplatform.googleapis.com --project={project_id}")
    
    print("\n2. Set up authentication (choose one):")
    print("   - For local dev: gcloud auth application-default login")
    print("   - For production: Use service account with GOOGLE_APPLICATION_CREDENTIALS")
    
    print("\n3. Grant permissions (if using service account):")
    print(f"   gcloud projects add-iam-policy-binding {project_id} \\")
    print("     --member='serviceAccount:YOUR_SERVICE_ACCOUNT@{project_id}.iam.gserviceaccount.com' \\")
    print("     --role='roles/aiplatform.user'")
    
    print("\n4. Ensure billing is enabled for the project")
    
    print("\n5. Test the health endpoint:")
    print("   curl http://localhost:8000/api/health/services")
    print("   curl http://localhost:8000/api/health/services/gemini-ai/diagnose")
    
    print("\n✅ Once these steps are complete, the 403 error should be resolved!")

if __name__ == "__main__":
    main()