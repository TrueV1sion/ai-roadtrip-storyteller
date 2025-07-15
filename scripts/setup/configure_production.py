#!/usr/bin/env python3
"""
Production configuration wizard for AI Road Trip Storyteller.
Helps configure all necessary secrets and API keys for production deployment.
"""
import os
import sys
import json
import secrets
import string
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import getpass
import re


class Colors:
    """Terminal colors for better output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})?(/.*)?$'
    return re.match(pattern, url) is not None


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure secret key."""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_gcp_project_id() -> Optional[str]:
    """Get current GCP project ID."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return None


def check_api_key_format(key: str, prefix: str = None) -> bool:
    """Basic validation of API key format."""
    if not key or len(key) < 10:
        return False
    if prefix and not key.startswith(prefix):
        return False
    return True


def configure_core_settings(config: Dict[str, Any]):
    """Configure core application settings."""
    print_header("Core Application Settings")
    
    # Environment
    print_info("Select environment:")
    print("1. Production")
    print("2. Staging")
    print("3. Development")
    env_choice = input("Enter choice (1-3) [1]: ").strip() or "1"
    
    environments = {"1": "production", "2": "staging", "3": "development"}
    config["ENVIRONMENT"] = environments.get(env_choice, "production")
    
    # App version
    current_version = "1.0.0"
    version = input(f"App version [{current_version}]: ").strip() or current_version
    config["APP_VERSION"] = version
    
    # Security keys
    print_info("\nGenerating security keys...")
    config["SECRET_KEY"] = generate_secret_key(64)
    config["JWT_SECRET_KEY"] = generate_secret_key(64)
    print_success("Security keys generated")
    
    # Domain configuration
    domain = input("\nProduction domain (e.g., api.roadtrip.ai): ").strip()
    if domain:
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        config["APP_URL"] = domain
        config["CORS_ORIGINS"] = json.dumps([domain, f"{domain.replace('api.', '')}"])
    
    print_success("Core settings configured")


def configure_google_cloud(config: Dict[str, Any]):
    """Configure Google Cloud settings."""
    print_header("Google Cloud Configuration")
    
    # Project ID
    current_project = get_gcp_project_id()
    if current_project:
        use_current = input(f"Use current project '{current_project}'? (Y/n): ").lower()
        if use_current != 'n':
            config["GCP_PROJECT_ID"] = current_project
            config["GOOGLE_AI_PROJECT_ID"] = current_project
        else:
            project_id = input("Enter GCP project ID: ").strip()
            config["GCP_PROJECT_ID"] = project_id
            config["GOOGLE_AI_PROJECT_ID"] = project_id
    else:
        project_id = input("Enter GCP project ID: ").strip()
        config["GCP_PROJECT_ID"] = project_id
        config["GOOGLE_AI_PROJECT_ID"] = project_id
    
    # Service account
    print_info("\nService Account Configuration:")
    sa_path = input("Path to service account JSON [./service-account-key.json]: ").strip()
    config["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path or "./service-account-key.json"
    
    # Verify file exists
    if not os.path.exists(config["GOOGLE_APPLICATION_CREDENTIALS"]):
        print_warning(f"Service account file not found at {config['GOOGLE_APPLICATION_CREDENTIALS']}")
        print_info("You'll need to create it before deployment")
    
    # AI Configuration
    config["GOOGLE_AI_LOCATION"] = "us-central1"
    ai_model = input("Vertex AI model [gemini-1.5-flash]: ").strip() or "gemini-1.5-flash"
    config["GOOGLE_AI_MODEL"] = ai_model
    
    # Storage bucket
    bucket_name = input(f"GCS bucket name [{config['GCP_PROJECT_ID']}-roadtrip-assets]: ").strip()
    config["GCS_BUCKET_NAME"] = bucket_name or f"{config['GCP_PROJECT_ID']}-roadtrip-assets"
    
    print_success("Google Cloud configured")


def configure_database(config: Dict[str, Any]):
    """Configure database settings."""
    print_header("Database Configuration")
    
    print_info("Database connection options:")
    print("1. Cloud SQL (Production)")
    print("2. Local PostgreSQL (Development)")
    print("3. Cloud SQL with Proxy")
    
    db_choice = input("Select option (1-3) [1]: ").strip() or "1"
    
    if db_choice == "1":
        # Cloud SQL
        instance_name = input("Cloud SQL instance name [roadtrip-db]: ").strip() or "roadtrip-db"
        connection_name = f"{config['GCP_PROJECT_ID']}:us-central1:{instance_name}"
        
        db_user = input("Database user [postgres]: ").strip() or "postgres"
        db_password = getpass.getpass("Database password: ")
        db_name = input("Database name [roadtrip]: ").strip() or "roadtrip"
        
        config["DATABASE_URL"] = f"postgresql://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{connection_name}"
        config["CLOUD_SQL_CONNECTION_NAME"] = connection_name
        config["DB_USER"] = db_user
        config["DB_PASSWORD"] = db_password
        config["DB_NAME"] = db_name
        
    elif db_choice == "3":
        # Cloud SQL with proxy
        instance_name = input("Cloud SQL instance name [roadtrip-db]: ").strip() or "roadtrip-db"
        connection_name = f"{config['GCP_PROJECT_ID']}:us-central1:{instance_name}"
        
        db_user = input("Database user [postgres]: ").strip() or "postgres"
        db_password = getpass.getpass("Database password: ")
        db_name = input("Database name [roadtrip]: ").strip() or "roadtrip"
        
        config["DATABASE_URL"] = f"postgresql://{db_user}:{db_password}@localhost:5432/{db_name}"
        config["CLOUD_SQL_CONNECTION_NAME"] = connection_name
        config["DB_USER"] = db_user
        config["DB_PASSWORD"] = db_password
        config["DB_NAME"] = db_name
        
    else:
        # Local development
        config["DATABASE_URL"] = "postgresql://roadtrip:roadtrip123@localhost:5432/roadtrip"
        config["DB_USER"] = "roadtrip"
        config["DB_PASSWORD"] = "roadtrip123"
        config["DB_NAME"] = "roadtrip"
    
    print_success("Database configured")


def configure_redis(config: Dict[str, Any]):
    """Configure Redis settings."""
    print_header("Redis Configuration")
    
    print_info("Redis connection options:")
    print("1. Google Cloud Memorystore (Production)")
    print("2. Local Redis (Development)")
    print("3. Redis Cloud")
    
    redis_choice = input("Select option (1-3) [1]: ").strip() or "1"
    
    if redis_choice == "1":
        # Memorystore
        redis_host = input("Redis host IP: ").strip()
        redis_port = input("Redis port [6379]: ").strip() or "6379"
        config["REDIS_URL"] = f"redis://{redis_host}:{redis_port}"
        config["REDIS_HOST"] = redis_host
        config["REDIS_PORT"] = redis_port
        
    elif redis_choice == "3":
        # Redis Cloud
        redis_url = input("Redis Cloud URL: ").strip()
        config["REDIS_URL"] = redis_url
        
    else:
        # Local Redis
        config["REDIS_URL"] = "redis://localhost:6379"
        config["REDIS_HOST"] = "localhost"
        config["REDIS_PORT"] = "6379"
    
    print_success("Redis configured")


def configure_api_keys(config: Dict[str, Any]):
    """Configure third-party API keys."""
    print_header("API Keys Configuration")
    
    # Required APIs
    print_info("Required API Keys:")
    
    # Google Maps
    print("\n1. Google Maps API Key")
    print_info("Get it from: https://console.cloud.google.com/google/maps-apis/credentials")
    maps_key = input("Enter Google Maps API key: ").strip()
    if check_api_key_format(maps_key, "AIza"):
        config["GOOGLE_MAPS_API_KEY"] = maps_key
        print_success("Google Maps API key configured")
    else:
        print_warning("Invalid Google Maps API key format")
    
    # Ticketmaster
    print("\n2. Ticketmaster API Key")
    print_info("Get it from: https://developer.ticketmaster.com/")
    tm_key = input("Enter Ticketmaster API key: ").strip()
    if tm_key:
        config["TICKETMASTER_API_KEY"] = tm_key
        print_success("Ticketmaster API key configured")
    
    # OpenWeatherMap
    print("\n3. OpenWeatherMap API Key")
    print_info("Get it from: https://openweathermap.org/api")
    weather_key = input("Enter OpenWeatherMap API key: ").strip()
    if weather_key:
        config["OPENWEATHERMAP_API_KEY"] = weather_key
        print_success("OpenWeatherMap API key configured")
    
    # Recreation.gov
    print("\n4. Recreation.gov API Key")
    print_info("Get it from: https://www.recreation.gov/api")
    rec_key = input("Enter Recreation.gov API key: ").strip()
    if rec_key:
        config["RECREATION_GOV_API_KEY"] = rec_key
        print_success("Recreation.gov API key configured")
    
    # Optional APIs
    print_info("\nOptional API Keys (press Enter to skip):")
    
    # Spotify
    add_spotify = input("\nConfigure Spotify? (y/N): ").lower() == 'y'
    if add_spotify:
        config["SPOTIFY_CLIENT_ID"] = input("Spotify Client ID: ").strip()
        config["SPOTIFY_CLIENT_SECRET"] = input("Spotify Client Secret: ").strip()
    
    # Partner APIs (currently in mock mode)
    print_info("\nPartner APIs (will use mock mode if not configured):")
    config["CHARGEPOINT_API_KEY"] = input("ChargePoint API key (optional): ").strip() or ""
    config["VIATOR_API_KEY"] = input("Viator API key (optional): ").strip() or ""
    config["RESY_API_KEY"] = input("Resy API key (optional): ").strip() or ""
    config["OPENTABLE_API_KEY"] = input("OpenTable API key (optional): ").strip() or ""
    config["SHELL_RECHARGE_API_KEY"] = input("Shell Recharge API key (optional): ").strip() or ""


def configure_features(config: Dict[str, Any]):
    """Configure feature flags."""
    print_header("Feature Configuration")
    
    # Feature flags
    config["ENABLE_VOICE_SAFETY"] = "true"
    config["ENABLE_BOOKING_COMMISSION"] = "true"
    config["ENABLE_SEASONAL_PERSONALITIES"] = "true"
    config["ENABLE_AR_FEATURES"] = "true"
    config["ENABLE_SOCIAL_SHARING"] = "true"
    
    # Performance settings
    config["MAX_CONCURRENT_REQUESTS"] = "100"
    config["CACHE_TTL_SECONDS"] = "3600"
    config["AI_TIMEOUT_SECONDS"] = "30"
    
    # Safety settings
    config["MAX_DRIVING_SPEED_MPH"] = "75"
    config["VOICE_INTERACTION_COOLDOWN_MS"] = "2000"
    
    print_success("Features configured with production defaults")


def write_env_file(config: Dict[str, Any], filename: str = ".env.production"):
    """Write configuration to .env file."""
    print_header("Writing Configuration")
    
    # Group configurations
    groups = {
        "Core Configuration": [
            "ENVIRONMENT", "APP_VERSION", "SECRET_KEY", "JWT_SECRET_KEY",
            "APP_URL", "CORS_ORIGINS"
        ],
        "Database Configuration": [
            "DATABASE_URL", "DB_USER", "DB_PASSWORD", "DB_NAME",
            "CLOUD_SQL_CONNECTION_NAME"
        ],
        "Redis Configuration": [
            "REDIS_URL", "REDIS_HOST", "REDIS_PORT"
        ],
        "Google Cloud Configuration": [
            "GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT_ID",
            "GOOGLE_AI_PROJECT_ID", "GOOGLE_AI_LOCATION", "GOOGLE_AI_MODEL",
            "GCS_BUCKET_NAME"
        ],
        "API Keys": [
            "GOOGLE_MAPS_API_KEY", "TICKETMASTER_API_KEY", "OPENWEATHERMAP_API_KEY",
            "RECREATION_GOV_API_KEY", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET",
            "CHARGEPOINT_API_KEY", "VIATOR_API_KEY", "RESY_API_KEY",
            "OPENTABLE_API_KEY", "SHELL_RECHARGE_API_KEY"
        ],
        "Feature Flags": [
            "ENABLE_VOICE_SAFETY", "ENABLE_BOOKING_COMMISSION",
            "ENABLE_SEASONAL_PERSONALITIES", "ENABLE_AR_FEATURES",
            "ENABLE_SOCIAL_SHARING"
        ],
        "Performance Settings": [
            "MAX_CONCURRENT_REQUESTS", "CACHE_TTL_SECONDS", "AI_TIMEOUT_SECONDS",
            "MAX_DRIVING_SPEED_MPH", "VOICE_INTERACTION_COOLDOWN_MS"
        ]
    }
    
    # Additional production settings
    config["LOG_LEVEL"] = "INFO"
    config["DEBUG"] = "false"
    config["TEST_MODE"] = "live"
    
    # Write to file
    lines = ["# AI Road Trip Storyteller - Production Configuration",
             "# Generated by configure_production.py",
             "# DO NOT COMMIT THIS FILE TO VERSION CONTROL\n"]
    
    for group_name, keys in groups.items():
        lines.append(f"\n# {group_name}")
        for key in keys:
            if key in config and config[key]:
                value = config[key]
                # Don't quote boolean values
                if value in ["true", "false"]:
                    lines.append(f"{key}={value}")
                else:
                    lines.append(f"{key}={value}")
    
    # Additional settings
    lines.extend([
        "\n# Application Settings",
        f"LOG_LEVEL={config.get('LOG_LEVEL', 'INFO')}",
        f"DEBUG={config.get('DEBUG', 'false')}",
        f"TEST_MODE={config.get('TEST_MODE', 'live')}"
    ])
    
    # Write file
    with open(filename, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    
    print_success(f"Configuration written to {filename}")
    
    # Create backup
    backup_name = f"{filename}.backup"
    with open(backup_name, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print_info(f"Backup created at {backup_name}")


def create_secrets_in_gcp(config: Dict[str, Any]):
    """Create secrets in Google Secret Manager."""
    print_header("Creating Secrets in Secret Manager")
    
    create_secrets = input("Create secrets in Google Secret Manager? (y/N): ").lower() == 'y'
    if not create_secrets:
        return
    
    print_info("Creating secrets...")
    
    sensitive_keys = [
        "SECRET_KEY", "JWT_SECRET_KEY", "DB_PASSWORD",
        "GOOGLE_MAPS_API_KEY", "TICKETMASTER_API_KEY",
        "OPENWEATHERMAP_API_KEY", "RECREATION_GOV_API_KEY",
        "SPOTIFY_CLIENT_SECRET"
    ]
    
    project_id = config.get("GCP_PROJECT_ID")
    
    for key in sensitive_keys:
        if key in config and config[key]:
            secret_name = key.lower().replace('_', '-')
            try:
                # Create secret
                subprocess.run([
                    "gcloud", "secrets", "create", secret_name,
                    f"--data-file=-",
                    f"--project={project_id}"
                ], input=config[key].encode(), check=True)
                
                print_success(f"Created secret: {secret_name}")
            except subprocess.CalledProcessError:
                print_warning(f"Failed to create secret: {secret_name}")


def print_next_steps(config: Dict[str, Any]):
    """Print next steps after configuration."""
    print_header("Configuration Complete!")
    
    print("Next steps:\n")
    
    print(f"{Colors.BOLD}1. Verify Service Account{Colors.END}")
    print(f"   Ensure {config.get('GOOGLE_APPLICATION_CREDENTIALS')} exists")
    print(f"   {Colors.YELLOW}ls -la {config.get('GOOGLE_APPLICATION_CREDENTIALS')}{Colors.END}\n")
    
    print(f"{Colors.BOLD}2. Enable Google APIs{Colors.END}")
    print(f"   Go to: https://console.cloud.google.com/apis/library?project={config.get('GCP_PROJECT_ID')}")
    print("   Enable: Maps, Places, Geocoding, Directions, Text-to-Speech, Speech-to-Text\n")
    
    print(f"{Colors.BOLD}3. Run Database Migrations{Colors.END}")
    print(f"   {Colors.YELLOW}alembic upgrade head{Colors.END}\n")
    
    print(f"{Colors.BOLD}4. Deploy Application{Colors.END}")
    print(f"   {Colors.YELLOW}./quick_deploy.sh{Colors.END}\n")
    
    print(f"{Colors.BOLD}5. Test Deployment{Colors.END}")
    print(f"   {Colors.YELLOW}curl https://your-domain.com/health/detailed{Colors.END}\n")
    
    if not all([config.get(k) for k in ["GOOGLE_MAPS_API_KEY", "TICKETMASTER_API_KEY"]]):
        print(f"{Colors.WARNING}⚠ Missing Required API Keys:{Colors.END}")
        if not config.get("GOOGLE_MAPS_API_KEY"):
            print("  - Google Maps API Key")
        if not config.get("TICKETMASTER_API_KEY"):
            print("  - Ticketmaster API Key")
        print()


def main():
    """Main configuration flow."""
    print_header("AI Road Trip Storyteller - Production Configuration")
    
    config = {}
    
    try:
        # Run configuration steps
        configure_core_settings(config)
        configure_google_cloud(config)
        configure_database(config)
        configure_redis(config)
        configure_api_keys(config)
        configure_features(config)
        
        # Write configuration
        write_env_file(config)
        
        # Optionally create secrets in GCP
        create_secrets_in_gcp(config)
        
        # Print next steps
        print_next_steps(config)
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Configuration complete!{Colors.END}")
        print(f"Production environment file created: .env.production")
        print(f"To use: {Colors.YELLOW}cp .env.production .env{Colors.END}")
        
    except KeyboardInterrupt:
        print_error("\n\nConfiguration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nConfiguration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()