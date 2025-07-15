#!/usr/bin/env python3
"""
Comprehensive API Setup Script for AI Road Trip Storyteller
Helps configure all required API keys and credentials
"""

import os
import sys
from pathlib import Path
import json

def get_input_with_default(prompt, default=""):
    """Get user input with default value"""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        return input(f"{prompt}: ").strip()

def validate_google_maps_key(api_key):
    """Validate Google Maps API key by making a test request"""
    import urllib.request
    import urllib.parse
    import json
    
    params = {
        'origins': 'San Francisco, CA',
        'destinations': 'Los Angeles, CA',
        'key': api_key
    }
    
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return data.get('status') == 'OK'
    except Exception:
        return False

def validate_openweather_key(api_key):
    """Validate OpenWeatherMap API key"""
    import urllib.request
    import urllib.parse
    import json
    
    params = {
        'q': 'London',
        'appid': api_key
    }
    
    url = f"https://api.openweathermap.org/data/2.5/weather?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return 'main' in data
    except Exception:
        return False

def validate_ticketmaster_key(api_key):
    """Validate Ticketmaster API key"""
    import urllib.request
    import urllib.parse
    import json
    
    params = {
        'apikey': api_key,
        'size': 1
    }
    
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return '_embedded' in data or 'page' in data
    except Exception:
        return False

def validate_recreation_gov_key(api_key):
    """Validate Recreation.gov API key"""
    import urllib.request
    import json
    
    url = "https://ridb.recreation.gov/api/v1/facilities?limit=1"
    
    try:
        req = urllib.request.Request(url)
        req.add_header('apikey', api_key)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return 'RECDATA' in data
    except Exception:
        return False

def setup_google_cloud():
    """Setup Google Cloud configuration"""
    print("\n🔧 Setting up Google Cloud Integration")
    print("="*50)
    
    project_id = get_input_with_default(
        "Enter your Google Cloud Project ID",
        os.getenv('GOOGLE_AI_PROJECT_ID', '')
    )
    
    if not project_id:
        print("❌ Google Cloud Project ID is required!")
        print("💡 Create a project at: https://console.cloud.google.com/")
        return {}
    
    location = get_input_with_default(
        "Enter Google Cloud region",
        "us-central1"
    )
    
    model = get_input_with_default(
        "Enter AI model name",
        "gemini-1.5-flash"
    )
    
    return {
        'GOOGLE_AI_PROJECT_ID': project_id,
        'GOOGLE_AI_LOCATION': location,
        'GOOGLE_AI_MODEL': model
    }

def setup_required_apis():
    """Setup all required API keys"""
    print("\n🗝️  Setting up Required API Keys")
    print("="*50)
    
    apis = {}
    
    # Google Maps API
    print("\n📍 Google Maps API")
    print("Get your key at: https://console.cloud.google.com/apis/library/maps-backend.googleapis.com")
    google_maps_key = get_input_with_default(
        "Enter Google Maps API key",
        os.getenv('GOOGLE_MAPS_API_KEY', '')
    )
    
    if google_maps_key and google_maps_key != 'mock_google_maps_key_for_testing':
        print("🔍 Validating Google Maps key...")
        if validate_google_maps_key(google_maps_key):
            print("✅ Google Maps API key is valid")
            apis['GOOGLE_MAPS_API_KEY'] = google_maps_key
        else:
            print("❌ Google Maps API key validation failed")
            print("💡 Make sure the key has Directions API enabled")
    elif google_maps_key:
        apis['GOOGLE_MAPS_API_KEY'] = google_maps_key
    
    return apis

def setup_optional_apis():
    """Setup optional API keys"""
    print("\n🎯 Setting up Optional API Keys")
    print("="*50)
    
    apis = {}
    
    # OpenWeatherMap
    print("\n🌤️  OpenWeatherMap API")
    print("Get your free key at: https://openweathermap.org/api")
    weather_key = get_input_with_default(
        "Enter OpenWeatherMap API key (press Enter to skip)",
        os.getenv('OPENWEATHERMAP_API_KEY', '')
    )
    
    if weather_key and weather_key != 'mock_weather_key':
        print("🔍 Validating OpenWeatherMap key...")
        if validate_openweather_key(weather_key):
            print("✅ OpenWeatherMap API key is valid")
            apis['OPENWEATHERMAP_API_KEY'] = weather_key
        else:
            print("❌ OpenWeatherMap API key validation failed")
    elif weather_key:
        apis['OPENWEATHERMAP_API_KEY'] = weather_key
    
    # Ticketmaster
    print("\n🎫 Ticketmaster API")
    print("Get your key at: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/")
    ticketmaster_key = get_input_with_default(
        "Enter Ticketmaster API key (press Enter to skip)",
        os.getenv('TICKETMASTER_API_KEY', '')
    )
    
    if ticketmaster_key and ticketmaster_key != 'mock_ticketmaster_key':
        print("🔍 Validating Ticketmaster key...")
        if validate_ticketmaster_key(ticketmaster_key):
            print("✅ Ticketmaster API key is valid")
            apis['TICKETMASTER_API_KEY'] = ticketmaster_key
        else:
            print("❌ Ticketmaster API key validation failed")
    elif ticketmaster_key:
        apis['TICKETMASTER_API_KEY'] = ticketmaster_key
    
    # Recreation.gov
    print("\n🏕️  Recreation.gov API")
    print("Get your free key at: https://ridb.recreation.gov/")
    recreation_key = get_input_with_default(
        "Enter Recreation.gov API key (press Enter to skip)",
        os.getenv('RECREATION_GOV_API_KEY', '')
    )
    
    if recreation_key:
        print("🔍 Validating Recreation.gov key...")
        if validate_recreation_gov_key(recreation_key):
            print("✅ Recreation.gov API key is valid")
            apis['RECREATION_GOV_API_KEY'] = recreation_key
        else:
            print("❌ Recreation.gov API key validation failed")
    
    return apis

def setup_spotify():
    """Setup Spotify integration"""
    print("\n🎵 Setting up Spotify Integration (Optional)")
    print("="*50)
    print("Get your credentials at: https://developer.spotify.com/dashboard/applications")
    
    client_id = get_input_with_default(
        "Enter Spotify Client ID (press Enter to skip)",
        os.getenv('SPOTIFY_CLIENT_ID', '')
    )
    
    if not client_id:
        return {}
    
    client_secret = get_input_with_default(
        "Enter Spotify Client Secret",
        os.getenv('SPOTIFY_CLIENT_SECRET', '')
    )
    
    redirect_uri = get_input_with_default(
        "Enter Spotify Redirect URI",
        "http://localhost:8000/api/spotify/callback"
    )
    
    return {
        'SPOTIFY_CLIENT_ID': client_id,
        'SPOTIFY_CLIENT_SECRET': client_secret,
        'SPOTIFY_REDIRECT_URI': redirect_uri
    }

def setup_database():
    """Setup database configuration"""
    print("\n🗄️  Setting up Database Configuration")
    print("="*50)
    
    db_url = get_input_with_default(
        "Enter Database URL (press Enter for local PostgreSQL)",
        os.getenv('DATABASE_URL', 'postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip')
    )
    
    secret_key = get_input_with_default(
        "Enter Secret Key (press Enter to generate)",
        os.getenv('SECRET_KEY', '')
    )
    
    if not secret_key:
        import secrets
        secret_key = secrets.token_urlsafe(32)
        print(f"🔑 Generated secret key: {secret_key}")
    
    return {
        'DATABASE_URL': db_url,
        'SECRET_KEY': secret_key
    }

def save_env_file(config):
    """Save configuration to .env file"""
    env_path = Path('.env')
    
    # Read existing .env if it exists
    existing_config = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    existing_config[key] = value
    
    # Merge configurations
    existing_config.update(config)
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.write("# AI Road Trip Storyteller Configuration\n")
        f.write("# Generated by setup_apis_comprehensive.py\n\n")
        
        f.write("# Google Cloud Configuration\n")
        for key in ['GOOGLE_AI_PROJECT_ID', 'GOOGLE_AI_LOCATION', 'GOOGLE_AI_MODEL']:
            if key in existing_config:
                f.write(f"{key}={existing_config[key]}\n")
        f.write("\n")
        
        f.write("# API Keys\n")
        for key in ['GOOGLE_MAPS_API_KEY', 'OPENWEATHERMAP_API_KEY', 'TICKETMASTER_API_KEY', 'RECREATION_GOV_API_KEY']:
            if key in existing_config:
                f.write(f"{key}={existing_config[key]}\n")
        f.write("\n")
        
        f.write("# Database Configuration\n")
        for key in ['DATABASE_URL', 'SECRET_KEY']:
            if key in existing_config:
                f.write(f"{key}={existing_config[key]}\n")
        f.write("\n")
        
        f.write("# Spotify Integration\n")
        for key in ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REDIRECT_URI']:
            if key in existing_config:
                f.write(f"{key}={existing_config[key]}\n")
        f.write("\n")
        
        f.write("# Development Settings\n")
        f.write("APP_VERSION=1.0.0\n")
        f.write("TTS_PROVIDER=google\n")
        f.write("DEFAULT_AI_PROVIDER=google\n")
    
    print(f"\n✅ Configuration saved to {env_path}")

def main():
    """Main setup function"""
    print("🚀 AI Road Trip Storyteller - Comprehensive API Setup")
    print("="*60)
    print("This script will help you configure all the required and optional")
    print("API keys and credentials for the AI Road Trip Storyteller.")
    print("\nPress Enter to continue or Ctrl+C to exit...")
    input()
    
    config = {}
    
    # Setup Google Cloud (required)
    config.update(setup_google_cloud())
    
    # Setup required APIs
    config.update(setup_required_apis())
    
    # Setup optional APIs
    setup_optional = input("\n🎯 Would you like to setup optional APIs? (y/N): ").strip().lower()
    if setup_optional in ['y', 'yes']:
        config.update(setup_optional_apis())
    
    # Setup Spotify
    setup_spotify_integration = input("\n🎵 Would you like to setup Spotify integration? (y/N): ").strip().lower()
    if setup_spotify_integration in ['y', 'yes']:
        config.update(setup_spotify())
    
    # Setup database
    config.update(setup_database())
    
    # Save configuration
    save_env_file(config)
    
    print("\n🎉 Setup Complete!")
    print("="*60)
    print("Your configuration has been saved to .env")
    print("\n📋 Next Steps:")
    print("1. Run: python3 test_apis_simple.py")
    print("2. Start the backend: ./scripts/launch_beta.sh")
    print("3. Test the mobile app: cd mobile && npm start")
    print("\n💡 For Google Cloud service account setup:")
    print("   Follow the guide in docs/google_cloud_setup.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)