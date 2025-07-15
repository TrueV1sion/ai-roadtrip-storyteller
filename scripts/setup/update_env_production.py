#!/usr/bin/env python3
"""
Update .env file for production deployment.
"""
import os
import secrets
import string
from datetime import datetime


def generate_secret_key(length=64):
    """Generate a secure secret key."""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def main():
    # Read current .env
    current_env = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    current_env[key] = value
    
    # Map old variable names to new ones
    variable_mapping = {
        'GOOGLE_CLOUD_PROJECT_ID': 'GCP_PROJECT_ID',
        'VERTEX_AI_LOCATION': 'GOOGLE_AI_LOCATION'
    }
    
    # Update with correct variable names
    for old_key, new_key in variable_mapping.items():
        if old_key in current_env and new_key not in current_env:
            current_env[new_key] = current_env[old_key]
    
    # Add missing required variables
    updates = {
        # Core Google Cloud
        'GCP_PROJECT_ID': current_env.get('GOOGLE_CLOUD_PROJECT_ID', 'roadtrip-460720'),
        'GOOGLE_AI_PROJECT_ID': current_env.get('GOOGLE_CLOUD_PROJECT_ID', 'roadtrip-460720'),
        'GOOGLE_AI_LOCATION': current_env.get('VERTEX_AI_LOCATION', 'us-central1'),
        'GOOGLE_AI_MODEL': 'gemini-1.5-flash',
        'GCS_BUCKET_NAME': f"{current_env.get('GOOGLE_CLOUD_PROJECT_ID', 'roadtrip-460720')}-roadtrip-assets",
        
        # Security keys (generate new ones for production)
        'SECRET_KEY': generate_secret_key(),
        'JWT_SECRET_KEY': generate_secret_key(),
        
        # Database (update for production deployment)
        'DB_USER': 'roadtrip',
        'DB_PASSWORD': current_env.get('DB_PASSWORD', 'roadtrip123'),
        'DB_NAME': 'roadtrip',
        
        # Redis
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        
        # App settings for production
        'ENVIRONMENT': 'production',
        'APP_VERSION': '1.0.0',
        'DEBUG': 'false',
        'LOG_LEVEL': 'INFO',
        'TEST_MODE': 'live',
        
        # Feature flags
        'ENABLE_VOICE_SAFETY': 'true',
        'ENABLE_BOOKING_COMMISSION': 'true',
        'ENABLE_SEASONAL_PERSONALITIES': 'true',
        'ENABLE_AR_FEATURES': 'true',
        'ENABLE_SOCIAL_SHARING': 'true',
        
        # Performance settings
        'MAX_CONCURRENT_REQUESTS': '100',
        'CACHE_TTL_SECONDS': '3600',
        'AI_TIMEOUT_SECONDS': '30',
        'MAX_DRIVING_SPEED_MPH': '75',
        'VOICE_INTERACTION_COOLDOWN_MS': '2000'
    }
    
    # Merge with current env, preserving existing values
    for key, value in updates.items():
        if key not in current_env:
            current_env[key] = value
    
    # Backup current .env
    if os.path.exists('.env'):
        backup_name = f'.env.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.rename('.env', backup_name)
        print(f"✓ Backed up current .env to {backup_name}")
    
    # Write updated .env
    with open('.env', 'w') as f:
        f.write("# AI Road Trip Storyteller Configuration\n")
        f.write("# Updated for production deployment\n")
        f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Group variables
        groups = {
            "Core Configuration": [
                'ENVIRONMENT', 'APP_VERSION', 'SECRET_KEY', 'JWT_SECRET_KEY'
            ],
            "Google Cloud Platform": [
                'GCP_PROJECT_ID', 'GOOGLE_AI_PROJECT_ID', 'GOOGLE_AI_LOCATION',
                'GOOGLE_AI_MODEL', 'GCS_BUCKET_NAME', 'GOOGLE_APPLICATION_CREDENTIALS',
                'GOOGLE_MAPS_API_KEY'
            ],
            "Database Configuration": [
                'DATABASE_URL', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'
            ],
            "Redis Configuration": [
                'REDIS_URL', 'REDIS_HOST', 'REDIS_PORT'
            ],
            "API Keys": [
                'TICKETMASTER_API_KEY', 'TICKETMASTER_API_SECRET',
                'OPENWEATHERMAP_API_KEY', 'RECREATION_GOV_API_KEY',
                'OPENTABLE_CLIENT_ID', 'OPENTABLE_CLIENT_SECRET',
                'SHELL_RECHARGE_API_KEY'
            ],
            "Feature Flags": [
                'ENABLE_VOICE_SAFETY', 'ENABLE_BOOKING_COMMISSION',
                'ENABLE_SEASONAL_PERSONALITIES', 'ENABLE_AR_FEATURES',
                'ENABLE_SOCIAL_SHARING'
            ],
            "Performance Settings": [
                'MAX_CONCURRENT_REQUESTS', 'CACHE_TTL_SECONDS',
                'AI_TIMEOUT_SECONDS', 'MAX_DRIVING_SPEED_MPH',
                'VOICE_INTERACTION_COOLDOWN_MS'
            ],
            "Application Settings": [
                'DEBUG', 'LOG_LEVEL', 'TEST_MODE', 'USE_MOCK_APIS'
            ]
        }
        
        # Write grouped variables
        for group_name, keys in groups.items():
            f.write(f"# ==== {group_name} ====\n")
            for key in keys:
                if key in current_env:
                    f.write(f"{key}={current_env[key]}\n")
            f.write("\n")
        
        # Write any remaining variables
        written_keys = set()
        for keys in groups.values():
            written_keys.update(keys)
        
        remaining = {k: v for k, v in current_env.items() if k not in written_keys}
        if remaining:
            f.write("# ==== Other Settings ====\n")
            for key, value in remaining.items():
                f.write(f"{key}={value}\n")
    
    print("✓ Updated .env file for production")
    print("\nKey changes made:")
    print("- Added GCP_PROJECT_ID and GOOGLE_AI_PROJECT_ID")
    print("- Added GOOGLE_AI_MODEL configuration")
    print("- Generated new SECRET_KEY and JWT_SECRET_KEY")
    print("- Set ENVIRONMENT=production")
    print("- Added all feature flags and performance settings")
    print("\nNext steps:")
    print("1. Review the updated .env file")
    print("2. Ensure service account key exists at:", current_env.get('GOOGLE_APPLICATION_CREDENTIALS', './credentials/vertex-ai-key.json'))
    print("3. Run: python3 setup_infrastructure.py")


if __name__ == "__main__":
    main()