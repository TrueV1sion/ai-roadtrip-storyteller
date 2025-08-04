#!/usr/bin/env python3
"""
Prepare backend for deployment by fixing all import issues.
"""
import os
import re
import sys
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Fix backend.app imports
        content = re.sub(r'from backend\.app\.', 'from app.', content)
        content = re.sub(r'import backend\.app\.', 'import app.', content)
        
        # Fix Vertex AI imports
        content = re.sub(r'from vertexai\.preview\.generative_models', 'from vertexai.generative_models', content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error in {filepath}: {e}")
        return False

def main():
    """Main function."""
    print("=== Preparing Backend for Deployment ===\n")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    print("1. Fixing import issues...")
    fixed_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk('.'):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', '.pytest_cache', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                total_count += 1
                filepath = os.path.join(root, file)
                if fix_imports_in_file(filepath):
                    print(f"   Fixed: {filepath}")
                    fixed_count += 1
    
    print(f"\n   Total Python files: {total_count}")
    print(f"   Files fixed: {fixed_count}")
    
    print("\n2. Creating environment template...")
    env_template = """# AI Road Trip Backend Environment Variables

# Google Cloud Configuration
GOOGLE_AI_PROJECT_ID=your-project-id
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-2.0-pro-exp

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/roadtrip

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET_KEY=generate-a-secure-random-key-here

# API Keys
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
OPENWEATHERMAP_API_KEY=your-openweather-api-key

# Optional: External Service Keys
TICKETMASTER_API_KEY=
OPENTABLE_PARTNER_ID=
VIATOR_PARTNER_ID=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# Environment
ENVIRONMENT=development
DEBUG=True
"""
    
    if not os.path.exists('.env.example'):
        with open('.env.example', 'w') as f:
            f.write(env_template)
        print("   Created .env.example")
    
    print("\n3. Deployment checklist:")
    print("   [ ] Install dependencies: pip install -r requirements.txt")
    print("   [ ] Copy .env.example to .env and fill in your values")
    print("   [ ] Run database migrations: alembic upgrade head")
    print("   [ ] Start Redis: redis-server")
    print("   [ ] Start the server: uvicorn app.main:app --reload")
    
    print("\n4. Quick test commands:")
    print("   - Test imports: python test_imports.py")
    print("   - Verify startup: python verify_startup.py")
    print("   - Health check: curl http://localhost:8000/health")
    
    print("\n=== Backend is ready for deployment! ===")

if __name__ == "__main__":
    main()