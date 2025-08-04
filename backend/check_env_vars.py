#!/usr/bin/env python3
"""
Check and validate required environment variables for the backend.
"""

import os
import sys
from typing import Dict, List, Tuple

# Define required and optional environment variables
REQUIRED_VARS = {
    "DATABASE_URL": "PostgreSQL connection string (e.g., postgresql://user:pass@host/db)",
    "JWT_SECRET_KEY": "Secret key for JWT token generation",
    "GOOGLE_CLOUD_PROJECT": "Google Cloud project ID",
    "GOOGLE_AI_PROJECT_ID": "Google AI/Vertex AI project ID",
    "GOOGLE_AI_LOCATION": "Google AI location (e.g., us-central1)",
}

OPTIONAL_VARS = {
    "REDIS_URL": "Redis connection string (defaults to redis://localhost:6379)",
    "GOOGLE_MAPS_API_KEY": "Google Maps API key for location services",
    "OPENWEATHER_API_KEY": "OpenWeather API key for weather data",
    "TICKETMASTER_API_KEY": "Ticketmaster API key for event bookings",
    "TICKETMASTER_API_SECRET": "Ticketmaster API secret",
    "OPENTABLE_API_KEY": "OpenTable API key for restaurant bookings",
    "VIATOR_API_KEY": "Viator API key for tour bookings",
    "RECREATION_GOV_API_KEY": "Recreation.gov API key for park bookings",
    "SPOTIFY_CLIENT_ID": "Spotify client ID for music integration",
    "SPOTIFY_CLIENT_SECRET": "Spotify client secret",
    "SENTRY_DSN": "Sentry DSN for error tracking",
    "ENVIRONMENT": "Environment name (development/staging/production)",
    "LOG_LEVEL": "Logging level (DEBUG/INFO/WARNING/ERROR)",
    "CORS_ORIGINS": "Comma-separated list of allowed CORS origins",
    "PORT": "Port to run the application on (defaults to 8080)",
}

def check_environment() -> Tuple[List[str], List[str], Dict[str, str]]:
    """Check environment variables and return status."""
    missing_required = []
    missing_optional = []
    present_vars = {}
    
    # Check required variables
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_required.append(f"{var}: {description}")
        else:
            # Mask sensitive values
            if "SECRET" in var or "PASSWORD" in var or "KEY" in var:
                present_vars[var] = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            elif "URL" in var and "@" in value:
                # Mask database URLs
                parts = value.split("@")
                if len(parts) > 1:
                    present_vars[var] = f"{parts[0].split('://')[0]}://***@{parts[1]}"
                else:
                    present_vars[var] = "***"
            else:
                present_vars[var] = value
    
    # Check optional variables
    for var, description in OPTIONAL_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_optional.append(f"{var}: {description}")
        else:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var:
                present_vars[var] = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                present_vars[var] = value
    
    return missing_required, missing_optional, present_vars

def generate_env_template():
    """Generate a .env.example template file."""
    template = """# AI Road Trip Storyteller Backend Environment Variables
# Copy this file to .env and fill in your values

# Required Variables
"""
    
    for var, description in REQUIRED_VARS.items():
        template += f"\n# {description}\n{var}=\n"
    
    template += "\n# Optional Variables\n"
    
    for var, description in OPTIONAL_VARS.items():
        template += f"\n# {description}\n{var}=\n"
    
    with open(".env.example", "w") as f:
        f.write(template)
    
    print("Generated .env.example template file")

def main():
    """Main function to check environment variables."""
    print("=== AI Road Trip Backend Environment Check ===\n")
    
    missing_required, missing_optional, present_vars = check_environment()
    
    # Display present variables
    if present_vars:
        print("✓ Present Environment Variables:")
        for var, value in sorted(present_vars.items()):
            print(f"  {var}: {value}")
        print()
    
    # Display missing required variables
    if missing_required:
        print("✗ Missing Required Variables:")
        for var in missing_required:
            print(f"  {var}")
        print()
    
    # Display missing optional variables
    if missing_optional:
        print("⚠ Missing Optional Variables (app will work but with reduced functionality):")
        for var in missing_optional:
            print(f"  {var}")
        print()
    
    # Summary
    if missing_required:
        print("❌ FAIL: Missing required environment variables!")
        print("   The application will not start properly without these variables.")
        print("\nTo fix this:")
        print("1. Create a .env file in the backend directory")
        print("2. Add the missing required variables")
        print("3. Run this script again to verify")
        
        if not os.path.exists(".env.example"):
            print("\nGenerating .env.example template...")
            generate_env_template()
        
        sys.exit(1)
    else:
        print("✅ SUCCESS: All required environment variables are present!")
        print("   The application should start successfully.")
        
        if missing_optional:
            print("\n💡 TIP: Consider adding optional variables for full functionality:")
            print("   - Maps integration requires GOOGLE_MAPS_API_KEY")
            print("   - Booking features require partner API keys")
            print("   - Music features require Spotify credentials")

if __name__ == "__main__":
    main()