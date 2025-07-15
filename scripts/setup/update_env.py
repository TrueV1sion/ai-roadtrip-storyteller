#!/usr/bin/env python3
"""
Simple script to update .env file with real API keys
"""

import os
from pathlib import Path

def update_env():
    """Update .env file with user's API keys"""
    
    print("🔑 Update Your API Keys")
    print("=" * 40)
    print("Enter your API keys (press Enter to skip/keep current value):")
    print()
    
    # Read current .env
    env_file = Path(".env")
    current_values = {}
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    current_values[key] = value
    
    # API keys to update
    api_keys = {
        'GOOGLE_MAPS_API_KEY': 'Google Maps API Key',
        'GOOGLE_CLOUD_PROJECT_ID': 'Google Cloud Project ID',
        'RECREATION_GOV_API_KEY': 'Recreation.gov API Key',
        'TICKETMASTER_API_KEY': 'Ticketmaster API Key', 
        'OPENWEATHERMAP_API_KEY': 'OpenWeatherMap API Key',
        'AVIATIONSTACK_API_KEY': 'AviationStack API Key (Free tier)',
        'FLIGHTSTATS_APP_ID': 'FlightStats App ID',
        'FLIGHTSTATS_API_KEY': 'FlightStats API Key',
        'FLIGHTAWARE_API_KEY': 'FlightAware API Key',
        'FLIGHTLABS_API_KEY': 'FlightLabs API Key'
    }
    
    new_values = current_values.copy()
    
    for key, description in api_keys.items():
        current = current_values.get(key, 'not_set')
        print(f"\n📌 {description}")
        if current and not current.startswith('mock_') and current != 'not_set':
            print(f"   Current: {current[:10]}...")
        else:
            print(f"   Current: Not configured")
        
        new_key = input(f"   Enter new value (or press Enter to keep current): ").strip()
        if new_key:
            new_values[key] = new_key
            print(f"   ✅ Updated!")
    
    # Write updated .env
    with open(".env", "w") as f:
        f.write("# AI Road Trip Storyteller Configuration\n")
        f.write("# Updated with real API keys\n\n")
        
        # Core APIs
        f.write("# ==== Google Cloud Platform ====\n")
        f.write(f"GOOGLE_MAPS_API_KEY={new_values.get('GOOGLE_MAPS_API_KEY', 'your_google_key_here')}\n")
        f.write(f"GOOGLE_CLOUD_PROJECT_ID={new_values.get('GOOGLE_CLOUD_PROJECT_ID', 'your-project-id')}\n\n")
        
        # Free APIs
        f.write("# ==== Free APIs ====\n")
        f.write(f"RECREATION_GOV_API_KEY={new_values.get('RECREATION_GOV_API_KEY', 'mock_recreation_gov_key')}\n")
        f.write(f"TICKETMASTER_API_KEY={new_values.get('TICKETMASTER_API_KEY', 'mock_ticketmaster_key')}\n")
        f.write(f"OPENWEATHERMAP_API_KEY={new_values.get('OPENWEATHERMAP_API_KEY', 'mock_weather_key')}\n\n")
        
        # Flight Tracking APIs
        f.write("# ==== Flight Tracking APIs ====\n")
        f.write(f"AVIATIONSTACK_API_KEY={new_values.get('AVIATIONSTACK_API_KEY', '')}\n")
        f.write(f"FLIGHTSTATS_APP_ID={new_values.get('FLIGHTSTATS_APP_ID', '')}\n")
        f.write(f"FLIGHTSTATS_API_KEY={new_values.get('FLIGHTSTATS_API_KEY', '')}\n")
        f.write(f"FLIGHTAWARE_API_KEY={new_values.get('FLIGHTAWARE_API_KEY', '')}\n")
        f.write(f"FLIGHTLABS_API_KEY={new_values.get('FLIGHTLABS_API_KEY', '')}\n\n")
        
        # Partner APIs (mock for now)
        f.write("# ==== Partner APIs (using mock mode) ====\n")
        f.write("OPENTABLE_CLIENT_ID=mock_opentable_id\n")
        f.write("OPENTABLE_CLIENT_SECRET=mock_opentable_secret\n")
        f.write("SHELL_RECHARGE_API_KEY=mock_shell_key\n\n")
        
        # Local settings
        f.write("# ==== Local Development ====\n")
        f.write("DATABASE_URL=postgresql://roadtrip:roadtrip123@localhost:5432/roadtrip\n")
        f.write("REDIS_URL=redis://localhost:6379\n")
        f.write("SECRET_KEY=dev-secret-key-change-in-production\n\n")
        
        # App settings
        f.write("# ==== App Settings ====\n")
        f.write("ENVIRONMENT=development\n")
        f.write("DEBUG=true\n")
        f.write("LOG_LEVEL=INFO\n")
        
        # Feature flags
        f.write("USE_MOCK_APIS=false\n")
        f.write("ENABLE_VOICE_SAFETY=true\n")
        f.write("ENABLE_BOOKING_COMMISSION=true\n")
        f.write("ENABLE_SEASONAL_PERSONALITIES=true\n")
    
    print("\n✅ .env file updated successfully!")
    
    # Test configuration
    print("\n🧪 Testing configuration:")
    configured_count = 0
    for key in api_keys.keys():
        value = new_values.get(key, '')
        if value and not value.startswith('mock_') and value != 'your_' + key.lower() + '_here':
            print(f"   ✅ {key}: Configured")
            configured_count += 1
        else:
            print(f"   ⚠️  {key}: Using mock/default")
    
    # Check flight tracking APIs separately
    flight_apis = ['AVIATIONSTACK_API_KEY', 'FLIGHTSTATS_API_KEY', 'FLIGHTAWARE_API_KEY', 'FLIGHTLABS_API_KEY']
    flight_configured = any(new_values.get(api, '').strip() and not new_values.get(api, '').startswith('mock_') for api in flight_apis)
    
    print(f"\n📊 APIs configured:")
    print(f"   Core APIs: {min(configured_count, 5)}/5")
    print(f"   Flight Tracking: {'✓' if flight_configured else '✗ (will use mock data)'}")
    
    if configured_count >= 2:
        print("\n🚀 Ready to test! You have enough APIs configured.")
        print("Next steps:")
        print("1. ./scripts/launch_beta.sh")
        print("2. python3 scripts/run_simulation.py")
        if flight_configured:
            print("3. TEST_MODE=live pytest tests/integration/live/test_flight_tracker_integration.py -v")
    else:
        print("\n💡 Tip: Get at least Google Maps + Recreation.gov for best testing experience!")
        print("   For flight tracking, AviationStack offers a free tier.")

if __name__ == "__main__":
    update_env()