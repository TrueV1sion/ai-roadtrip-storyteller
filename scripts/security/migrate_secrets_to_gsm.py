#!/usr/bin/env python3
"""
Migrate all secrets from .env file to Google Secret Manager.
This script should be run once to move all sensitive data to GSM.
"""
import os
import sys
import json
from datetime import datetime
from google.cloud import secretmanager
from pathlib import Path
import argparse

# Secrets that should be migrated to Google Secret Manager
SECRETS_TO_MIGRATE = [
    'SECRET_KEY',
    'JWT_SECRET_KEY',
    'DATABASE_URL',
    'DB_PASSWORD',
    'GOOGLE_MAPS_API_KEY',
    'TICKETMASTER_API_KEY',
    'TICKETMASTER_API_SECRET',
    'OPENWEATHERMAP_API_KEY',
    'OPENTABLE_CLIENT_ID',
    'OPENTABLE_CLIENT_SECRET',
    'SHELL_RECHARGE_API_KEY',
    'REDIS_URL',
    'REDIS_PASSWORD',  # If using Redis with auth
]

# Non-sensitive configs that can remain in .env
PUBLIC_CONFIGS = [
    'ENVIRONMENT',
    'APP_VERSION',
    'GCP_PROJECT_ID',
    'GOOGLE_AI_PROJECT_ID',
    'GOOGLE_AI_LOCATION',
    'GOOGLE_AI_MODEL',
    'GCS_BUCKET_NAME',
    'DB_USER',
    'DB_NAME',
    'REDIS_HOST',
    'REDIS_PORT',
    'ENABLE_VOICE_SAFETY',
    'ENABLE_BOOKING_COMMISSION',
    'ENABLE_SEASONAL_PERSONALITIES',
    'ENABLE_AR_FEATURES',
    'ENABLE_SOCIAL_SHARING',
    'MAX_CONCURRENT_REQUESTS',
    'CACHE_TTL_SECONDS',
    'AI_TIMEOUT_SECONDS',
    'MAX_DRIVING_SPEED_MPH',
    'VOICE_INTERACTION_COOLDOWN_MS',
    'DEBUG',
    'LOG_LEVEL',
    'TEST_MODE',
    'USE_MOCK_APIS',
    'VERTEX_AI_LOCATION',
]


def read_env_file(env_path):
    """Read and parse .env file."""
    env_vars = {}
    
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found")
        return env_vars
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def generate_strong_secret():
    """Generate a cryptographically strong secret."""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(64))


def create_or_update_secret(client, project_id, secret_id, secret_value):
    """Create or update a secret in Google Secret Manager."""
    parent = f"projects/{project_id}"
    secret_name = f"{parent}/secrets/{secret_id}"
    
    try:
        # Try to get the secret first
        client.get_secret(request={"name": secret_name})
        print(f"Secret {secret_id} already exists, adding new version...")
        
        # Add a new version
        response = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )
        print(f"Added new version for {secret_id}: {response.name}")
        
    except Exception:
        # Secret doesn't exist, create it
        print(f"Creating new secret {secret_id}...")
        
        # Create the secret
        secret = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {
                    "replication": {"automatic": {}},
                    "labels": {
                        "app": "roadtrip",
                        "environment": "production",
                        "managed-by": "migration-script"
                    }
                },
            }
        )
        
        # Add the secret version
        version = client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )
        print(f"Created secret {secret_id}: {version.name}")


def create_production_env_file(env_vars, output_path):
    """Create a production .env file with only public configs."""
    with open(output_path, 'w') as f:
        f.write("# AI Road Trip Storyteller Production Configuration\n")
        f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# Secrets are stored in Google Secret Manager\n\n")
        
        f.write("# ==== Core Configuration ====\n")
        f.write("ENVIRONMENT=production\n")
        f.write("PRODUCTION=true\n")
        f.write("FORCE_HTTPS=true\n")
        f.write("SECURE_COOKIES=true\n")
        
        for key in PUBLIC_CONFIGS:
            if key in env_vars:
                # Override certain values for production
                if key == 'DEBUG':
                    f.write("DEBUG=false\n")
                elif key == 'LOG_LEVEL':
                    f.write("LOG_LEVEL=WARNING\n")
                elif key == 'TEST_MODE':
                    f.write("TEST_MODE=false\n")
                elif key == 'USE_MOCK_APIS':
                    f.write("USE_MOCK_APIS=false\n")
                else:
                    f.write(f"{key}={env_vars[key]}\n")
        
        f.write("\n# ==== Secret Manager Configuration ====\n")
        f.write("USE_SECRET_MANAGER=true\n")
        f.write("SECRET_MANAGER_PROJECT_ID=${GCP_PROJECT_ID}\n")


def main():
    parser = argparse.ArgumentParser(description='Migrate secrets to Google Secret Manager')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--env-file', default='.env', help='Path to .env file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
    parser.add_argument('--regenerate-keys', action='store_true', help='Generate new secure keys')
    args = parser.parse_args()
    
    # Read current .env file
    env_vars = read_env_file(args.env_file)
    
    if not env_vars:
        print("No environment variables found")
        return 1
    
    # Initialize Secret Manager client
    if not args.dry_run:
        client = secretmanager.SecretManagerServiceClient()
    
    print(f"Migrating secrets to Google Secret Manager for project: {args.project_id}\n")
    
    # Migrate secrets
    migration_summary = []
    
    for secret_key in SECRETS_TO_MIGRATE:
        if secret_key in env_vars:
            secret_value = env_vars[secret_key]
            
            # Generate new secure values for certain keys
            if args.regenerate_keys:
                if secret_key in ['SECRET_KEY', 'JWT_SECRET_KEY']:
                    old_value = secret_value[:10] + "..." if len(secret_value) > 10 else secret_value
                    secret_value = generate_strong_secret()
                    print(f"Regenerating {secret_key}: {old_value} -> [NEW SECURE VALUE]")
                elif secret_key == 'DB_PASSWORD' and secret_value == 'roadtrip123':
                    secret_value = generate_strong_secret()[:32]  # Reasonable password length
                    print(f"Generating secure password for {secret_key}")
            
            secret_id = f"roadtrip-{secret_key.lower().replace('_', '-')}"
            
            if args.dry_run:
                print(f"Would create/update secret: {secret_id}")
                migration_summary.append((secret_key, secret_id, "DRY RUN"))
            else:
                try:
                    create_or_update_secret(client, args.project_id, secret_id, secret_value)
                    migration_summary.append((secret_key, secret_id, "SUCCESS"))
                except Exception as e:
                    print(f"Error creating secret {secret_id}: {e}")
                    migration_summary.append((secret_key, secret_id, f"FAILED: {e}"))
    
    # Create production .env file
    production_env_path = '.env.production'
    if not args.dry_run:
        create_production_env_file(env_vars, production_env_path)
        print(f"\nCreated production environment file: {production_env_path}")
    
    # Print summary
    print("\n=== Migration Summary ===")
    for key, secret_id, status in migration_summary:
        print(f"{key} -> {secret_id}: {status}")
    
    # Print instructions
    print("\n=== Next Steps ===")
    print("1. Review and test the migration")
    print("2. Update your application to use Google Secret Manager")
    print("3. Delete the original .env file with secrets")
    print("4. Use .env.production for non-sensitive configuration")
    print("5. Grant necessary IAM permissions to service accounts:")
    print(f"   gcloud projects add-iam-policy-binding {args.project_id} \\")
    print("     --member='serviceAccount:YOUR-SERVICE-ACCOUNT@PROJECT.iam.gserviceaccount.com' \\")
    print("     --role='roles/secretmanager.secretAccessor'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())