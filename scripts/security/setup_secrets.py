#!/usr/bin/env python3
"""
Script to set up secrets in Google Secret Manager.
Run this after creating a new GCP project to configure all required secrets.
"""
import os
import sys
import json
import secrets
import base64
from typing import Dict, Any

from google.cloud import secretmanager


def generate_secure_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_urlsafe(length)


def create_secret(client: secretmanager.SecretManagerServiceClient, 
                 project_id: str, 
                 secret_id: str, 
                 secret_value: str) -> None:
    """Create a new secret in Secret Manager."""
    parent = f"projects/{project_id}"
    
    try:
        # Create the secret
        secret = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Created secret: {secret_id}")
        
        # Add the secret version
        client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )
        print(f"Added secret version for: {secret_id}")
        
    except Exception as e:
        print(f"Error creating secret {secret_id}: {e}")


def main():
    # Check if running in production
    if os.getenv("ENVIRONMENT") != "production":
        print("WARNING: This script should only be run in production!")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            sys.exit(0)
    
    # Get project ID
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        project_id = input("Enter your GCP project ID: ")
    
    # Initialize client
    client = secretmanager.SecretManagerServiceClient()
    
    # Generate new secrets
    secrets_to_create = {
        "jwt-secret-key": generate_secure_key(64),
        "csrf-secret-key": generate_secure_key(64),
        "encryption-key": generate_secure_key(32),
        "database-url": input("Enter production database URL: "),
        "redis-password": generate_secure_key(32),
    }
    
    # API keys (must be obtained from providers)
    print("\nEnter API keys (leave blank to skip):")
    api_keys = {
        "google-maps-api-key": input("Google Maps API key: "),
        "ticketmaster-api-key": input("Ticketmaster API key: "),
        "openweathermap-api-key": input("OpenWeatherMap API key: "),
        "spotify-client-id": input("Spotify Client ID: "),
        "spotify-client-secret": input("Spotify Client Secret: "),
    }
    
    # Add non-empty API keys
    for key, value in api_keys.items():
        if value:
            secrets_to_create[key] = value
    
    # Create all secrets
    print("\nCreating secrets in Secret Manager...")
    for secret_id, secret_value in secrets_to_create.items():
        if secret_value:
            create_secret(client, project_id, secret_id, secret_value)
    
    # Generate .env.production.template
    print("\nGenerating .env.production.template...")
    template_content = """# Production Environment Variables Template
# DO NOT COMMIT THIS FILE WITH ACTUAL VALUES

# Core Configuration
ENVIRONMENT=production
GOOGLE_CLOUD_PROJECT={project_id}
VERTEX_AI_LOCATION=us-central1

# These values are stored in Secret Manager
# Do not set them here in production
DATABASE_URL=# Stored in Secret Manager
JWT_SECRET_KEY=# Stored in Secret Manager
CSRF_SECRET_KEY=# Stored in Secret Manager
ENCRYPTION_KEY=# Stored in Secret Manager
REDIS_PASSWORD=# Stored in Secret Manager

# API Keys - Stored in Secret Manager
GOOGLE_MAPS_API_KEY=# Stored in Secret Manager
TICKETMASTER_API_KEY=# Stored in Secret Manager
OPENWEATHERMAP_API_KEY=# Stored in Secret Manager
SPOTIFY_CLIENT_ID=# Stored in Secret Manager
SPOTIFY_CLIENT_SECRET=# Stored in Secret Manager

# Public Configuration
REDIS_URL=redis://redis:6379/0
BACKEND_CORS_ORIGINS=["https://your-domain.com"]
FORCE_HTTPS=true
SECURE_COOKIES=true
SAMESITE_COOKIES=strict
""".format(project_id=project_id)
    
    with open(".env.production.template", "w") as f:
        f.write(template_content)
    
    print("\n✅ Secret setup complete!")
    print("\nIMPORTANT NEXT STEPS:")
    print("1. Enable Secret Manager API in your GCP project")
    print("2. Grant your service account 'Secret Manager Secret Accessor' role")
    print("3. Test secret access with: gcloud secrets versions access latest --secret='jwt-secret-key'")
    print("4. Update your deployment scripts to use Secret Manager")
    print("\nGenerated keys have been saved to Secret Manager.")
    print("DO NOT save these keys anywhere else!")


if __name__ == "__main__":
    main()