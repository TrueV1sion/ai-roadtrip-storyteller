#!/usr/bin/env python3
"""
Fix secret name mismatches between application code and Secret Manager.
This script creates aliases and updates mappings to ensure consistency.
"""

import subprocess
import json
import sys
from typing import Dict, List, Tuple

# Color codes for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Mapping of what the app expects vs what's in Secret Manager
SECRET_MAPPINGS = {
    # Core secrets
    "DATABASE_URL": "roadtrip-database-url",
    "SECRET_KEY": "roadtrip-secret-key",
    "JWT_SECRET_KEY": "roadtrip-jwt-secret",
    "CSRF_SECRET_KEY": "roadtrip-csrf-secret",
    "REDIS_URL": "roadtrip-redis-url",
    "GCS_BUCKET_NAME": "roadtrip-gcs-bucket",
    
    # API Keys - note the naming differences
    "GOOGLE_MAPS_API_KEY": "roadtrip-google-maps-key",
    "OPENWEATHERMAP_API_KEY": "roadtrip-openweather-key",  # App expects OPENWEATHERMAP
    "OPENWEATHER_API_KEY": "roadtrip-openweather-key",     # CloudBuild uses OPENWEATHER
    "TICKETMASTER_API_KEY": "roadtrip-ticketmaster-key",
    "TICKETMASTER_API_SECRET": "roadtrip-ticketmaster-secret",
    "RECREATION_GOV_API_KEY": "roadtrip-recreation-key",
    "RECREATION_GOV_API_SECRET": "roadtrip-recreation-secret",
    "RECREATION_GOV_ACCOUNT_ID": "roadtrip-recreation-account",
    
    # Optional APIs
    "OPENTABLE_API_KEY": "roadtrip-opentable-key",
    "OPENTABLE_CLIENT_ID": "roadtrip-opentable-id",
    "OPENTABLE_CLIENT_SECRET": "roadtrip-opentable-secret",
    "OPENTABLE_PARTNER_ID": "roadtrip-opentable-partner",
    "VIATOR_API_KEY": "roadtrip-viator-key",
    "VIATOR_PARTNER_ID": "roadtrip-viator-partner",
    "SPOTIFY_CLIENT_ID": "roadtrip-spotify-id",
    "SPOTIFY_CLIENT_SECRET": "roadtrip-spotify-secret",
    "RESY_API_KEY": "roadtrip-resy-key",
    "RESY_CLIENT_ID": "roadtrip-resy-id",
    "RESY_CLIENT_SECRET": "roadtrip-resy-secret",
    "SHELL_RECHARGE_API_KEY": "roadtrip-shell-key",
    "CHARGEPOINT_API_KEY": "roadtrip-chargepoint-key",
    "CHARGEPOINT_CLIENT_ID": "roadtrip-chargepoint-id",
    "CHARGEPOINT_CLIENT_SECRET": "roadtrip-chargepoint-secret",
    
    # Flight tracking
    "FLIGHT_TRACKING_API_KEY": "roadtrip-flight-tracking-key",
    "FLIGHTSTATS_API_KEY": "roadtrip-flightstats-key",
    "FLIGHTSTATS_APP_ID": "roadtrip-flightstats-id",
    "FLIGHTAWARE_API_KEY": "roadtrip-flightaware-key",
    "AVIATIONSTACK_API_KEY": "roadtrip-aviationstack-key",
    "FLIGHTLABS_API_KEY": "roadtrip-flightlabs-key",
    
    # Airport services
    "PRIORITY_PASS_API_KEY": "roadtrip-priority-pass-key",
    "AIRLINE_LOUNGE_API_KEY": "roadtrip-airline-lounge-key",
    
    # Communication
    "TWILIO_ACCOUNT_SID": "roadtrip-twilio-sid",
    "TWILIO_AUTH_TOKEN": "roadtrip-twilio-token",
    "TWILIO_FROM_PHONE": "roadtrip-twilio-phone",
    "SENDGRID_API_KEY": "roadtrip-sendgrid-key",
    
    # Other
    "TWO_FACTOR_SECRET": "roadtrip-two-factor-secret",
    "ENCRYPTION_KEY": "encryption-key",
}

def run_command(cmd: List[str]) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def create_secret_alias(env_var: str, secret_id: str, project_id: str):
    """Create an alias for a secret if it doesn't exist."""
    # For now, we'll just document the mapping
    # In a real scenario, you might create duplicate secrets or use labels
    print(f"  {env_var} -> {secret_id}")

def main(project_id: str = "roadtrip-460720"):
    print(f"{BLUE}RoadTrip Secret Mapping Fixer{NC}")
    print(f"{BLUE}============================={NC}")
    print(f"Project ID: {project_id}\n")
    
    print(f"{YELLOW}Secret Name Mappings:{NC}")
    print("=====================")
    
    # Group by secret ID to show all env vars that map to it
    reverse_mapping: Dict[str, List[str]] = {}
    for env_var, secret_id in SECRET_MAPPINGS.items():
        if secret_id not in reverse_mapping:
            reverse_mapping[secret_id] = []
        reverse_mapping[secret_id].append(env_var)
    
    # Display mappings
    for secret_id, env_vars in sorted(reverse_mapping.items()):
        print(f"\n{GREEN}{secret_id}:{NC}")
        for env_var in sorted(env_vars):
            print(f"  - {env_var}")
    
    print(f"\n{YELLOW}Generating Updated CloudBuild Configuration:{NC}")
    print("==========================================")
    
    # Generate the --set-secrets parameter for CloudBuild
    secret_params = []
    seen_secrets = set()
    
    for env_var, secret_id in sorted(SECRET_MAPPINGS.items()):
        # Skip duplicates (e.g., OPENWEATHER_API_KEY and OPENWEATHERMAP_API_KEY)
        if env_var in seen_secrets:
            continue
        
        # Use the actual environment variable name expected by the app
        if env_var == "OPENWEATHER_API_KEY":
            # Skip this one, use OPENWEATHERMAP_API_KEY instead
            continue
            
        secret_params.append(f"{env_var}={secret_id}:latest")
        seen_secrets.add(env_var)
    
    # Format for CloudBuild YAML
    print("\nAdd this to your CloudBuild YAML under --set-secrets:")
    print("------------------------------------------------------")
    print("      - '--set-secrets'")
    print("      - |")
    
    # Group in chunks of 5 for readability
    for i in range(0, len(secret_params), 5):
        chunk = secret_params[i:i+5]
        if i == 0:
            print(f"        {','.join(chunk)}", end="")
        else:
            print(f",\n        {','.join(chunk)}", end="")
    print()
    
    print(f"\n{YELLOW}Creating Environment Variable Mapping:{NC}")
    print("====================================")
    
    # Create a mapping file for the application
    mapping_content = {
        "secret_mappings": SECRET_MAPPINGS,
        "description": "Mapping of environment variables to Google Secret Manager secret IDs",
        "notes": {
            "OPENWEATHERMAP_API_KEY": "Application code expects this name",
            "OPENWEATHER_API_KEY": "CloudBuild YAML uses this name (maps to same secret)",
        }
    }
    
    import os
    mapping_file = os.path.join(os.path.dirname(__file__), "secret-mappings.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping_content, f, indent=2)
    
    print(f"Created mapping file: {mapping_file}")
    
    print(f"\n{GREEN}Next Steps:{NC}")
    print("===========")
    print("1. Update your CloudBuild YAML files with the --set-secrets configuration above")
    print("2. Update backend/app/core/config.py to use consistent naming")
    print("3. Run setup-secrets.sh to create all required secrets")
    print("4. Run validate-secrets.sh to verify everything is configured correctly")

if __name__ == "__main__":
    project_id = sys.argv[1] if len(sys.argv) > 1 else "roadtrip-460720"
    main(project_id)