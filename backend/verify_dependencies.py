#!/usr/bin/env python3
"""
Dependency verification script for AI Road Trip Storyteller backend.
Tests that all required packages can be imported successfully.
"""

import sys
import importlib
from typing import List, Tuple

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_import(module_name: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {module_name}"
    except ImportError as e:
        return False, f"❌ {module_name}: {str(e)}"
    except Exception as e:
        return False, f"⚠️  {module_name}: Unexpected error - {str(e)}"

def main():
    """Test all required imports."""
    print("🔍 Verifying AI Road Trip Storyteller Backend Dependencies\n")
    
    # Core dependencies
    core_modules = [
        "fastapi",
        "uvicorn",
        "gunicorn",
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "psycopg2",
        "jose",
        "passlib",
        "cryptography",
        "multipart",
        "dotenv",
        "httpx",
        "requests",
        "itsdangerous",
        "polyline",
    ]
    
    # Google Cloud Services
    google_modules = [
        "google.cloud.aiplatform",
        "vertexai",
        "google.cloud.language",
        "googlemaps",
        "google.cloud.texttospeech",
        "google.cloud.storage",
        "google.cloud.speech",
        "google.cloud.secretmanager",
        "google.cloud.logging",
        "google.cloud.translate",
    ]
    
    # AI and ML
    ai_modules = [
        "langchain",
        "langchain_google_vertexai",
        "numpy",
        "pandas",
        "sklearn",
        "joblib",
    ]
    
    # Task queue
    celery_modules = [
        "celery",
        "kombu",
        "billiard",
        "vine",
    ]
    
    # GraphQL
    graphql_modules = [
        "strawberry",
    ]
    
    # Other dependencies
    other_modules = [
        "spotipy",
        "redis",
        "aioredis",
        "slowapi",
        "stripe",
        "twilio",
        "sendgrid",
        "aiofiles",
        "aiohttp",
        "pyotp",
        "qrcode",
        "bcrypt",
        "prometheus_client",
        "prometheus_fastapi_instrumentator",
        "opentelemetry",
        "alembic",
        "pytest",
    ]
    
    all_modules = [
        ("Core Dependencies", core_modules),
        ("Google Cloud Services", google_modules),
        ("AI and ML", ai_modules),
        ("Task Queue (Celery)", celery_modules),
        ("GraphQL", graphql_modules),
        ("Other Dependencies", other_modules),
    ]
    
    total_tests = 0
    total_passed = 0
    failed_imports = []
    
    for category, modules in all_modules:
        print(f"\n📦 {category}:")
        print("-" * 50)
        
        for module in modules:
            total_tests += 1
            success, message = test_import(module)
            print(message)
            
            if success:
                total_passed += 1
            else:
                failed_imports.append((module, message))
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Summary: {total_passed}/{total_tests} imports successful")
    print("=" * 60)
    
    if failed_imports:
        print("\n❌ Failed imports:")
        for module, message in failed_imports:
            print(f"  {message}")
        print("\n💡 To fix missing dependencies, run:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("\n✅ All dependencies verified successfully!")
        print("🚀 Ready for deployment!")
        sys.exit(0)

if __name__ == "__main__":
    main()