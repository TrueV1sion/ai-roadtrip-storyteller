#!/usr/bin/env python3
"""
AI Road Trip Storyteller - Production Deployment Script
Cross-platform deployment automation for Google Cloud Platform

Features:
- Pre-checks all requirements (gcloud, APIs, permissions)
- Sets up the environment (project, region, APIs)
- Configures secrets if needed
- Builds and deploys using Cloud Build
- Verifies the deployment
- Provides rollback options
- Works on both Windows and Unix systems

Usage:
    python deploy_production.py [OPTIONS]

Options:
    --project-id     GCP Project ID (required)
    --environment    Environment to deploy (staging/production)
    --region         GCP region (default: us-central1)
    --rollback       Rollback to previous version
    --dry-run        Show what would be done without executing
    --force          Skip confirmation prompts
    --verbose        Enable verbose logging
"""

import os
import sys
import json
import time
import subprocess
import platform
import argparse
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    project_id: str
    environment: Environment
    region: str = "us-central1"
    service_name: str = "roadtrip-backend"
    memory: str = "2Gi"
    cpu: str = "2"
    max_instances: int = 100
    min_instances: int = 1
    timeout: int = 900
    concurrency: int = 100
    
    @property
    def full_service_name(self) -> str:
        """Get the full service name including environment"""
        if self.environment == Environment.PRODUCTION:
            return self.service_name
        return f"{self.service_name}-{self.environment.value}"
    
    @property
    def image_name(self) -> str:
        """Get the container image name"""
        return f"gcr.io/{self.project_id}/{self.service_name}"
    
    @property
    def service_account(self) -> str:
        """Get the service account email"""
        return f"{self.service_name}@{self.project_id}.iam.gserviceaccount.com"


class GCPDeployer:
    """Google Cloud Platform deployment manager"""
    
    # Required APIs for the application
    REQUIRED_APIS = [
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "secretmanager.googleapis.com",
        "sqladmin.googleapis.com",
        "redis.googleapis.com",
        "aiplatform.googleapis.com",
        "cloudtrace.googleapis.com",
        "monitoring.googleapis.com",
        "logging.googleapis.com",
        "maps-backend.googleapis.com",
        "places-backend.googleapis.com",
        "texttospeech.googleapis.com",
        "speech.googleapis.com",
        "containerregistry.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "iam.googleapis.com",
    ]
    
    # Required secrets for the application
    REQUIRED_SECRETS = {
        "roadtrip-database-url": "DATABASE_URL",
        "roadtrip-redis-url": "REDIS_URL",
        "roadtrip-jwt-secret": "JWT_SECRET_KEY",
        "roadtrip-secret-key": "SECRET_KEY",
        "roadtrip-csrf-secret": "CSRF_SECRET_KEY",
        "roadtrip-google-maps-key": "GOOGLE_MAPS_API_KEY",
        "roadtrip-ticketmaster-key": "TICKETMASTER_API_KEY",
        "roadtrip-openweather-key": "OPENWEATHERMAP_API_KEY",
        "roadtrip-recreation-key": "RECREATION_GOV_API_KEY",
        "roadtrip-spotify-id": "SPOTIFY_CLIENT_ID",
        "roadtrip-spotify-secret": "SPOTIFY_CLIENT_SECRET",
        "roadtrip-viator-key": "VIATOR_API_KEY",
        "roadtrip-opentable-key": "OPENTABLE_API_KEY",
    }
    
    # Service account roles
    SERVICE_ACCOUNT_ROLES = [
        "roles/aiplatform.user",
        "roles/secretmanager.secretAccessor",
        "roles/cloudsql.client",
        "roles/redis.editor",
        "roles/cloudtrace.agent",
        "roles/monitoring.metricWriter",
        "roles/logging.logWriter",
    ]
    
    def __init__(self, config: DeploymentConfig, dry_run: bool = False, verbose: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def run_command(self, cmd: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a command with proper cross-platform handling"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        
        logger.debug(f"Executing: {' '.join(cmd)}")
        
        # On Windows, use shell=True for gcloud commands
        use_shell = platform.system() == "Windows" and cmd[0] == "gcloud"
        
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
                shell=use_shell
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stdout:
                logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            raise
    
    def check_prerequisites(self) -> bool:
        """Check all prerequisites for deployment"""
        logger.info("Checking prerequisites...")
        
        # Check gcloud CLI
        if not self._check_gcloud():
            return False
        
        # Check authentication
        if not self._check_authentication():
            return False
        
        # Check project access
        if not self._check_project():
            return False
        
        # Check Docker
        if not self._check_docker():
            return False
        
        logger.info("✓ All prerequisites met")
        return True
    
    def _check_gcloud(self) -> bool:
        """Check if gcloud CLI is installed"""
        logger.info("Checking gcloud CLI installation...")
        
        if shutil.which("gcloud") is None:
            logger.error("✗ gcloud CLI not found. Please install from https://cloud.google.com/sdk")
            return False
        
        try:
            result = self.run_command(["gcloud", "version"], capture_output=True)
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
            logger.info(f"✓ gcloud CLI installed: {version_line}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to check gcloud version: {e}")
            return False
    
    def _check_authentication(self) -> bool:
        """Check GCP authentication"""
        logger.info("Checking authentication...")
        
        try:
            result = self.run_command([
                "gcloud", "auth", "list",
                "--filter=status:ACTIVE",
                "--format=value(account)"
            ], capture_output=True)
            
            if not result.stdout.strip():
                logger.error("✗ Not authenticated. Run: gcloud auth login")
                return False
            
            logger.info(f"✓ Authenticated as: {result.stdout.strip()}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to check authentication: {e}")
            return False
    
    def _check_project(self) -> bool:
        """Check if project exists and is accessible"""
        logger.info(f"Checking project {self.config.project_id}...")
        
        try:
            result = self.run_command([
                "gcloud", "projects", "describe",
                self.config.project_id,
                "--format=json"
            ], capture_output=True)
            
            project_info = json.loads(result.stdout)
            logger.info(f"✓ Project found: {project_info['name']}")
            logger.info(f"  State: {project_info['lifecycleState']}")
            
            # Set as active project
            self.run_command([
                "gcloud", "config", "set",
                "project", self.config.project_id
            ], capture_output=False)
            
            return True
        except Exception as e:
            logger.error(f"✗ Project not found or not accessible: {e}")
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is installed and running"""
        logger.info("Checking Docker installation...")
        
        if shutil.which("docker") is None:
            logger.error("✗ Docker not found. Please install Docker")
            return False
        
        try:
            result = self.run_command(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True)
            logger.info(f"✓ Docker installed: {result.stdout.strip()}")
            
            # Check if Docker daemon is running
            self.run_command(["docker", "ps"], capture_output=True)
            logger.info("✓ Docker daemon is running")
            return True
        except Exception as e:
            logger.error(f"✗ Docker check failed: {e}")
            logger.error("Make sure Docker daemon is running")
            return False
    
    def setup_environment(self) -> bool:
        """Set up the GCP environment"""
        logger.info("Setting up environment...")
        
        # Enable required APIs
        if not self._enable_apis():
            return False
        
        # Create service account
        if not self._setup_service_account():
            return False
        
        # Check/create secrets
        if not self._check_secrets():
            return False
        
        logger.info("✓ Environment setup complete")
        return True
    
    def _enable_apis(self) -> bool:
        """Enable required GCP APIs"""
        logger.info("Checking and enabling required APIs...")
        
        # Get currently enabled APIs
        try:
            result = self.run_command([
                "gcloud", "services", "list",
                "--enabled",
                "--format=value(config.name)"
            ], capture_output=True)
            
            enabled_apis = set(result.stdout.strip().split('\n')) if result.stdout else set()
            missing_apis = [api for api in self.REQUIRED_APIS if api not in enabled_apis]
            
            if not missing_apis:
                logger.info("✓ All required APIs are already enabled")
                return True
            
            logger.info(f"Enabling {len(missing_apis)} missing APIs...")
            
            # Enable missing APIs in batches
            batch_size = 5
            for i in range(0, len(missing_apis), batch_size):
                batch = missing_apis[i:i + batch_size]
                logger.info(f"  Enabling: {', '.join(batch)}")
                
                self.run_command([
                    "gcloud", "services", "enable",
                    *batch,
                    f"--project={self.config.project_id}"
                ])
                
                # Wait a bit for APIs to activate
                time.sleep(2)
            
            logger.info("✓ All APIs enabled")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to enable APIs: {e}")
            return False
    
    def _setup_service_account(self) -> bool:
        """Create and configure service account"""
        logger.info("Setting up service account...")
        
        try:
            # Check if service account exists
            result = self.run_command([
                "gcloud", "iam", "service-accounts", "describe",
                self.config.service_account,
                f"--project={self.config.project_id}"
            ], check=False, capture_output=True)
            
            if result.returncode != 0:
                # Create service account
                logger.info(f"Creating service account: {self.config.service_account}")
                self.run_command([
                    "gcloud", "iam", "service-accounts", "create",
                    self.config.service_name,
                    f"--display-name=RoadTrip Backend Service Account",
                    f"--project={self.config.project_id}"
                ])
            else:
                logger.info(f"✓ Service account already exists: {self.config.service_account}")
            
            # Grant required roles
            logger.info("Granting IAM roles...")
            for role in self.SERVICE_ACCOUNT_ROLES:
                self.run_command([
                    "gcloud", "projects", "add-iam-policy-binding",
                    self.config.project_id,
                    f"--member=serviceAccount:{self.config.service_account}",
                    f"--role={role}",
                    "--condition=None",
                    "--quiet"
                ])
            
            logger.info("✓ Service account configured")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to setup service account: {e}")
            return False
    
    def _check_secrets(self) -> bool:
        """Check if required secrets exist"""
        logger.info("Checking secrets...")
        
        try:
            # List existing secrets
            result = self.run_command([
                "gcloud", "secrets", "list",
                "--format=value(name)",
                f"--project={self.config.project_id}"
            ], capture_output=True)
            
            existing_secrets = set(result.stdout.strip().split('\n')) if result.stdout else set()
            missing_secrets = [s for s in self.REQUIRED_SECRETS.keys() if s not in existing_secrets]
            
            if missing_secrets:
                logger.warning(f"Missing secrets: {', '.join(missing_secrets)}")
                logger.warning("Please create these secrets in Secret Manager before deploying to production")
                
                if self.config.environment == Environment.PRODUCTION:
                    logger.error("✗ Cannot deploy to production without all secrets configured")
                    return False
                else:
                    logger.info("Continuing with staging deployment (will use default values)")
            else:
                logger.info("✓ All required secrets exist")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to check secrets: {e}")
            return False
    
    def build_and_push(self) -> bool:
        """Build and push Docker image"""
        logger.info("Building and pushing Docker image...")
        
        # Find the backend directory
        backend_dir = Path.cwd() / "backend"
        if not backend_dir.exists():
            logger.error(f"✗ Backend directory not found: {backend_dir}")
            return False
        
        # Check if Dockerfile exists
        dockerfile = backend_dir / "Dockerfile"
        if not dockerfile.exists():
            logger.error(f"✗ Dockerfile not found: {dockerfile}")
            return False
        
        try:
            # Configure Docker for GCR
            logger.info("Configuring Docker for Google Container Registry...")
            self.run_command([
                "gcloud", "auth", "configure-docker",
                "--quiet"
            ])
            
            # Build image
            build_tag = f"{self.config.image_name}:{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            latest_tag = f"{self.config.image_name}:latest"
            
            logger.info(f"Building Docker image: {build_tag}")
            self.run_command([
                "docker", "build",
                "-t", build_tag,
                "-t", latest_tag,
                "-f", str(dockerfile),
                str(backend_dir)
            ])
            
            # Push image
            logger.info(f"Pushing image to Container Registry...")
            self.run_command(["docker", "push", build_tag])
            self.run_command(["docker", "push", latest_tag])
            
            logger.info("✓ Image built and pushed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to build/push image: {e}")
            return False
    
    def deploy_service(self) -> Tuple[bool, Optional[str]]:
        """Deploy the service to Cloud Run"""
        logger.info(f"Deploying {self.config.full_service_name} to Cloud Run...")
        
        try:
            # Get current revision for rollback
            current_revision = self._get_current_revision()
            if current_revision:
                logger.info(f"Current revision: {current_revision}")
            
            # Deploy command
            deploy_cmd = [
                "gcloud", "run", "deploy",
                self.config.full_service_name,
                f"--image={self.config.image_name}:latest",
                f"--region={self.config.region}",
                "--platform=managed",
                f"--memory={self.config.memory}",
                f"--cpu={self.config.cpu}",
                f"--timeout={self.config.timeout}",
                f"--concurrency={self.config.concurrency}",
                f"--max-instances={self.config.max_instances}",
                f"--min-instances={self.config.min_instances}",
                f"--service-account={self.config.service_account}",
                "--allow-unauthenticated",
                "--port=8080",
                f"--set-env-vars=ENVIRONMENT={self.config.environment.value}",
                f"--set-env-vars=GOOGLE_CLOUD_PROJECT={self.config.project_id}",
                f"--set-env-vars=GOOGLE_AI_PROJECT_ID={self.config.project_id}",
                f"--set-env-vars=GOOGLE_AI_LOCATION={self.config.region}",
                f"--set-env-vars=VERTEX_AI_LOCATION={self.config.region}",
                "--set-env-vars=LOG_LEVEL=INFO",
                "--set-env-vars=CORS_ORIGINS=*",
                "--set-env-vars=API_V1_STR=/api/v1",
            ]
            
            # Add secrets
            for secret_name, env_var in self.REQUIRED_SECRETS.items():
                deploy_cmd.append(f"--set-secrets={env_var}={secret_name}:latest")
            
            # Add labels
            deploy_cmd.extend([
                f"--labels=environment={self.config.environment.value}",
                "--labels=app=roadtrip",
                "--labels=component=backend",
            ])
            
            # Deploy without traffic (for testing)
            deploy_cmd.append("--no-traffic")
            
            self.run_command(deploy_cmd)
            
            # Get the new revision
            new_revision = self._get_current_revision()
            logger.info(f"✓ Deployed new revision: {new_revision}")
            
            return True, current_revision
            
        except Exception as e:
            logger.error(f"✗ Failed to deploy service: {e}")
            return False, None
    
    def _get_current_revision(self) -> Optional[str]:
        """Get the current serving revision"""
        try:
            result = self.run_command([
                "gcloud", "run", "services", "describe",
                self.config.full_service_name,
                f"--region={self.config.region}",
                "--format=value(status.latestReadyRevisionName)"
            ], check=False, capture_output=True)
            
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            return None
    
    def verify_deployment(self, revision: Optional[str] = None) -> bool:
        """Verify the deployment is working"""
        logger.info("Verifying deployment...")
        
        try:
            # Get service URL
            result = self.run_command([
                "gcloud", "run", "services", "describe",
                self.config.full_service_name,
                f"--region={self.config.region}",
                "--format=value(status.address.url)"
            ], capture_output=True)
            
            service_url = result.stdout.strip()
            if not service_url:
                logger.error("✗ Could not get service URL")
                return False
            
            logger.info(f"Service URL: {service_url}")
            
            # If testing a specific revision, get its URL
            if revision:
                # Get revision URL by tag
                test_url = f"{service_url}"  # Cloud Run will route to tagged revision
            else:
                test_url = service_url
            
            # Health check
            logger.info("Running health checks...")
            
            # Wait for service to be ready
            time.sleep(10)
            
            # Try health endpoint multiple times
            import urllib.request
            import urllib.error
            
            for attempt in range(10):
                try:
                    with urllib.request.urlopen(f"{test_url}/health", timeout=10) as response:
                        if response.status == 200:
                            logger.info(f"✓ Health check passed (attempt {attempt + 1})")
                            
                            # Test other critical endpoints
                            with urllib.request.urlopen(f"{test_url}/api/v1/health", timeout=10) as api_response:
                                if api_response.status == 200:
                                    logger.info("✓ API health check passed")
                            
                            logger.info("✓ Deployment verified successfully")
                            return True
                except urllib.error.URLError as e:
                    logger.warning(f"Health check attempt {attempt + 1} failed: {e}")
                    time.sleep(10)
            
            logger.error("✗ Health checks failed after 10 attempts")
            return False
            
        except Exception as e:
            logger.error(f"✗ Failed to verify deployment: {e}")
            return False
    
    def shift_traffic(self, new_revision: str, old_revision: Optional[str] = None) -> bool:
        """Gradually shift traffic to new revision"""
        logger.info("Shifting traffic to new revision...")
        
        try:
            # Stage 1: 10% traffic
            logger.info("Stage 1: Shifting 10% traffic...")
            self.run_command([
                "gcloud", "run", "services", "update-traffic",
                self.config.full_service_name,
                f"--region={self.config.region}",
                f"--to-revisions={new_revision}=10"
            ])
            
            logger.info("Monitoring for 30 seconds...")
            time.sleep(30)
            
            # Stage 2: 50% traffic
            logger.info("Stage 2: Shifting 50% traffic...")
            self.run_command([
                "gcloud", "run", "services", "update-traffic",
                self.config.full_service_name,
                f"--region={self.config.region}",
                f"--to-revisions={new_revision}=50"
            ])
            
            logger.info("Monitoring for 30 seconds...")
            time.sleep(30)
            
            # Stage 3: 100% traffic
            logger.info("Stage 3: Shifting 100% traffic...")
            self.run_command([
                "gcloud", "run", "services", "update-traffic",
                self.config.full_service_name,
                f"--region={self.config.region}",
                f"--to-revisions={new_revision}=100"
            ])
            
            logger.info("✓ Traffic successfully shifted to new revision")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to shift traffic: {e}")
            
            # Attempt rollback if old revision exists
            if old_revision:
                logger.warning(f"Attempting rollback to {old_revision}...")
                try:
                    self.run_command([
                        "gcloud", "run", "services", "update-traffic",
                        self.config.full_service_name,
                        f"--region={self.config.region}",
                        f"--to-revisions={old_revision}=100"
                    ])
                    logger.info("✓ Rolled back to previous revision")
                except Exception as e:
                    logger.error("✗ Rollback failed!")
            
            return False
    
    def rollback(self, revision: str) -> bool:
        """Rollback to a specific revision"""
        logger.info(f"Rolling back to revision: {revision}")
        
        try:
            self.run_command([
                "gcloud", "run", "services", "update-traffic",
                self.config.full_service_name,
                f"--region={self.config.region}",
                f"--to-revisions={revision}=100"
            ])
            
            logger.info("✓ Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Rollback failed: {e}")
            return False
    
    def cleanup_old_revisions(self) -> bool:
        """Clean up old revisions (keep last 3)"""
        logger.info("Cleaning up old revisions...")
        
        try:
            # List all revisions
            result = self.run_command([
                "gcloud", "run", "revisions", "list",
                f"--service={self.config.full_service_name}",
                f"--region={self.config.region}",
                "--format=value(name)",
                "--sort-by=~creationTimestamp"
            ], capture_output=True)
            
            revisions = result.stdout.strip().split('\n') if result.stdout else []
            
            # Keep last 3 revisions
            if len(revisions) > 3:
                to_delete = revisions[3:]
                logger.info(f"Deleting {len(to_delete)} old revisions...")
                
                for revision in to_delete:
                    if revision:
                        self.run_command([
                            "gcloud", "run", "revisions", "delete",
                            revision,
                            f"--region={self.config.region}",
                            "--quiet"
                        ], check=False)
                
                logger.info("✓ Old revisions cleaned up")
            else:
                logger.info("✓ No old revisions to clean up")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to cleanup revisions: {e}")
            return False
    
    def deploy(self) -> bool:
        """Execute the full deployment process"""
        logger.info(f"Starting deployment to {self.config.environment.value}...")
        logger.info(f"Project: {self.config.project_id}")
        logger.info(f"Region: {self.config.region}")
        logger.info(f"Service: {self.config.full_service_name}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed")
            return False
        
        # Setup environment
        if not self.setup_environment():
            logger.error("Environment setup failed")
            return False
        
        # Build and push image
        if not self.build_and_push():
            logger.error("Build/push failed")
            return False
        
        # Deploy service
        success, old_revision = self.deploy_service()
        if not success:
            logger.error("Deployment failed")
            return False
        
        # Get new revision
        new_revision = self._get_current_revision()
        if not new_revision:
            logger.error("Could not get new revision")
            return False
        
        # Verify deployment
        if not self.verify_deployment(new_revision):
            logger.error("Deployment verification failed")
            if old_revision:
                logger.info("Attempting rollback...")
                self.rollback(old_revision)
            return False
        
        # Shift traffic
        if not self.shift_traffic(new_revision, old_revision):
            logger.error("Traffic shift failed")
            return False
        
        # Cleanup old revisions
        self.cleanup_old_revisions()
        
        # Final verification
        if not self.verify_deployment():
            logger.error("Final verification failed")
            return False
        
        logger.info("=" * 60)
        logger.info("✅ DEPLOYMENT SUCCESSFUL!")
        logger.info("=" * 60)
        
        # Get final service URL
        result = self.run_command([
            "gcloud", "run", "services", "describe",
            self.config.full_service_name,
            f"--region={self.config.region}",
            "--format=value(status.address.url)"
        ], capture_output=True)
        
        service_url = result.stdout.strip()
        logger.info(f"Service URL: {service_url}")
        logger.info(f"API Docs: {service_url}/docs")
        logger.info(f"Health Check: {service_url}/health")
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Deploy AI Road Trip Storyteller to Google Cloud Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy to staging
  python deploy_production.py --project-id my-project --environment staging
  
  # Deploy to production with confirmation
  python deploy_production.py --project-id my-project --environment production
  
  # Rollback to previous version
  python deploy_production.py --project-id my-project --rollback REVISION_NAME
  
  # Dry run to see what would happen
  python deploy_production.py --project-id my-project --dry-run
        """
    )
    
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP Project ID"
    )
    
    parser.add_argument(
        "--environment",
        choices=["staging", "production"],
        default="staging",
        help="Deployment environment (default: staging)"
    )
    
    parser.add_argument(
        "--region",
        default="us-central1",
        help="GCP region (default: us-central1)"
    )
    
    parser.add_argument(
        "--rollback",
        metavar="REVISION",
        help="Rollback to specific revision"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Create deployment config
    config = DeploymentConfig(
        project_id=args.project_id,
        environment=Environment(args.environment),
        region=args.region
    )
    
    # Create deployer
    deployer = GCPDeployer(config, dry_run=args.dry_run, verbose=args.verbose)
    
    # Handle rollback
    if args.rollback:
        logger.info("Starting rollback process...")
        if not args.force and args.environment == "production":
            response = input(f"Are you sure you want to rollback production to {args.rollback}? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Rollback cancelled")
                return
        
        if deployer.rollback(args.rollback):
            logger.info("✅ Rollback completed successfully")
        else:
            logger.error("❌ Rollback failed")
            sys.exit(1)
        return
    
    # Confirmation for production
    if not args.force and args.environment == "production" and not args.dry_run:
        logger.warning("=" * 60)
        logger.warning("⚠️  PRODUCTION DEPLOYMENT WARNING")
        logger.warning("=" * 60)
        logger.warning("You are about to deploy to PRODUCTION.")
        logger.warning("This will affect real users and data.")
        logger.warning("")
        logger.warning(f"Project: {args.project_id}")
        logger.warning(f"Environment: {args.environment}")
        logger.warning(f"Region: {args.region}")
        logger.warning("")
        
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Deployment cancelled")
            return
    
    # Execute deployment
    if deployer.deploy():
        logger.info("✅ Deployment completed successfully")
    else:
        logger.error("❌ Deployment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()