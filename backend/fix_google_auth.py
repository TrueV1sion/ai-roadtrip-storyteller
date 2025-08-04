#!/usr/bin/env python3
"""
Fix common Google Cloud authentication issues for the RoadTrip backend.
"""

import os
import sys
import json
from pathlib import Path


def create_mock_service_account():
    """Create a mock service account file for testing."""
    mock_sa = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
        "client_email": "roadtrip-backend@your-project-id.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/roadtrip-backend%40your-project-id.iam.gserviceaccount.com"
    }
    
    file_path = Path(__file__).parent / "service-account-template.json"
    with open(file_path, 'w') as f:
        json.dump(mock_sa, f, indent=2)
    
    print(f"✅ Created template service account file: {file_path}")
    print("⚠️  This is just a template! You need to:")
    print("   1. Create a real service account in Google Cloud Console")
    print("   2. Download the actual JSON key file")
    print("   3. Replace this template with the real file")
    return file_path


def update_env_file():
    """Update .env file with Google Cloud settings."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        print("   Creating from .env.example...")
        
        example_path = Path(__file__).parent.parent / ".env.example"
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            print(f"✅ Created .env from .env.example")
        else:
            print("❌ .env.example not found either!")
            return False
    
    # Read current .env
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Settings to add/update
    settings_to_add = {
        "GOOGLE_AI_PROJECT_ID": "your-project-id",
        "GOOGLE_CLOUD_PROJECT_ID": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "backend/service-account.json",
        "VERTEX_AI_LOCATION": "us-central1",
        "GOOGLE_AI_MODEL": "gemini-2.0-pro-exp"
    }
    
    # Check which settings are missing
    existing_keys = set()
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            existing_keys.add(key)
    
    # Add missing settings
    added = []
    for key, value in settings_to_add.items():
        if key not in existing_keys:
            lines.append(f"\n{key}={value}")
            added.append(key)
    
    if added:
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Added missing settings to .env: {', '.join(added)}")
    else:
        print("✅ All Google Cloud settings already in .env")
    
    print("\n⚠️  Remember to update these values with your actual project details!")
    return True


def check_python_packages():
    """Check if required Python packages are installed."""
    packages = {
        "google-cloud-aiplatform": "vertexai",
        "google-cloud-texttospeech": None,
        "google-cloud-secret-manager": None,
        "google-auth": None
    }
    
    print("\nChecking required Python packages...")
    missing = []
    
    for package, import_name in packages.items():
        try:
            if import_name:
                __import__(import_name)
            else:
                __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    
    return True


def main():
    """Main fix script."""
    print("=" * 60)
    print("Google Cloud Authentication Fix Script")
    print("=" * 60)
    
    # Check Python packages
    if not check_python_packages():
        print("\n❌ Please install missing packages first!")
        sys.exit(1)
    
    # Update .env file
    print("\n1. Checking .env file...")
    update_env_file()
    
    # Create template service account if needed
    sa_path = Path(__file__).parent / "service-account.json"
    if not sa_path.exists():
        print("\n2. Creating service account template...")
        create_mock_service_account()
    else:
        print(f"\n2. Service account file exists: {sa_path}")
    
    # Instructions
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("\n1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create or select your project")
    print("3. Enable these APIs:")
    print("   - Vertex AI API")
    print("   - Cloud Text-to-Speech API")
    print("   - Secret Manager API (optional)")
    print("4. Create a service account with these roles:")
    print("   - Vertex AI User")
    print("   - Cloud Text-to-Speech API Client")
    print("5. Download the JSON key file")
    print(f"6. Save it as: {sa_path}")
    print("7. Update your .env file with your actual project ID")
    print("8. Run: python backend/test_google_auth.py")
    
    print("\nFor detailed instructions, see: setup_google_auth.md")


if __name__ == "__main__":
    main()