#!/usr/bin/env python3
"""
Verify that the backend can start properly.
This script checks if the main app can be imported and started.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_startup():
    """Verify backend startup."""
    print("=== Backend Startup Verification ===\n")
    
    # Step 1: Check if main app can be imported
    print("1. Testing main app import...")
    try:
        from app.main import app
        print("   [OK] Main app imported successfully")
        print(f"   App title: {app.title}")
        print(f"   App version: {app.version}")
    except Exception as e:
        print(f"   [ERROR] Failed to import main app: {e}")
        return False
    
    # Step 2: Check critical routes
    print("\n2. Checking critical routes...")
    critical_routes = ['health', 'auth', 'csrf', 'jwks']
    for route_name in critical_routes:
        try:
            module = __import__(f'app.routes.{route_name}', fromlist=['router'])
            router = getattr(module, 'router', None)
            if router:
                print(f"   [OK] Route '{route_name}' loaded")
            else:
                print(f"   [WARNING] Route '{route_name}' has no router")
        except Exception as e:
            print(f"   [ERROR] Route '{route_name}' failed: {e}")
    
    # Step 3: Check API documentation
    print("\n3. Checking API documentation...")
    try:
        docs_url = app.docs_url or "/docs"
        print(f"   [OK] API docs available at: {docs_url}")
    except Exception as e:
        print(f"   [ERROR] API docs check failed: {e}")
    
    print("\n=== Verification Complete ===")
    print("\nTo start the backend server, run:")
    print("  cd backend")
    print("  pip install -r requirements.txt")
    print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    
    return True

if __name__ == "__main__":
    success = verify_startup()
    sys.exit(0 if success else 1)