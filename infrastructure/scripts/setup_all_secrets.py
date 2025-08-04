#!/usr/bin/env python3
"""
Comprehensive secret setup script for RoadTrip application.
This script creates all required secrets in Google Secret Manager with proper mappings.
"""

import os
import sys
import json
import secrets
import subprocess
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

# Add color support for Windows
if sys.platform == 'win32':
    os.system('color')

# Color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class SecretPriority(Enum):
    CRITICAL = "critical"  # App won't work without these
    REQUIRED = "required"  # Core features disabled without these
    OPTIONAL = "optional"  # Enhanced features only

@dataclass
class SecretConfig:
    """Configuration for a secret."""
    secret_id: str
    env_vars: List[str]  # All environment variable names that map to this secret
    description: str
    priority: SecretPriority
    placeholder_value: Optional[str] = None
    instructions: Optional[str] = None
    cost: Optional[str] = None
    
class SecretManager:
    """Manages Google Secret Manager operations."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.service_account = f"roadtrip-mvp-sa@{project_id}.iam.gserviceaccount.com"
        
    def run_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def secret_exists(self, secret_id: str) -> bool:
        """Check if a secret exists."""
        cmd = ['gcloud', 'secrets', 'describe', secret_id, f'--project={self.project_id}']
        success, _ = self.run_command(cmd)
        return success
    
    def create_or_update_secret(self, secret_id: str, value: str) -> bool:
        """Create or update a secret."""
        if self.secret_exists(secret_id):
            # Update existing secret
            cmd = ['gcloud', 'secrets', 'versions', 'add', secret_id, 
                   f'--project={self.project_id}', '--data-file=-']
        else:
            # Create new secret
            create_cmd = ['gcloud', 'secrets', 'create', secret_id,
                          f'--project={self.project_id}',
                          '--replication-policy=automatic', '--data-file=-']
            
            # Run create command with value piped in
            proc = subprocess.Popen(create_cmd, stdin=subprocess.PIPE, 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(input=value)
            
            if proc.returncode != 0:
                print(f"{Colors.RED}Failed to create secret: {stderr}{Colors.RESET}")
                return False
            
            # Add labels
            label_cmd = ['gcloud', 'secrets', 'update', secret_id,
                        f'--project={self.project_id}',
                        '--update-labels=environment=production,component=backend']
            self.run_command(label_cmd)
            
            # Grant access to service account
            self.grant_secret_access(secret_id)
            return True
        
        # For updates, pipe the value
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=value)
        
        return proc.returncode == 0
    
    def grant_secret_access(self, secret_id: str) -> bool:
        """Grant service account access to a secret."""
        cmd = ['gcloud', 'secrets', 'add-iam-policy-binding', secret_id,
               f'--member=serviceAccount:{self.service_account}',
               '--role=roles/secretmanager.secretAccessor',
               f'--project={self.project_id}']
        success, _ = self.run_command(cmd)
        return success
    
    def get_secret_value(self, secret_id: str) -> Optional[str]:
        """Get the current value of a secret."""
        cmd = ['gcloud', 'secrets', 'versions', 'access', 'latest',
               f'--secret={secret_id}', f'--project={self.project_id}']
        success, output = self.run_command(cmd)
        return output.strip() if success else None

def get_all_secrets() -> Dict[str, SecretConfig]:
    """Define all secrets needed by the application."""
    return {
        # Core application secrets
        "roadtrip-secret-key": SecretConfig(
            secret_id="roadtrip-secret-key",
            env_vars=["SECRET_KEY"],
            description="Application secret key for session management",
            priority=SecretPriority.CRITICAL,
            placeholder_value=secrets.token_hex(32)
        ),
        
        "roadtrip-jwt-secret": SecretConfig(
            secret_id="roadtrip-jwt-secret",
            env_vars=["JWT_SECRET_KEY"],
            description="JWT token signing key",
            priority=SecretPriority.CRITICAL,
            placeholder_value=secrets.token_hex(64)
        ),
        
        "roadtrip-csrf-secret": SecretConfig(
            secret_id="roadtrip-csrf-secret",
            env_vars=["CSRF_SECRET_KEY"],
            description="CSRF protection secret",
            priority=SecretPriority.CRITICAL,
            placeholder_value=secrets.token_hex(32)
        ),
        
        "encryption-key": SecretConfig(
            secret_id="encryption-key",
            env_vars=["ENCRYPTION_KEY"],
            description="Data encryption key",
            priority=SecretPriority.CRITICAL,
            placeholder_value=secrets.token_hex(32)
        ),
        
        # Infrastructure
        "roadtrip-database-url": SecretConfig(
            secret_id="roadtrip-database-url",
            env_vars=["DATABASE_URL"],
            description="PostgreSQL connection string",
            priority=SecretPriority.CRITICAL,
            placeholder_value="postgresql://user:password@localhost/roadtrip",
            instructions="Update with your Cloud SQL connection string"
        ),
        
        "roadtrip-redis-url": SecretConfig(
            secret_id="roadtrip-redis-url",
            env_vars=["REDIS_URL"],
            description="Redis connection string",
            priority=SecretPriority.CRITICAL,
            placeholder_value="redis://localhost:6379/0",
            instructions="Update with your Redis instance URL"
        ),
        
        "roadtrip-gcs-bucket": SecretConfig(
            secret_id="roadtrip-gcs-bucket",
            env_vars=["GCS_BUCKET_NAME"],
            description="Google Cloud Storage bucket name",
            priority=SecretPriority.REQUIRED,
            placeholder_value="roadtrip-user-photos",
            instructions="Create a GCS bucket and update this value"
        ),
        
        # Google Services
        "roadtrip-google-maps-key": SecretConfig(
            secret_id="roadtrip-google-maps-key",
            env_vars=["GOOGLE_MAPS_API_KEY"],
            description="Google Maps API key for navigation",
            priority=SecretPriority.CRITICAL,
            placeholder_value="PLACEHOLDER_GOOGLE_MAPS_KEY",
            instructions="Get from Google Cloud Console - Enable Maps, Places, Directions APIs",
            cost="~$200/month free credit, then usage-based"
        ),
        
        # Weather
        "roadtrip-openweather-key": SecretConfig(
            secret_id="roadtrip-openweather-key",
            env_vars=["OPENWEATHERMAP_API_KEY", "OPENWEATHER_API_KEY"],
            description="OpenWeatherMap API key",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_OPENWEATHER_KEY",
            instructions="Sign up at openweathermap.org for free API key",
            cost="Free tier: 1,000 calls/day"
        ),
        
        # Event Booking
        "roadtrip-ticketmaster-key": SecretConfig(
            secret_id="roadtrip-ticketmaster-key",
            env_vars=["TICKETMASTER_API_KEY"],
            description="Ticketmaster API key for events",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_TICKETMASTER_KEY",
            instructions="Register at developer.ticketmaster.com",
            cost="Free for developers"
        ),
        
        "roadtrip-ticketmaster-secret": SecretConfig(
            secret_id="roadtrip-ticketmaster-secret",
            env_vars=["TICKETMASTER_API_SECRET"],
            description="Ticketmaster API secret",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_TICKETMASTER_SECRET"
        ),
        
        # Camping
        "roadtrip-recreation-key": SecretConfig(
            secret_id="roadtrip-recreation-key",
            env_vars=["RECREATION_GOV_API_KEY"],
            description="Recreation.gov API key",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_RECREATION_KEY",
            instructions="Apply at recreation.gov/api (1-2 week approval)",
            cost="Free"
        ),
        
        "roadtrip-recreation-secret": SecretConfig(
            secret_id="roadtrip-recreation-secret",
            env_vars=["RECREATION_GOV_API_SECRET"],
            description="Recreation.gov API secret",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_RECREATION_SECRET"
        ),
        
        "roadtrip-recreation-account": SecretConfig(
            secret_id="roadtrip-recreation-account",
            env_vars=["RECREATION_GOV_ACCOUNT_ID"],
            description="Recreation.gov account ID",
            priority=SecretPriority.REQUIRED,
            placeholder_value="PLACEHOLDER_RECREATION_ACCOUNT"
        ),
        
        # Music
        "roadtrip-spotify-id": SecretConfig(
            secret_id="roadtrip-spotify-id",
            env_vars=["SPOTIFY_CLIENT_ID"],
            description="Spotify client ID",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_SPOTIFY_ID",
            instructions="Create app at developer.spotify.com",
            cost="Free"
        ),
        
        "roadtrip-spotify-secret": SecretConfig(
            secret_id="roadtrip-spotify-secret",
            env_vars=["SPOTIFY_CLIENT_SECRET"],
            description="Spotify client secret",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_SPOTIFY_SECRET"
        ),
        
        # Restaurant Booking
        "roadtrip-opentable-key": SecretConfig(
            secret_id="roadtrip-opentable-key",
            env_vars=["OPENTABLE_API_KEY"],
            description="OpenTable API key",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_OPENTABLE_KEY",
            instructions="Contact OpenTable for partner access",
            cost="Partner program required"
        ),
        
        "roadtrip-opentable-id": SecretConfig(
            secret_id="roadtrip-opentable-id",
            env_vars=["OPENTABLE_CLIENT_ID"],
            description="OpenTable client ID",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_OPENTABLE_ID"
        ),
        
        "roadtrip-opentable-secret": SecretConfig(
            secret_id="roadtrip-opentable-secret",
            env_vars=["OPENTABLE_CLIENT_SECRET"],
            description="OpenTable client secret",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_OPENTABLE_SECRET"
        ),
        
        # Tours & Activities
        "roadtrip-viator-key": SecretConfig(
            secret_id="roadtrip-viator-key",
            env_vars=["VIATOR_API_KEY"],
            description="Viator API key for tours",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_VIATOR_KEY",
            instructions="Apply at viatorapi.viator.com",
            cost="Commission-based"
        ),
        
        # Flight Tracking
        "roadtrip-flight-tracking-key": SecretConfig(
            secret_id="roadtrip-flight-tracking-key",
            env_vars=["FLIGHT_TRACKING_API_KEY"],
            description="Generic flight tracking API",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_FLIGHT_KEY"
        ),
        
        # Airport Services
        "roadtrip-priority-pass-key": SecretConfig(
            secret_id="roadtrip-priority-pass-key",
            env_vars=["PRIORITY_PASS_API_KEY"],
            description="Priority Pass lounge access",
            priority=SecretPriority.OPTIONAL,
            placeholder_value="PLACEHOLDER_PRIORITY_PASS_KEY"
        ),
        
        # 2FA
        "roadtrip-two-factor-secret": SecretConfig(
            secret_id="roadtrip-two-factor-secret",
            env_vars=["TWO_FACTOR_SECRET"],
            description="2FA authentication secret",
            priority=SecretPriority.OPTIONAL,
            placeholder_value=secrets.token_hex(32)
        ),
    }

def main():
    """Main setup function."""
    print(f"{Colors.BLUE}{Colors.BOLD}RoadTrip Secret Manager Setup{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")
    
    # Get project ID
    project_id = os.environ.get('PROJECT_ID', 'roadtrip-460720')
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    
    print(f"Project ID: {Colors.CYAN}{project_id}{Colors.RESET}")
    print(f"Service Account: {Colors.CYAN}roadtrip-mvp-sa@{project_id}.iam.gserviceaccount.com{Colors.RESET}\n")
    
    # Initialize secret manager
    sm = SecretManager(project_id)
    
    # Get all secret configurations
    all_secrets = get_all_secrets()
    
    # Statistics
    stats = {
        SecretPriority.CRITICAL: {'total': 0, 'configured': 0, 'placeholder': 0},
        SecretPriority.REQUIRED: {'total': 0, 'configured': 0, 'placeholder': 0},
        SecretPriority.OPTIONAL: {'total': 0, 'configured': 0, 'placeholder': 0},
    }
    
    # Process each secret
    for secret_id, config in all_secrets.items():
        stats[config.priority]['total'] += 1
        
        print(f"\n{Colors.YELLOW}Setting up: {secret_id}{Colors.RESET}")
        print(f"  Priority: {config.priority.value}")
        print(f"  Maps to: {', '.join(config.env_vars)}")
        print(f"  Description: {config.description}")
        
        # Check current value
        current_value = sm.get_secret_value(secret_id)
        
        if current_value:
            if current_value.startswith('PLACEHOLDER_'):
                print(f"  Status: {Colors.YELLOW}Placeholder configured{Colors.RESET}")
                stats[config.priority]['placeholder'] += 1
            else:
                print(f"  Status: {Colors.GREEN}Already configured{Colors.RESET}")
                stats[config.priority]['configured'] += 1
                continue
        else:
            print(f"  Status: {Colors.RED}Not found{Colors.RESET}")
        
        # Create or update with placeholder
        if config.placeholder_value:
            if sm.create_or_update_secret(secret_id, config.placeholder_value):
                print(f"  {Colors.GREEN}✓ Created with placeholder value{Colors.RESET}")
                stats[config.priority]['placeholder'] += 1
            else:
                print(f"  {Colors.RED}✗ Failed to create secret{Colors.RESET}")
        
        # Show additional info
        if config.instructions:
            print(f"  {Colors.CYAN}Instructions: {config.instructions}{Colors.RESET}")
        if config.cost:
            print(f"  {Colors.MAGENTA}Cost: {config.cost}{Colors.RESET}")
    
    # Generate CloudBuild secret mapping
    print(f"\n{Colors.BLUE}{Colors.BOLD}CloudBuild Configuration{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")
    
    cloudbuild_secrets = []
    for config in all_secrets.values():
        # Use the first env var name for CloudBuild
        env_var = config.env_vars[0]
        cloudbuild_secrets.append(f"{env_var}={config.secret_id}:latest")
    
    print("Add this to your cloudbuild.yaml under '--set-secrets':")
    print("```yaml")
    print("      - '--set-secrets'")
    print("      - |")
    
    # Format in chunks for readability
    for i in range(0, len(cloudbuild_secrets), 3):
        chunk = cloudbuild_secrets[i:i+3]
        line = "        " + ",".join(chunk)
        if i + 3 < len(cloudbuild_secrets):
            line += ","
        print(line)
    print("```")
    
    # Summary
    print(f"\n{Colors.BLUE}{Colors.BOLD}Summary{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")
    
    for priority in SecretPriority:
        s = stats[priority]
        total = s['total']
        configured = s['configured']
        placeholder = s['placeholder']
        missing = total - configured - placeholder
        
        print(f"{priority.value.capitalize()} Secrets:")
        print(f"  Total: {total}")
        print(f"  {Colors.GREEN}Configured: {configured}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Placeholder: {placeholder}{Colors.RESET}")
        if missing > 0:
            print(f"  {Colors.RED}Missing: {missing}{Colors.RESET}")
        print()
    
    # Next steps
    print(f"{Colors.BLUE}{Colors.BOLD}Next Steps{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.RESET}\n")
    
    print(f"{Colors.RED}1. CRITICAL - Update these immediately:{Colors.RESET}")
    print("   - roadtrip-database-url: Your Cloud SQL connection string")
    print("   - roadtrip-redis-url: Your Redis instance URL")
    print("   - roadtrip-google-maps-key: Get from Google Cloud Console\n")
    
    print(f"{Colors.YELLOW}2. REQUIRED - Core features need these:{Colors.RESET}")
    print("   - roadtrip-openweather-key: Free at openweathermap.org")
    print("   - roadtrip-ticketmaster-key: Free at developer.ticketmaster.com")
    print("   - roadtrip-recreation-key: Apply at recreation.gov/api\n")
    
    print(f"{Colors.GREEN}3. OPTIONAL - Enhanced features:{Colors.RESET}")
    print("   - Spotify: Music integration")
    print("   - Viator: Tour booking")
    print("   - Others: See API_CREDENTIALS.md\n")
    
    print("To update a secret:")
    print(f"{Colors.CYAN}echo -n 'your-value' | gcloud secrets versions add SECRET_ID --data-file=- --project={project_id}{Colors.RESET}")

if __name__ == "__main__":
    main()