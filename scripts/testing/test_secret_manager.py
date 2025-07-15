#!/usr/bin/env python3
"""
Test script to verify Secret Manager integration is working correctly.
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_secret_manager():
    """Test Secret Manager functionality."""
    print("Testing Secret Manager Integration...")
    print("=" * 50)
    
    # Test 1: Check environment
    print("\n1. Checking environment variables:")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_AI_PROJECT_ID")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"   Project ID: {project_id or 'NOT SET'}")
    print(f"   Credentials Path: {creds_path or 'NOT SET'}")
    
    if creds_path and os.path.exists(creds_path):
        print(f"   Credentials File Exists: YES")
    else:
        print(f"   Credentials File Exists: NO")
    
    # Test 2: Try to import and initialize Secret Manager
    print("\n2. Testing Secret Manager client:")
    try:
        from backend.app.core.secrets import get_secret_manager
        manager = get_secret_manager()
        print("   ✓ Secret Manager client initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return
    
    # Test 3: Test secret retrieval
    print("\n3. Testing secret retrieval:")
    test_secrets = [
        "roadtrip-secret-key",
        "roadtrip-database-url",
        "roadtrip-google-maps-key"
    ]
    
    for secret_id in test_secrets:
        try:
            value = manager.get_secret(secret_id)
            if value:
                # Don't print actual secret values
                print(f"   ✓ {secret_id}: Found (length: {len(value)})")
            else:
                print(f"   ✗ {secret_id}: Not found")
        except Exception as e:
            print(f"   ✗ {secret_id}: Error - {e}")
    
    # Test 4: Test configuration loading
    print("\n4. Testing configuration with Secret Manager:")
    try:
        from backend.app.core.config import settings
        
        # Check if critical settings are loaded
        critical_settings = {
            "SECRET_KEY": settings.SECRET_KEY,
            "DATABASE_URL": settings.DATABASE_URL,
            "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
            "REDIS_URL": settings.REDIS_URL
        }
        
        for name, value in critical_settings.items():
            if value:
                print(f"   ✓ {name}: Loaded (length: {len(str(value))})")
            else:
                print(f"   ✗ {name}: Not loaded")
                
    except Exception as e:
        print(f"   ✗ Failed to load configuration: {e}")
    
    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_secret_manager()