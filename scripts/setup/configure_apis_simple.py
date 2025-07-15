#!/usr/bin/env python3
"""
Simple API Configuration Helper
No external dependencies required - uses only Python standard library
"""

import os
import json
import getpass
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*50)
    print(f"🔑 {text}")
    print("="*50)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")

def get_api_key(name, description, required=True, url=None):
    """Get API key from user"""
    print(f"\n📌 {name}")
    print(f"   {description}")
    if url:
        print(f"   Get it here: {url}")
    
    if not required:
        print("   (Optional - press Enter to skip)")
    
    key = getpass.getpass(f"   Enter {name}: ").strip()
    
    if not key and required:
        print_warning(f"{name} is required!")
        return get_api_key(name, description, required, url)
    
    return key

def create_env_file():
    """Create .env file with API keys"""
    print_header("AI Road Trip Storyteller - API Configuration")
    
    print("\nThis wizard will help you configure your API keys.")
    print("Your keys will be saved to .env file (gitignored for security)")
    
    # Check if .env exists
    env_path = Path(".env")
    if env_path.exists():
        overwrite = input("\n⚠️  .env file already exists. Overwrite? (y/N): ")
        if overwrite.lower() != 'y':
            print("Configuration cancelled.")
            return
    
    # Collect API keys
    config = {}
    
    print_header("Step 1: Google Cloud Platform (Required)")
    print_info("You need a Google Cloud project with Maps, TTS, STT, and Vertex AI enabled")
    config['GOOGLE_MAPS_API_KEY'] = get_api_key(
        "Google Maps API Key",
        "For maps, directions, and places",
        url="https://console.cloud.google.com/apis/credentials"
    )
    config['GOOGLE_CLOUD_PROJECT_ID'] = get_api_key(
        "Google Cloud Project ID",
        "Your GCP project identifier (e.g., 'my-project-123')"
    )
    
    print_header("Step 2: Free APIs (Highly Recommended)")
    config['RECREATION_GOV_API_KEY'] = get_api_key(
        "Recreation.gov API Key",
        "FREE - For campground bookings",
        url="https://ridb.recreation.gov/",
        required=False
    )
    config['TICKETMASTER_API_KEY'] = get_api_key(
        "Ticketmaster API Key",
        "FREE - For event detection",
        url="https://developer.ticketmaster.com/",
        required=False
    )
    config['OPENWEATHERMAP_API_KEY'] = get_api_key(
        "OpenWeatherMap API Key",
        "FREE tier available - For weather data",
        url="https://openweathermap.org/api",
        required=False
    )
    
    print_header("Step 3: Flight Tracking APIs (Optional)")
    print_info("Configure at least one for flight tracking. AviationStack has free tier.")
    config['AVIATIONSTACK_API_KEY'] = get_api_key(
        "AviationStack API Key",
        "FREE tier (100 req/month) - For flight tracking",
        url="https://aviationstack.com/signup/free",
        required=False
    )
    config['FLIGHTSTATS_APP_ID'] = get_api_key(
        "FlightStats App ID",
        "Enterprise flight data (paid)",
        url="https://developer.flightstats.com/",
        required=False
    )
    config['FLIGHTSTATS_API_KEY'] = get_api_key(
        "FlightStats API Key",
        "FlightStats App Key",
        required=False
    )
    config['FLIGHTAWARE_API_KEY'] = get_api_key(
        "FlightAware API Key",
        "Professional flight tracking (paid)",
        url="https://flightaware.com/commercial/aeroapi/",
        required=False
    )
    config['FLIGHTLABS_API_KEY'] = get_api_key(
        "FlightLabs API Key",
        "Affordable flight data",
        url="https://www.goflightlabs.com/",
        required=False
    )
    
    print_header("Step 4: Partner APIs (Optional - Can use mock mode)")
    print_info("These require partnership approval. Leave blank to use mock mode.")
    config['OPENTABLE_CLIENT_ID'] = get_api_key(
        "OpenTable Client ID",
        "For restaurant reservations (requires partnership)",
        required=False
    )
    config['OPENTABLE_CLIENT_SECRET'] = get_api_key(
        "OpenTable Client Secret",
        "OpenTable OAuth secret",
        required=False
    )
    config['SHELL_RECHARGE_API_KEY'] = get_api_key(
        "Shell Recharge API Key",
        "For EV charging reservations",
        required=False
    )
    
    print_header("Step 5: Local Services")
    use_defaults = input("\nUse default local settings? (Y/n): ")
    if use_defaults.lower() != 'n':
        config['DATABASE_URL'] = "postgresql://roadtrip:roadtrip123@localhost:5432/roadtrip"
        config['REDIS_URL'] = "redis://localhost:6379"
        config['SECRET_KEY'] = "dev-secret-key-change-in-production"
        print_success("Using default local settings")
    else:
        config['DATABASE_URL'] = get_api_key(
            "Database URL",
            "PostgreSQL connection string"
        )
        config['REDIS_URL'] = get_api_key(
            "Redis URL",
            "Redis connection string"
        )
        config['SECRET_KEY'] = get_api_key(
            "Secret Key",
            "Random string for security"
        )
    
    # Add environment settings
    config['ENVIRONMENT'] = "development"
    config['DEBUG'] = "true"
    config['LOG_LEVEL'] = "INFO"
    
    # Write .env file
    print_header("Saving Configuration")
    with open(".env", "w") as f:
        f.write("# AI Road Trip Storyteller Configuration\n")
        f.write("# Generated by configure_apis_simple.py\n\n")
        
        for key, value in config.items():
            if value:  # Only write non-empty values
                f.write(f"{key}={value}\n")
    
    print_success(".env file created successfully!")
    
    # Create .env.example
    with open(".env.example", "w") as f:
        f.write("# AI Road Trip Storyteller Configuration Template\n\n")
        for key in config.keys():
            f.write(f"{key}=your_{key.lower()}_here\n")
    
    print_success(".env.example template created!")
    
    # Summary
    print_header("Configuration Summary")
    configured = sum(1 for v in config.values() if v and not v.startswith("dev-"))
    total = len([k for k in config.keys() if not k.startswith("DATABASE") and not k.startswith("REDIS") and k != "SECRET_KEY"])
    
    print(f"\n📊 APIs Configured: {configured}/{total}")
    print("\n✅ Required APIs:")
    print(f"   - Google Maps: {'✓' if config.get('GOOGLE_MAPS_API_KEY') else '✗'}")
    print(f"   - Google Cloud Project: {'✓' if config.get('GOOGLE_CLOUD_PROJECT_ID') else '✗'}")
    
    print("\n📦 Optional APIs:")
    print(f"   - Recreation.gov: {'✓' if config.get('RECREATION_GOV_API_KEY') else '✗ (will use mock)'}")
    print(f"   - Ticketmaster: {'✓' if config.get('TICKETMASTER_API_KEY') else '✗ (will use mock)'}")
    print(f"   - OpenWeatherMap: {'✓' if config.get('OPENWEATHERMAP_API_KEY') else '✗ (will use mock)'}")
    
    print("\n✈️  Flight Tracking:")
    flight_apis = ['AVIATIONSTACK_API_KEY', 'FLIGHTSTATS_API_KEY', 'FLIGHTAWARE_API_KEY', 'FLIGHTLABS_API_KEY']
    configured_flight = any(config.get(api) for api in flight_apis)
    if configured_flight:
        print(f"   - AviationStack: {'✓' if config.get('AVIATIONSTACK_API_KEY') else '✗'}")
        print(f"   - FlightStats: {'✓' if config.get('FLIGHTSTATS_API_KEY') else '✗'}")
        print(f"   - FlightAware: {'✓' if config.get('FLIGHTAWARE_API_KEY') else '✗'}")
        print(f"   - FlightLabs: {'✓' if config.get('FLIGHTLABS_API_KEY') else '✗'}")
    else:
        print("   ✗ No flight tracking APIs configured (will use mock data)")
    
    print("\n🍽️  Partner APIs:")
    print(f"   - OpenTable: {'✓' if config.get('OPENTABLE_CLIENT_ID') else '✗ (will use mock)'}")
    print(f"   - Shell Recharge: {'✓' if config.get('SHELL_RECHARGE_API_KEY') else '✗ (will use mock)'}")
    
    print("\n🚀 Next Steps:")
    print("1. If you haven't already, enable Google Cloud APIs:")
    print("   - Maps JavaScript API")
    print("   - Places API") 
    print("   - Directions API")
    print("   - Cloud Text-to-Speech API")
    print("   - Cloud Speech-to-Text API")
    print("   - Vertex AI API")
    print("\n2. Run the simulation to test:")
    print("   python scripts/run_simulation.py")
    print("\n3. Launch the beta:")
    print("   ./scripts/launch_beta.sh")

def main():
    """Main entry point"""
    # Change to project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        create_env_file()
    except KeyboardInterrupt:
        print("\n\n❌ Configuration cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")

if __name__ == "__main__":
    main()