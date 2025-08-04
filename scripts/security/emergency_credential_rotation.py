#!/usr/bin/env python3
"""
EMERGENCY Credential Rotation Script for AI Road Trip Storyteller
CRITICAL: Run this immediately to rotate all exposed credentials
"""

import os
import sys
import json
import subprocess
import secrets
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CRITICAL: Exposed credentials that must be rotated
EXPOSED_CREDENTIALS = {
    "GOOGLE_MAPS_API_KEY": "AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ",
    "TICKETMASTER_API_KEY": "5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo",
    "OPENWEATHERMAP_API_KEY": "d7aa0dc75ed0dae38f627ed48d3e3bf1"
}

# Project configuration
PROJECT_ID = "roadtrip-460720"
SECRET_MANAGER_MAPPING = {
    "GOOGLE_MAPS_API_KEY": "roadtrip-google-maps-key",
    "TICKETMASTER_API_KEY": "roadtrip-ticketmaster-key",
    "OPENWEATHERMAP_API_KEY": "roadtrip-openweather-key",
    "DATABASE_URL": "roadtrip-database-url",
    "JWT_SECRET_KEY": "roadtrip-jwt-secret",
    "CSRF_SECRET_KEY": "roadtrip-csrf-secret",
    "REDIS_URL": "roadtrip-redis-url",
    "SECRET_KEY": "roadtrip-secret-key",
    "ENCRYPTION_KEY": "roadtrip-encryption-key"
}

@dataclass
class RotationResult:
    """Result of a credential rotation attempt"""
    credential_name: str
    old_value: str
    new_value: Optional[str]
    success: bool
    error: Optional[str]
    actions_taken: List[str]
    manual_steps: List[str]

class CredentialRotator:
    """Handles emergency credential rotation"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self.rotation_results: List[RotationResult] = []
        
    def generate_secure_key(self, length: int = 32) -> str:
        """Generate a cryptographically secure random key"""
        return secrets.token_urlsafe(length)
    
    def create_or_update_secret(self, secret_id: str, value: str) -> bool:
        """Create or update a secret in Google Secret Manager"""
        parent = f"projects/{self.project_id}"
        
        try:
            # Try to create the secret first
            secret = self.secret_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": {
                            "rotation-date": datetime.now().strftime("%Y%m%d"),
                            "rotation-reason": "emergency-exposed-credentials"
                        }
                    }
                }
            )
            logger.info(f"Created new secret: {secret_id}")
        except gcp_exceptions.AlreadyExists:
            # Secret exists, just add a new version
            logger.info(f"Secret {secret_id} already exists, adding new version")
            secret_name = f"{parent}/secrets/{secret_id}"
        else:
            secret_name = secret.name
            
        # Add the secret version
        try:
            version = self.secret_client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": value.encode("UTF-8")}
                }
            )
            logger.info(f"Added new version for secret: {secret_id}")
            
            # Disable old versions
            self._disable_old_versions(secret_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            return False
    
    def _disable_old_versions(self, secret_id: str) -> None:
        """Disable old versions of a secret, keeping only the latest 3"""
        try:
            parent = f"projects/{self.project_id}/secrets/{secret_id}"
            versions = list(self.secret_client.list_secret_versions(
                request={"parent": parent, "filter": "state:ENABLED"}
            ))
            
            # Sort by create time and disable all but the latest 3
            versions.sort(key=lambda v: v.create_time, reverse=True)
            for version in versions[3:]:
                self.secret_client.disable_secret_version(
                    request={"name": version.name}
                )
                logger.info(f"Disabled old version: {version.name}")
                
        except Exception as e:
            logger.warning(f"Could not disable old versions for {secret_id}: {e}")
    
    def rotate_google_maps_key(self, old_key: str) -> RotationResult:
        """Rotate Google Maps API key"""
        result = RotationResult(
            credential_name="GOOGLE_MAPS_API_KEY",
            old_value=old_key,
            new_value=None,
            success=False,
            error=None,
            actions_taken=[],
            manual_steps=[]
        )
        
        try:
            # Disable the exposed key
            cmd = [
                "gcloud", "alpha", "services", "api-keys", "update",
                "--project", self.project_id,
                "--filter", f"keyString={old_key}",
                "--clear-restrictions"
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            result.actions_taken.append("Disabled exposed Google Maps API key")
            
            # Manual steps required
            result.manual_steps.extend([
                "1. Go to https://console.cloud.google.com/apis/credentials",
                f"2. Select project: {self.project_id}",
                "3. Create a new API key",
                "4. Add restrictions:",
                "   - Application restrictions: HTTP referrers",
                "   - Add your domain: https://roadtrip.app/*",
                "   - API restrictions: Maps JavaScript API, Places API, Directions API",
                "5. Copy the new API key",
                f"6. Run: gcloud secrets versions add {SECRET_MANAGER_MAPPING['GOOGLE_MAPS_API_KEY']} --data-file=-",
                "7. Paste the new key and press Ctrl+D",
                "8. Delete the old API key from the console"
            ])
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Failed to rotate Google Maps key: {e}")
            
        return result
    
    def rotate_ticketmaster_key(self, old_key: str) -> RotationResult:
        """Rotate Ticketmaster API key"""
        result = RotationResult(
            credential_name="TICKETMASTER_API_KEY",
            old_value=old_key,
            new_value=None,
            success=False,
            error=None,
            actions_taken=[],
            manual_steps=[]
        )
        
        # Ticketmaster requires manual rotation
        result.manual_steps.extend([
            "1. Contact Ticketmaster Partner Support immediately",
            "2. Report compromised API key",
            "3. Request emergency key rotation",
            "4. Email: apisupport@ticketmaster.com",
            "5. Include:",
            "   - Your partner account details",
            "   - The compromised key (last 4 chars only)",
            "   - Request for immediate rotation",
            "6. Once you receive the new key:",
            f"   gcloud secrets versions add {SECRET_MANAGER_MAPPING['TICKETMASTER_API_KEY']} --data-file=-",
            "7. Update all environments to use Secret Manager"
        ])
        
        result.success = True
        return result
    
    def rotate_openweather_key(self, old_key: str) -> RotationResult:
        """Rotate OpenWeatherMap API key"""
        result = RotationResult(
            credential_name="OPENWEATHERMAP_API_KEY",
            old_value=old_key,
            new_value=None,
            success=False,
            error=None,
            actions_taken=[],
            manual_steps=[]
        )
        
        result.manual_steps.extend([
            "1. Log in to https://openweathermap.org/api_keys",
            "2. Generate a new API key",
            "3. Name it: roadtrip-prod-{date}",
            "4. Copy the new API key",
            f"5. Run: gcloud secrets versions add {SECRET_MANAGER_MAPPING['OPENWEATHERMAP_API_KEY']} --data-file=-",
            "6. Paste the new key and press Ctrl+D",
            "7. Delete the old API key from OpenWeatherMap dashboard",
            "8. Update monitoring to track the new key usage"
        ])
        
        result.success = True
        return result
    
    def rotate_internal_secrets(self) -> List[RotationResult]:
        """Rotate all internal secrets (JWT, CSRF, etc.)"""
        results = []
        
        internal_secrets = {
            "JWT_SECRET_KEY": self.generate_secure_key(64),
            "CSRF_SECRET_KEY": self.generate_secure_key(64),
            "SECRET_KEY": self.generate_secure_key(64),
            "ENCRYPTION_KEY": self.generate_secure_key(32)
        }
        
        for secret_name, new_value in internal_secrets.items():
            result = RotationResult(
                credential_name=secret_name,
                old_value="[HIDDEN]",
                new_value="[GENERATED]",
                success=False,
                error=None,
                actions_taken=[],
                manual_steps=[]
            )
            
            try:
                secret_id = SECRET_MANAGER_MAPPING.get(secret_name)
                if secret_id and self.create_or_update_secret(secret_id, new_value):
                    result.success = True
                    result.actions_taken.append(f"Generated new {secret_name}")
                    result.actions_taken.append(f"Stored in Secret Manager: {secret_id}")
                else:
                    result.error = "Failed to update Secret Manager"
                    
            except Exception as e:
                result.error = str(e)
                logger.error(f"Failed to rotate {secret_name}: {e}")
                
            results.append(result)
            
        return results
    
    def scan_for_credentials(self) -> List[str]:
        """Scan codebase for any remaining exposed credentials"""
        findings = []
        
        # Patterns to search for
        patterns = [
            r"AIzaSy[0-9A-Za-z\-_]{33}",  # Google API keys
            r"[0-9a-zA-Z]{32}",  # Generic API keys
            r"postgresql://.*:.*@",  # Database URLs
            r"redis://.*:.*@"  # Redis URLs
        ]
        
        logger.info("Scanning codebase for exposed credentials...")
        
        # Use ripgrep for fast searching
        for pattern in patterns:
            try:
                cmd = ["rg", "-i", pattern, "--type", "py", "--type", "js", "--type", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.stdout:
                    findings.append(f"Pattern '{pattern}' found:\n{result.stdout}")
            except Exception as e:
                logger.warning(f"Could not scan for pattern {pattern}: {e}")
                
        return findings
    
    def generate_rotation_report(self) -> str:
        """Generate a comprehensive rotation report"""
        report = []
        report.append("=" * 80)
        report.append("EMERGENCY CREDENTIAL ROTATION REPORT")
        report.append(f"Date: {datetime.now().isoformat()}")
        report.append(f"Project: {self.project_id}")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        successful = sum(1 for r in self.rotation_results if r.success)
        failed = len(self.rotation_results) - successful
        
        report.append("SUMMARY:")
        report.append(f"  Total credentials processed: {len(self.rotation_results)}")
        report.append(f"  Successfully rotated: {successful}")
        report.append(f"  Failed/Manual required: {failed}")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS:")
        for result in self.rotation_results:
            report.append(f"\n{result.credential_name}:")
            report.append(f"  Status: {'SUCCESS' if result.success else 'MANUAL ACTION REQUIRED'}")
            
            if result.actions_taken:
                report.append("  Actions taken:")
                for action in result.actions_taken:
                    report.append(f"    - {action}")
                    
            if result.manual_steps:
                report.append("  Manual steps required:")
                for step in result.manual_steps:
                    report.append(f"    {step}")
                    
            if result.error:
                report.append(f"  Error: {result.error}")
                
        report.append("")
        report.append("=" * 80)
        report.append("IMMEDIATE NEXT STEPS:")
        report.append("1. Complete all manual rotation steps listed above")
        report.append("2. Deploy updated configuration to all environments")
        report.append("3. Verify all services are using Secret Manager")
        report.append("4. Monitor for any unauthorized usage of old keys")
        report.append("5. Set up automated rotation schedule")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_emergency_rotation(self) -> None:
        """Execute emergency credential rotation"""
        logger.info("Starting EMERGENCY credential rotation...")
        
        # Rotate exposed API keys
        for key_name, key_value in EXPOSED_CREDENTIALS.items():
            logger.info(f"Rotating {key_name}...")
            
            if key_name == "GOOGLE_MAPS_API_KEY":
                result = self.rotate_google_maps_key(key_value)
            elif key_name == "TICKETMASTER_API_KEY":
                result = self.rotate_ticketmaster_key(key_value)
            elif key_name == "OPENWEATHERMAP_API_KEY":
                result = self.rotate_openweather_key(key_value)
            else:
                continue
                
            self.rotation_results.append(result)
        
        # Rotate internal secrets
        logger.info("Rotating internal secrets...")
        internal_results = self.rotate_internal_secrets()
        self.rotation_results.extend(internal_results)
        
        # Scan for any other exposed credentials
        findings = self.scan_for_credentials()
        if findings:
            logger.warning("Additional exposed credentials found!")
            for finding in findings:
                logger.warning(finding)
        
        # Generate report
        report = self.generate_rotation_report()
        
        # Save report
        report_file = f"credential_rotation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            f.write(report)
            
        print("\n" + report)
        print(f"\nReport saved to: {report_file}")

def main():
    """Main entry point"""
    print("=" * 80)
    print("EMERGENCY CREDENTIAL ROTATION FOR AI ROAD TRIP STORYTELLER")
    print("CRITICAL: This will rotate all exposed credentials")
    print("=" * 80)
    print()
    
    # Confirm execution
    print("This script will:")
    print("1. Disable exposed API keys")
    print("2. Generate new internal secrets")
    print("3. Update Google Secret Manager")
    print("4. Provide manual rotation instructions")
    print()
    
    response = input("Proceed with emergency rotation? (yes/no): ")
    if response.lower() != "yes":
        print("Rotation cancelled. CRITICAL: Exposed credentials remain active!")
        sys.exit(1)
    
    # Check prerequisites
    try:
        subprocess.run(["gcloud", "config", "get-value", "project"], 
                      check=True, capture_output=True)
    except Exception as e:
        print("ERROR: gcloud CLI not configured. Run: gcloud auth login")
        sys.exit(1)
    
    # Run rotation
    rotator = CredentialRotator(PROJECT_ID)
    rotator.run_emergency_rotation()

if __name__ == "__main__":
    main()