#!/usr/bin/env python3
"""
Quick deployment script for the incremental backend.
Handles environment setup, import fixes, and deployment in one command.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, shell=True):
    """Run a command and return success status."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    """Main deployment process."""
    print("=== AI Road Trip Backend Quick Deploy ===\n")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    print(f"Working directory: {backend_dir}")
    
    # Step 1: Check environment variables
    print("\n1. Checking environment variables...")
    if not run_command(f"{sys.executable} check_env_vars.py"):
        print("\n⚠️  Environment variables need to be configured.")
        print("Please create a .env file or set them in Cloud Run.")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # Step 2: Fix imports
    print("\n2. Fixing import statements...")
    if not run_command(f"{sys.executable} fix_imports.py"):
        print("Failed to fix imports")
        return 1
    
    # Step 3: Test locally (optional)
    response = input("\n3. Test locally first? (y/N): ")
    if response.lower() == 'y':
        print("\nStarting local server...")
        print("Press Ctrl+C to stop and continue with deployment")
        try:
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "app.main_incremental:app", 
                "--reload", "--host", "0.0.0.0", "--port", "8000"
            ])
        except KeyboardInterrupt:
            print("\nLocal testing stopped")
    
    # Step 4: Deploy to Google Cloud Run
    print("\n4. Deploying to Google Cloud Run...")
    
    # Determine the platform and use appropriate script
    is_windows = platform.system() == "Windows"
    
    if is_windows:
        deploy_script = "deploy_incremental.bat"
    else:
        deploy_script = "./deploy_incremental.sh"
        # Make script executable
        run_command(f"chmod +x {deploy_script}", shell=True)
    
    print(f"\nRunning deployment script: {deploy_script}")
    if not run_command(deploy_script, shell=True):
        print("\n❌ Deployment failed!")
        print("\nTroubleshooting:")
        print("1. Ensure you're authenticated: gcloud auth login")
        print("2. Check your project ID is correct")
        print("3. Ensure Docker is running")
        print("4. Check the deployment logs above for specific errors")
        return 1
    
    # Step 5: Test deployed service
    print("\n5. Testing deployed service...")
    
    # Get service URL
    try:
        result = subprocess.run([
            "gcloud", "run", "services", "describe", 
            "roadtrip-backend-incremental",
            "--region", "us-central1",
            "--format", "value(status.url)"
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            service_url = result.stdout.strip()
            print(f"\nService URL: {service_url}")
            
            # Test the health endpoint
            os.environ["API_BASE_URL"] = service_url
            run_command(f"{sys.executable} test_api_endpoints.py")
    except Exception as e:
        print(f"Could not test deployed service: {e}")
    
    print("\n✅ Deployment complete!")
    print("\nNext steps:")
    print("1. Configure environment variables in Cloud Run console")
    print("2. Set up Cloud SQL for production database")
    print("3. Configure Redis for caching")
    print("4. Add API keys for external services")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())