#!/usr/bin/env python3
"""
Fix Vertex AI authentication issue in production.
The health check is incorrectly using the Generative Language API with API key
instead of Vertex AI with service account authentication.
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any

def run_command(cmd: str) -> tuple[str, int]:
    """Run a shell command and return output and exit code."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def check_current_deployment():
    """Check current Cloud Run deployment configuration."""
    print("\n[CHECK] Checking current deployment configuration...")
    
    service_name = "roadtrip-mvp"
    region = "us-central1"
    
    # Get current environment variables
    cmd = f"gcloud run services describe {service_name} --region={region} --format=json"
    output, code = run_command(cmd)
    
    if code != 0:
        print(f"[ERROR] Failed to get service configuration: {output}")
        return None
    
    try:
        config = json.loads(output)
        env_vars = {}
        
        # Extract environment variables
        containers = config.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        if containers:
            for env in containers[0].get("env", []):
                env_vars[env["name"]] = env.get("value", "")
        
        print("\n[INFO] Current environment variables:")
        for key, value in env_vars.items():
            if "AI" in key or "VERTEX" in key or "GEMINI" in key:
                # Mask sensitive values
                masked_value = value[:10] + "..." if len(value) > 10 else value
                print(f"  {key}: {masked_value}")
        
        return env_vars
    except Exception as e:
        print(f"[ERROR] Failed to parse configuration: {e}")
        return None

def fix_environment_variables():
    """Update Cloud Run environment variables to use Vertex AI properly."""
    print("\n[FIX] Fixing environment variables...")
    
    service_name = "roadtrip-mvp"
    region = "us-central1"
    project_id = "roadtrip-460720"  # Your actual project ID
    
    # Update environment variables to ensure Vertex AI is used
    env_updates = [
        f"GOOGLE_AI_PROJECT_ID={project_id}",
        f"GOOGLE_AI_LOCATION={region}",
        f"VERTEX_AI_LOCATION={region}",
        f"GOOGLE_CLOUD_PROJECT={project_id}",
        "USE_VERTEX_AI=true",
        "DISABLE_GEMINI_API_KEY=true"  # Force disabling API key usage
    ]
    
    # Build the gcloud command
    cmd = f"gcloud run services update {service_name} --region={region}"
    for env_var in env_updates:
        cmd += f" --update-env-vars={env_var}"
    
    print("Running update command...")
    output, code = run_command(cmd)
    
    if code == 0:
        print("[SUCCESS] Environment variables updated successfully")
        return True
    else:
        print(f"[ERROR] Failed to update environment variables: {output}")
        return False

def verify_service_account():
    """Verify the service account has correct permissions."""
    print("\n[CHECK] Verifying service account permissions...")
    
    service_account = "roadtrip-backend@roadtrip-460720.iam.gserviceaccount.com"
    project_id = "roadtrip-460720"
    
    # Check IAM policy
    cmd = f"gcloud projects get-iam-policy {project_id} --flatten='bindings[].members' --format='table(bindings.role)' --filter='bindings.members:{service_account}'"
    output, code = run_command(cmd)
    
    if code == 0:
        print(f"\n[INFO] Service account roles:")
        print(output)
        
        required_roles = ["roles/aiplatform.user", "roles/serviceusage.serviceUsageConsumer"]
        roles_list = output.lower()
        
        missing_roles = []
        for role in required_roles:
            if role not in roles_list:
                missing_roles.append(role)
        
        if missing_roles:
            print(f"\n[WARNING] Missing required roles: {missing_roles}")
            return False
        else:
            print("[SUCCESS] All required roles are present")
            return True
    else:
        print(f"[ERROR] Failed to check IAM policy: {output}")
        return False

def grant_missing_permissions():
    """Grant any missing permissions to the service account."""
    print("\n[FIX] Granting missing permissions...")
    
    service_account = "roadtrip-backend@roadtrip-460720.iam.gserviceaccount.com"
    project_id = "roadtrip-460720"
    
    roles_to_grant = [
        "roles/aiplatform.user",
        "roles/serviceusage.serviceUsageConsumer"
    ]
    
    for role in roles_to_grant:
        cmd = f"gcloud projects add-iam-policy-binding {project_id} --member='serviceAccount:{service_account}' --role='{role}'"
        print(f"Granting {role}...")
        output, code = run_command(cmd)
        
        if code == 0:
            print(f"[SUCCESS] Granted {role}")
        else:
            print(f"[WARNING] Failed to grant {role}: {output}")

def test_health_endpoint():
    """Test the health endpoint after fixes."""
    print("\n[TEST] Testing health endpoint...")
    
    import time
    print("Waiting 30 seconds for changes to propagate...")
    time.sleep(30)
    
    import requests
    url = "https://roadtrip-mvp-792001900150.us-central1.run.app/health"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"\n[RESULT] Health check response:")
        print(f"Status: {data.get('status')}")
        
        if "services" in data:
            for service, status in data["services"].items():
                if isinstance(status, str) and "error" in status:
                    print(f"  {service}: [ERROR]")
                    print(f"    {status[:100]}...")
                else:
                    print(f"  {service}: [OK] {status}")
        
        return data.get("status") != "degraded"
    except Exception as e:
        print(f"[ERROR] Failed to test health endpoint: {e}")
        return False

def main():
    print("[LAUNCH] Vertex AI Authentication Fix Script")
    print("=====================================")
    
    # Check current configuration
    env_vars = check_current_deployment()
    if not env_vars:
        print("\n[ERROR] Failed to check current deployment")
        return 1
    
    # Verify service account
    if not verify_service_account():
        print("\n[FIX] Attempting to grant missing permissions...")
        grant_missing_permissions()
    
    # Fix environment variables
    print("\n[UPDATE] Updating deployment configuration...")
    if not fix_environment_variables():
        print("\n[ERROR] Failed to update environment variables")
        return 1
    
    # Test the health endpoint
    print("\n[TEST] Testing the fix...")
    if test_health_endpoint():
        print("\n[SUCCESS] Health check is now working!")
        print("\n[COMPLETE] Vertex AI authentication has been fixed!")
        print("\nNext steps:")
        print("1. Monitor the application logs for any remaining issues")
        print("2. Test AI story generation functionality")
        print("3. Verify all integrations are working properly")
    else:
        print("\n[WARNING] Health check still showing issues")
        print("\nTroubleshooting steps:")
        print("1. Check Cloud Run logs: gcloud run logs read roadtrip-backend --region=us-central1")
        print("2. Verify billing is enabled for the project")
        print("3. Check if there are quota limits on Vertex AI")
        print("4. Review the backend code to ensure it's using Vertex AI correctly")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())