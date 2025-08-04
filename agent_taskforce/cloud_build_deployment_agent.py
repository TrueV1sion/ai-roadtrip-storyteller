#!/usr/bin/env python3
"""
Cloud Build Deployment Agent
Uses Google Cloud Build for staging deployment without local Docker
"""

import os
import sys
import json
import subprocess
import time
import requests
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class CloudBuildDeploymentAgent:
    """Deploys to staging using Google Cloud Build"""
    
    def __init__(self):
        self.project_root = Path("/mnt/c/users/jared/onedrive/desktop/roadtrip")
        self.staging_config = {
            "project_id": "roadtrip-460720",
            "region": "us-central1",
            "service_name": "roadtrip-backend-staging",
            "environment": "staging"
        }
        self.deployment_metrics = {
            "start_time": time.time(),
            "build_id": None,
            "service_url": None,
            "success": False
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log with formatting"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        symbol = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "METRIC": "📊"
        }.get(level, "•")
        print(f"[{timestamp}] {symbol} {message}")
        
    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """Execute shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def create_cloudbuild_config(self):
        """Create Cloud Build configuration"""
        self.log("Creating Cloud Build configuration...", "INFO")
        
        cloudbuild_config = {
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "build",
                        "-t",
                        f"gcr.io/{self.staging_config['project_id']}/roadtrip-backend:staging-$SHORT_SHA",
                        "-t",
                        f"gcr.io/{self.staging_config['project_id']}/roadtrip-backend:staging-latest",
                        "-f",
                        "Dockerfile",
                        "."
                    ]
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "push",
                        f"gcr.io/{self.staging_config['project_id']}/roadtrip-backend:staging-$SHORT_SHA"
                    ]
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "push",
                        f"gcr.io/{self.staging_config['project_id']}/roadtrip-backend:staging-latest"
                    ]
                },
                {
                    "name": "gcr.io/google.com/cloudsdktool/cloud-sdk",
                    "entrypoint": "gcloud",
                    "args": [
                        "run",
                        "deploy",
                        self.staging_config['service_name'],
                        "--image",
                        f"gcr.io/{self.staging_config['project_id']}/roadtrip-backend:staging-$SHORT_SHA",
                        "--region",
                        self.staging_config['region'],
                        "--platform",
                        "managed",
                        "--port",
                        "8000",
                        "--cpu",
                        "1",
                        "--memory",
                        "1Gi",
                        "--min-instances",
                        "0",
                        "--max-instances",
                        "5",
                        "--concurrency",
                        "100",
                        "--timeout",
                        "300",
                        "--allow-unauthenticated",
                        "--set-env-vars",
                        "ENVIRONMENT=staging,LOG_LEVEL=INFO",
                        "--service-account",
                        f"roadtrip-backend@{self.staging_config['project_id']}.iam.gserviceaccount.com"
                    ]
                }
            ],
            "timeout": "1200s",
            "options": {
                "logging": "CLOUD_LOGGING_ONLY",
                "machineType": "N1_HIGHCPU_8"
            }
        }
        
        # Write Cloud Build config
        cloudbuild_path = self.project_root / "cloudbuild-staging.yaml"
        with open(cloudbuild_path, 'w') as f:
            yaml.dump(cloudbuild_config, f, default_flow_style=False)
            
        self.log("Created cloudbuild-staging.yaml", "SUCCESS")
        return cloudbuild_path
        
    def check_prerequisites(self):
        """Check deployment prerequisites"""
        self.log("Checking prerequisites...", "INFO")
        
        # Check gcloud CLI
        success, stdout, stderr = self.execute_command("gcloud --version")
        if not success:
            self.log("Google Cloud SDK not installed", "ERROR")
            self.log("Install from: https://cloud.google.com/sdk/install", "INFO")
            return False
        self.log("Google Cloud SDK available", "SUCCESS")
        
        # Check authentication
        success, stdout, stderr = self.execute_command("gcloud auth list --filter=status:ACTIVE --format='value(account)'")
        if not stdout.strip():
            self.log("Not authenticated to Google Cloud", "ERROR")
            self.log("Run: gcloud auth login", "INFO")
            return False
        self.log(f"Authenticated as: {stdout.strip()}", "SUCCESS")
        
        # Check project
        success, stdout, stderr = self.execute_command("gcloud config get-value project")
        if stdout.strip() != self.staging_config['project_id']:
            self.log(f"Setting project to {self.staging_config['project_id']}", "INFO")
            self.execute_command(f"gcloud config set project {self.staging_config['project_id']}")
            
        # Enable required APIs
        self.log("Checking required APIs...", "INFO")
        required_apis = [
            "cloudbuild.googleapis.com",
            "run.googleapis.com",
            "containerregistry.googleapis.com"
        ]
        
        for api in required_apis:
            success, stdout, stderr = self.execute_command(
                f"gcloud services list --enabled --filter='name:{api}' --format='value(name)'"
            )
            if api not in stdout:
                self.log(f"Enabling {api}...", "INFO")
                self.execute_command(f"gcloud services enable {api}")
                
        return True
        
    def submit_cloud_build(self, config_path: Path):
        """Submit build to Cloud Build"""
        self.log("\nSubmitting to Cloud Build...", "INFO")
        
        # Create substitutions for environment variables
        substitutions = [
            f"_PROJECT_ID={self.staging_config['project_id']}",
            f"_REGION={self.staging_config['region']}",
            f"_SERVICE_NAME={self.staging_config['service_name']}"
        ]
        
        # Submit build
        command = f"""
        gcloud builds submit \\
            --config={config_path} \\
            --substitutions={','.join(substitutions)} \\
            --project={self.staging_config['project_id']}
        """
        
        self.log("Starting Cloud Build job...", "INFO")
        self.log("This will take 5-10 minutes...", "INFO")
        
        success, stdout, stderr = self.execute_command(command)
        
        if success:
            # Extract build ID from output
            for line in stdout.split('\n'):
                if 'logs are available at' in line:
                    self.deployment_metrics['build_id'] = line.split('/')[-1].strip(']')
                    
            self.log("Cloud Build submitted successfully", "SUCCESS")
            self.log(f"Build ID: {self.deployment_metrics['build_id']}", "INFO")
            
            # Get service URL
            self.get_service_url()
            return True
        else:
            self.log(f"Cloud Build failed: {stderr}", "ERROR")
            return False
            
    def get_service_url(self):
        """Get the deployed service URL"""
        command = f"""
        gcloud run services describe {self.staging_config['service_name']} \\
            --region={self.staging_config['region']} \\
            --format='value(status.url)'
        """
        
        success, stdout, stderr = self.execute_command(command)
        if success and stdout.strip():
            self.deployment_metrics['service_url'] = stdout.strip()
            self.log(f"Service URL: {self.deployment_metrics['service_url']}", "SUCCESS")
            
    def validate_deployment(self):
        """Validate the deployment"""
        if not self.deployment_metrics['service_url']:
            self.log("No service URL available", "ERROR")
            return False
            
        self.log("\nValidating deployment...", "INFO")
        
        # Wait for service to be ready
        self.log("Waiting for service to stabilize...", "INFO")
        time.sleep(30)
        
        # Health check
        health_url = f"{self.deployment_metrics['service_url']}/health"
        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                self.log("Health check passed", "SUCCESS")
                health_data = response.json()
                self.log(f"Environment: {health_data.get('environment', 'unknown')}", "INFO")
                self.deployment_metrics['success'] = True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"Health check error: {str(e)}", "ERROR")
            
        # Test API endpoints
        self.log("\nTesting API endpoints...", "INFO")
        test_endpoints = [
            "/docs",
            "/api/v1/voices",
            "/openapi.json"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"{self.deployment_metrics['service_url']}{endpoint}", timeout=5)
                if response.status_code == 200:
                    self.log(f"✓ {endpoint}", "SUCCESS")
                else:
                    self.log(f"✗ {endpoint} ({response.status_code})", "WARNING")
            except Exception as e:
                self.log(f"✗ {endpoint} (timeout)", "WARNING")
                
        return self.deployment_metrics['success']
        
    def generate_deployment_summary(self):
        """Generate deployment summary"""
        duration = time.time() - self.deployment_metrics['start_time']
        
        summary = f"""
# Staging Deployment Summary

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration**: {duration:.1f} seconds
**Status**: {'✅ Success' if self.deployment_metrics['success'] else '❌ Failed'}

## Deployment Details

- **Project**: {self.staging_config['project_id']}
- **Service**: {self.staging_config['service_name']}
- **Region**: {self.staging_config['region']}
- **Build ID**: {self.deployment_metrics['build_id']}
- **Service URL**: {self.deployment_metrics['service_url']}

## Access Points

- API Documentation: {self.deployment_metrics['service_url']}/docs
- Health Check: {self.deployment_metrics['service_url']}/health
- OpenAPI Schema: {self.deployment_metrics['service_url']}/openapi.json

## Next Steps

1. Monitor Cloud Build logs:
   ```bash
   gcloud builds log {self.deployment_metrics['build_id']}
   ```

2. View service logs:
   ```bash
   gcloud run services logs read {self.staging_config['service_name']} \\
       --region={self.staging_config['region']}
   ```

3. Run integration tests:
   ```bash
   cd agent_taskforce
   python3 live_integration_test_runner_updated.py
   ```

## Notes

- The deployment used Google Cloud Build to avoid local Docker requirements
- The service is configured with staging environment variables
- Authentication is disabled for easy testing
- Monitoring and logging are enabled
"""
        
        # Save summary
        summary_path = self.project_root / f"STAGING_DEPLOYMENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(summary_path, 'w') as f:
            f.write(summary)
            
        self.log(f"\nDeployment summary saved to: {summary_path}", "SUCCESS")
        print(summary)
        
def main():
    """Run Cloud Build deployment"""
    agent = CloudBuildDeploymentAgent()
    
    agent.log("=" * 60)
    agent.log("Google Cloud Build Staging Deployment")
    agent.log("=" * 60)
    
    # Check prerequisites
    if not agent.check_prerequisites():
        return 1
        
    # Create Cloud Build config
    config_path = agent.create_cloudbuild_config()
    
    # Submit to Cloud Build
    if not agent.submit_cloud_build(config_path):
        return 1
        
    # Validate deployment
    agent.validate_deployment()
    
    # Generate summary
    agent.generate_deployment_summary()
    
    return 0 if agent.deployment_metrics['success'] else 1

if __name__ == "__main__":
    sys.exit(main())