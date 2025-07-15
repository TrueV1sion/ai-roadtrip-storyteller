#!/usr/bin/env python3
"""
Update Secret Manager Integration for Production Deployment
Ensures all configuration properly uses Secret Manager instead of environment variables
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# Files that need to be updated
CONFIG_FILES = [
    "backend/app/core/config.py",
    "backend/app/core/secret_manager.py",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    ".env.example",
    "infrastructure/terraform/main.tf",
    "infrastructure/k8s/deployment-api.yaml"
]

# Patterns to find and replace
REPLACEMENTS = {
    # Replace hardcoded API keys
    r'AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ': 'secret_manager.get_secret("roadtrip-google-maps-key")',
    r'5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo': 'secret_manager.get_secret("roadtrip-ticketmaster-key")',
    r'd7aa0dc75ed0dae38f627ed48d3e3bf1': 'secret_manager.get_secret("roadtrip-openweather-key")',
    
    # Update environment variable references
    r'os\.getenv\("GOOGLE_MAPS_API_KEY"\)': 'secret_manager.get_secret("roadtrip-google-maps-key")',
    r'os\.getenv\("TICKETMASTER_API_KEY"\)': 'secret_manager.get_secret("roadtrip-ticketmaster-key")',
    r'os\.getenv\("OPENWEATHERMAP_API_KEY"\)': 'secret_manager.get_secret("roadtrip-openweather-key")',
    
    # Update config references
    r'settings\.GOOGLE_MAPS_API_KEY': 'secret_manager.get_secret("roadtrip-google-maps-key")',
    r'settings\.TICKETMASTER_API_KEY': 'secret_manager.get_secret("roadtrip-ticketmaster-key")',
    r'settings\.OPENWEATHERMAP_API_KEY': 'secret_manager.get_secret("roadtrip-openweather-key")'
}

def scan_file_for_credentials(file_path: Path) -> List[Tuple[int, str]]:
    """Scan a file for exposed credentials"""
    findings = []
    
    # Patterns that indicate exposed credentials
    credential_patterns = [
        (r'AIzaSy[0-9A-Za-z\-_]{33}', 'Google API Key'),
        (r'["\']?\w{32}["\']?', 'Potential API Key'),
        (r'postgresql://[^:]+:[^@]+@', 'Database URL with password'),
        (r'redis://[^:]+:[^@]+@', 'Redis URL with password'),
        (r'["\']?[A-Za-z0-9+/]{40,}={0,2}["\']?', 'Potential Base64 encoded secret')
    ]
    
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                for pattern, desc in credential_patterns:
                    if re.search(pattern, line):
                        findings.append((line_num, f"{desc}: {line.strip()}"))
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
    
    return findings

def update_file_for_secret_manager(file_path: Path) -> bool:
    """Update a file to use Secret Manager instead of hardcoded values"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all replacements
        for pattern, replacement in REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def create_secret_manager_wrapper():
    """Create an enhanced secret manager wrapper"""
    wrapper_content = '''"""
Enhanced Secret Manager wrapper with credential rotation support
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache

from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

logger = logging.getLogger(__name__)

class SecretRotationManager:
    """Manages secret rotation and monitoring"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
        self._rotation_callbacks: Dict[str, List[callable]] = {}
    
    def check_rotation_needed(self, secret_id: str, max_age_days: int = 90) -> bool:
        """Check if a secret needs rotation based on age"""
        try:
            parent = f"projects/{self.project_id}/secrets/{secret_id}"
            secret = self.client.get_secret(request={"name": parent})
            
            # Check rotation metadata
            if "last-rotation" in secret.labels:
                last_rotation = datetime.fromtimestamp(
                    int(secret.labels["last-rotation"])
                )
                age = datetime.now() - last_rotation
                return age.days >= max_age_days
            
            return True  # No rotation metadata, assume it needs rotation
            
        except Exception as e:
            logger.error(f"Error checking rotation for {secret_id}: {e}")
            return False
    
    def register_rotation_callback(self, secret_id: str, callback: callable):
        """Register a callback to be called when a secret is rotated"""
        if secret_id not in self._rotation_callbacks:
            self._rotation_callbacks[secret_id] = []
        self._rotation_callbacks[secret_id].append(callback)
    
    def notify_rotation(self, secret_id: str, new_version: str):
        """Notify registered callbacks about secret rotation"""
        if secret_id in self._rotation_callbacks:
            for callback in self._rotation_callbacks[secret_id]:
                try:
                    callback(secret_id, new_version)
                except Exception as e:
                    logger.error(f"Error in rotation callback for {secret_id}: {e}")

class EnhancedSecretManager:
    """Enhanced Secret Manager with monitoring and rotation support"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "roadtrip-460720")
        self.client = None
        self._cache: Dict[str, Any] = {}
        self._access_log: List[Dict[str, Any]] = []
        self.rotation_manager = SecretRotationManager(self.project_id)
        
        # Initialize client
        try:
            self.client = secretmanager.SecretManagerServiceClient()
            logger.info("Secret Manager client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {e}")
    
    @lru_cache(maxsize=128)
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """Get a secret with monitoring and caching"""
        # Log access
        self._log_access(secret_id)
        
        # Check cache first
        cache_key = f"{secret_id}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Development fallback
        if not self.client or os.getenv("ENVIRONMENT") == "development":
            # Try environment variable fallback
            env_name = secret_id.upper().replace("-", "_")
            return os.getenv(env_name)
        
        try:
            # Build the resource name
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            
            # Access the secret
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Cache the result
            self._cache[cache_key] = secret_value
            
            # Check if rotation is needed
            if self.rotation_manager.check_rotation_needed(secret_id):
                logger.warning(f"Secret {secret_id} needs rotation")
            
            return secret_value
            
        except gcp_exceptions.NotFound:
            logger.error(f"Secret {secret_id} not found in Secret Manager")
            # Try environment variable fallback
            env_name = secret_id.upper().replace("-", "_")
            return os.getenv(env_name)
            
        except gcp_exceptions.PermissionDenied:
            logger.error(f"Permission denied accessing secret {secret_id}")
            logger.error("Ensure the service account has 'Secret Manager Secret Accessor' role")
            return None
            
        except Exception as e:
            logger.error(f"Error accessing secret {secret_id}: {e}")
            return None
    
    def _log_access(self, secret_id: str):
        """Log secret access for monitoring"""
        self._access_log.append({
            "secret_id": secret_id,
            "timestamp": datetime.now().isoformat(),
            "service": os.getenv("SERVICE_NAME", "unknown")
        })
        
        # Trim log if too large
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-500:]
    
    def get_access_metrics(self) -> Dict[str, Any]:
        """Get access metrics for monitoring"""
        metrics = {
            "total_accesses": len(self._access_log),
            "unique_secrets": len(set(log["secret_id"] for log in self._access_log)),
            "access_by_secret": {}
        }
        
        for log in self._access_log:
            secret_id = log["secret_id"]
            if secret_id not in metrics["access_by_secret"]:
                metrics["access_by_secret"][secret_id] = 0
            metrics["access_by_secret"][secret_id] += 1
        
        return metrics
    
    def verify_all_secrets(self) -> Dict[str, bool]:
        """Verify all required secrets are accessible"""
        required_secrets = [
            "roadtrip-google-maps-key",
            "roadtrip-ticketmaster-key",
            "roadtrip-openweather-key",
            "roadtrip-database-url",
            "roadtrip-jwt-secret",
            "roadtrip-csrf-secret",
            "roadtrip-redis-url",
            "roadtrip-secret-key",
            "roadtrip-encryption-key"
        ]
        
        results = {}
        for secret_id in required_secrets:
            try:
                value = self.get_secret(secret_id)
                results[secret_id] = bool(value)
            except Exception as e:
                logger.error(f"Failed to verify secret {secret_id}: {e}")
                results[secret_id] = False
        
        return results
    
    def clear_cache(self):
        """Clear the secret cache"""
        self._cache.clear()
        self.get_secret.cache_clear()
        logger.info("Secret cache cleared")

# Global instances
enhanced_secret_manager = EnhancedSecretManager()

# Convenience function for backward compatibility
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """Get a secret from Secret Manager"""
    return enhanced_secret_manager.get_secret(secret_id, version)

# Export for use in other modules
__all__ = [
    "enhanced_secret_manager",
    "get_secret",
    "SecretRotationManager",
    "EnhancedSecretManager"
]
'''
    
    wrapper_path = Path("backend/app/core/enhanced_secret_manager.py")
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    
    print(f"Created enhanced secret manager wrapper: {wrapper_path}")

def create_rotation_monitoring_script():
    """Create a script to monitor credential usage and rotation"""
    monitoring_content = '''#!/usr/bin/env python3
"""
Monitor credential usage and rotation status
"""

import os
import sys
import json
from datetime import datetime, timedelta
from google.cloud import secretmanager
from google.cloud import monitoring_v3

PROJECT_ID = "roadtrip-460720"

def check_secret_age():
    """Check age of all secrets"""
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}"
    
    print("Secret Rotation Status:")
    print("-" * 80)
    
    secrets = client.list_secrets(request={"parent": parent})
    for secret in secrets:
        # Get latest version
        versions = client.list_secret_versions(
            request={"parent": secret.name, "filter": "state:ENABLED"}
        )
        
        latest = None
        for version in versions:
            if not latest or version.create_time > latest.create_time:
                latest = version
        
        if latest:
            age = datetime.now(latest.create_time.tzinfo) - latest.create_time
            status = "⚠️  NEEDS ROTATION" if age.days > 90 else "✅ OK"
            print(f"{secret.name.split('/')[-1]}: {age.days} days old {status}")

def check_api_key_usage():
    """Monitor API key usage"""
    metrics_client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{PROJECT_ID}"
    
    # Check Google Maps API usage
    print("\\nAPI Key Usage (last 24h):")
    print("-" * 80)
    
    # Define the time interval
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(datetime.now().timestamp())},
            "start_time": {"seconds": int((datetime.now() - timedelta(hours=24)).timestamp())},
        }
    )
    
    try:
        # Query for API key usage
        results = metrics_client.list_time_series(
            request={
                "name": project_name,
                "filter": 'metric.type="serviceruntime.googleapis.com/api/request_count"',
                "interval": interval,
            }
        )
        
        for result in results:
            api_name = result.resource.labels.get("service", "unknown")
            total_requests = sum(point.value.int64_value for point in result.points)
            print(f"{api_name}: {total_requests} requests")
            
    except Exception as e:
        print(f"Could not retrieve metrics: {e}")

def verify_secret_access():
    """Verify service account can access all secrets"""
    client = secretmanager.SecretManagerServiceClient()
    
    print("\\nSecret Access Verification:")
    print("-" * 80)
    
    required_secrets = [
        "roadtrip-google-maps-key",
        "roadtrip-ticketmaster-key",
        "roadtrip-openweather-key",
        "roadtrip-database-url",
        "roadtrip-jwt-secret",
        "roadtrip-csrf-secret",
        "roadtrip-redis-url"
    ]
    
    for secret_id in required_secrets:
        try:
            name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            print(f"✅ {secret_id}: Accessible")
        except Exception as e:
            print(f"❌ {secret_id}: {str(e)}")

if __name__ == "__main__":
    print("Credential Monitoring Report")
    print("=" * 80)
    print(f"Project: {PROJECT_ID}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    check_secret_age()
    check_api_key_usage()
    verify_secret_access()
'''
    
    monitoring_path = Path("scripts/security/monitor_credentials.py")
    with open(monitoring_path, 'w') as f:
        f.write(monitoring_content)
    os.chmod(monitoring_path, 0o755)
    
    print(f"Created credential monitoring script: {monitoring_path}")

def main():
    """Main execution"""
    print("Updating Secret Manager Integration")
    print("=" * 80)
    
    # Step 1: Scan for exposed credentials
    print("\n1. Scanning for exposed credentials...")
    all_findings = []
    
    for file_pattern in ["**/*.py", "**/*.yaml", "**/*.yml", "**/*.json", "**/.env*"]:
        for file_path in Path(".").glob(file_pattern):
            if "node_modules" in str(file_path) or "venv" in str(file_path):
                continue
            
            findings = scan_file_for_credentials(file_path)
            if findings:
                print(f"\n  Found in {file_path}:")
                for line_num, finding in findings:
                    print(f"    Line {line_num}: {finding}")
                all_findings.extend([(file_path, line_num, finding) for line_num, finding in findings])
    
    if not all_findings:
        print("  No exposed credentials found")
    
    # Step 2: Update configuration files
    print("\n2. Updating configuration files...")
    for config_file in CONFIG_FILES:
        file_path = Path(config_file)
        if file_path.exists():
            if update_file_for_secret_manager(file_path):
                print(f"  ✅ Updated: {config_file}")
            else:
                print(f"  ⏭️  No changes needed: {config_file}")
    
    # Step 3: Create enhanced secret manager
    print("\n3. Creating enhanced secret manager wrapper...")
    create_secret_manager_wrapper()
    
    # Step 4: Create monitoring script
    print("\n4. Creating credential monitoring script...")
    create_rotation_monitoring_script()
    
    # Step 5: Generate report
    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run emergency credential rotation: python scripts/security/emergency_credential_rotation.py")
    print("2. Deploy updated configuration: ./scripts/deployment/deploy.sh")
    print("3. Monitor credentials: python scripts/security/monitor_credentials.py")
    print("4. Set up automated rotation: cron job for scripts/security/secret-rotation.sh")

if __name__ == "__main__":
    main()
'''

    with open(update_path, 'w') as f:
        f.write(monitoring_content)
    os.chmod(update_path, 0o755)

if __name__ == "__main__":
    main()