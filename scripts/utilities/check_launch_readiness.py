#!/usr/bin/env python3
"""
Check launch readiness and generate configuration template.
"""
import os
import json
import subprocess
from pathlib import Path


def check_file_exists(filepath):
    """Check if a file exists and return status."""
    return "✓" if os.path.exists(filepath) else "✗"


def check_env_var(var_name):
    """Check if an environment variable is set."""
    value = os.environ.get(var_name, "")
    if not value:
        # Check .env file
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith(f"{var_name}="):
                        value = line.split('=', 1)[1].strip()
                        break
    
    if value and value not in ["your-", "mock_", "undefined"]:
        return "✓ Configured"
    return "✗ Not configured"


def check_command_exists(command):
    """Check if a command exists."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=False)
        return "✓ Installed"
    except FileNotFoundError:
        return "✗ Not installed"


def main():
    print("=" * 60)
    print("AI Road Trip Storyteller - Launch Readiness Check")
    print("=" * 60)
    
    # Check prerequisites
    print("\n1. Prerequisites:")
    print(f"   Docker: {check_command_exists('docker')}")
    print(f"   Google Cloud SDK: {check_command_exists('gcloud')}")
    print(f"   Python 3.9+: {check_command_exists('python3')}")
    
    # Check files
    print("\n2. Configuration Files:")
    print(f"   .env file: {check_file_exists('.env')}")
    print(f"   Service account key: {check_file_exists('service-account-key.json')}")
    print(f"   Dockerfile: {check_file_exists('Dockerfile')}")
    print(f"   docker-compose.yml: {check_file_exists('docker-compose.yml')}")
    
    # Check API keys in environment
    print("\n3. Required API Keys:")
    print(f"   Google Maps API: {check_env_var('GOOGLE_MAPS_API_KEY')}")
    print(f"   Ticketmaster API: {check_env_var('TICKETMASTER_API_KEY')}")
    print(f"   OpenWeatherMap API: {check_env_var('OPENWEATHERMAP_API_KEY')}")
    print(f"   Recreation.gov API: {check_env_var('RECREATION_GOV_API_KEY')}")
    
    # Check Google Cloud config
    print("\n4. Google Cloud Configuration:")
    print(f"   Project ID: {check_env_var('GCP_PROJECT_ID')}")
    print(f"   Service Account: {check_env_var('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"   AI Model: {check_env_var('GOOGLE_AI_MODEL')}")
    
    # Check database config
    print("\n5. Database Configuration:")
    print(f"   Database URL: {check_env_var('DATABASE_URL')}")
    print(f"   Redis URL: {check_env_var('REDIS_URL')}")
    
    # Generate template if needed
    if not os.path.exists('.env.production.template'):
        print("\n6. Generating production template...")
        template = """# AI Road Trip Storyteller - Production Configuration Template
# Copy this to .env.production and fill in your values

# Core Configuration
ENVIRONMENT=production
APP_VERSION=1.0.0
SECRET_KEY=GENERATE_A_64_CHAR_RANDOM_STRING_HERE
JWT_SECRET_KEY=GENERATE_ANOTHER_64_CHAR_RANDOM_STRING_HERE
APP_URL=https://api.your-domain.com
CORS_ORIGINS=["https://api.your-domain.com","https://your-domain.com"]

# Database Configuration
DATABASE_URL=postgresql://USERNAME:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
DB_USER=postgres
DB_PASSWORD=YOUR_SECURE_PASSWORD
DB_NAME=roadtrip
CLOUD_SQL_CONNECTION_NAME=PROJECT:REGION:INSTANCE

# Redis Configuration
REDIS_URL=redis://REDIS_HOST:6379
REDIS_HOST=YOUR_REDIS_IP
REDIS_PORT=6379

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GCP_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_AI_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=YOUR_PROJECT_ID-roadtrip-assets

# Required API Keys
GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_KEY
TICKETMASTER_API_KEY=YOUR_TICKETMASTER_KEY
OPENWEATHERMAP_API_KEY=YOUR_OPENWEATHER_KEY
RECREATION_GOV_API_KEY=YOUR_RECREATION_GOV_KEY

# Optional API Keys
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
CHARGEPOINT_API_KEY=
VIATOR_API_KEY=
RESY_API_KEY=
OPENTABLE_API_KEY=
SHELL_RECHARGE_API_KEY=

# Feature Flags
ENABLE_VOICE_SAFETY=true
ENABLE_BOOKING_COMMISSION=true
ENABLE_SEASONAL_PERSONALITIES=true
ENABLE_AR_FEATURES=true
ENABLE_SOCIAL_SHARING=true

# Performance Settings
MAX_CONCURRENT_REQUESTS=100
CACHE_TTL_SECONDS=3600
AI_TIMEOUT_SECONDS=30
MAX_DRIVING_SPEED_MPH=75
VOICE_INTERACTION_COOLDOWN_MS=2000

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
TEST_MODE=live
"""
        with open('.env.production.template', 'w') as f:
            f.write(template)
        print("   ✓ Created .env.production.template")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    
    # Count checks
    missing_items = []
    
    # Check critical items
    if not os.path.exists('.env'):
        missing_items.append("- Create .env file (copy from .env.production.template)")
    
    if not os.path.exists('service-account-key.json'):
        missing_items.append("- Create Google Cloud service account key")
    
    # Read .env to check API keys
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    
    required_apis = ['GOOGLE_MAPS_API_KEY', 'TICKETMASTER_API_KEY', 
                     'OPENWEATHERMAP_API_KEY', 'RECREATION_GOV_API_KEY']
    
    for api in required_apis:
        if api not in env_vars or env_vars[api].startswith('your-'):
            missing_items.append(f"- Add {api}")
    
    if missing_items:
        print("\nMissing items to fix before launch:")
        for item in missing_items:
            print(item)
    else:
        print("\n✓ All critical items configured!")
        print("\nReady to proceed with:")
        print("1. Run infrastructure setup: python3 setup_infrastructure.py")
        print("2. Run tests: python3 run_all_tests_comprehensive.py")
        print("3. Deploy: ./quick_deploy.sh")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()