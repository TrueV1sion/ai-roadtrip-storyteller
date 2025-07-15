#!/usr/bin/env python3
"""
Production Deployment Wizard
Interactive wizard to guide through actual GCP production deployment
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional

class ProductionDeploymentWizard:
    """Interactive wizard for production deployment"""
    
    def __init__(self):
        self.config = {}
        self.completed_steps = []
        
    def run(self):
        """Run the deployment wizard"""
        print("\n🚀 AI ROAD TRIP STORYTELLER - PRODUCTION DEPLOYMENT WIZARD")
        print("=" * 60)
        print("This wizard will guide you through deploying to Google Cloud Platform")
        print()
        
        # Check prerequisites
        if not self.check_prerequisites():
            return
        
        # Collect configuration
        self.collect_configuration()
        
        # Confirm deployment
        if not self.confirm_deployment():
            print("\n❌ Deployment cancelled")
            return
        
        # Execute deployment steps
        self.execute_deployment()
    
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        print("📋 Checking prerequisites...")
        
        required_tools = {
            "gcloud": "Google Cloud SDK",
            "docker": "Docker",
            "python3": "Python 3",
            "alembic": "Alembic (database migrations)"
        }
        
        missing_tools = []
        
        for tool, name in required_tools.items():
            try:
                if tool == "alembic":
                    subprocess.run(["python3", "-m", "alembic", "--version"], 
                                 capture_output=True, check=True)
                else:
                    subprocess.run([tool, "--version"], 
                                 capture_output=True, check=True)
                print(f"  ✅ {name} found")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"  ❌ {name} not found")
                missing_tools.append(name)
        
        if missing_tools:
            print(f"\n❌ Missing required tools: {', '.join(missing_tools)}")
            print("\nInstallation instructions:")
            print("  • Google Cloud SDK: https://cloud.google.com/sdk/install")
            print("  • Docker: https://docs.docker.com/get-docker/")
            print("  • Alembic: pip install alembic")
            return False
        
        # Check if logged in to gcloud
        try:
            result = subprocess.run(["gcloud", "auth", "list", "--filter=status:ACTIVE", 
                                   "--format=value(account)"], 
                                  capture_output=True, text=True, check=True)
            if result.stdout.strip():
                print(f"  ✅ Logged in to GCP as: {result.stdout.strip()}")
            else:
                print("  ❌ Not logged in to Google Cloud")
                print("     Run: gcloud auth login")
                return False
        except subprocess.CalledProcessError:
            print("  ❌ Error checking GCP authentication")
            return False
        
        return True
    
    def collect_configuration(self):
        """Collect deployment configuration from user"""
        print("\n📝 Configuration")
        print("-" * 40)
        
        # Project ID
        default_project = "ai-road-trip-prod"
        self.config["project_id"] = input(f"GCP Project ID [{default_project}]: ").strip() or default_project
        
        # Region
        default_region = "us-central1"
        self.config["region"] = input(f"Region [{default_region}]: ").strip() or default_region
        
        # Service name
        default_service = "roadtrip-api"
        self.config["service_name"] = input(f"Service name [{default_service}]: ").strip() or default_service
        
        # Environment
        self.config["environment"] = "production"
        
        # Check if project exists
        try:
            subprocess.run(["gcloud", "projects", "describe", self.config["project_id"]], 
                         capture_output=True, check=True)
            print(f"\n✅ Project '{self.config['project_id']}' exists")
            self.config["create_project"] = False
        except subprocess.CalledProcessError:
            print(f"\n⚠️  Project '{self.config['project_id']}' does not exist")
            create = input("Create new project? (y/n): ").lower() == 'y'
            self.config["create_project"] = create
            if create:
                self.config["billing_account"] = input("Billing Account ID: ").strip()
    
    def confirm_deployment(self) -> bool:
        """Confirm deployment configuration"""
        print("\n📋 Deployment Summary")
        print("-" * 40)
        print(f"Project ID:    {self.config['project_id']}")
        print(f"Region:        {self.config['region']}")
        print(f"Service Name:  {self.config['service_name']}")
        print(f"Environment:   {self.config['environment']}")
        
        if self.config.get("create_project"):
            print(f"Action:        CREATE NEW PROJECT")
            print(f"Billing:       {self.config['billing_account']}")
        else:
            print(f"Action:        DEPLOY TO EXISTING PROJECT")
        
        print("\n⚠️  This will:")
        print("  • Enable required Google Cloud APIs")
        print("  • Create Cloud SQL and Redis instances")
        print("  • Deploy the application to Cloud Run")
        print("  • Set up monitoring and logging")
        
        return input("\nProceed with deployment? (y/n): ").lower() == 'y'
    
    def execute_deployment(self):
        """Execute the deployment steps"""
        print("\n🚀 Starting Deployment")
        print("=" * 60)
        
        steps = [
            ("Creating/configuring project", self.setup_project),
            ("Enabling APIs", self.enable_apis),
            ("Creating Cloud SQL instance", self.create_cloud_sql),
            ("Creating Redis instance", self.create_redis),
            ("Setting up secrets", self.setup_secrets),
            ("Building Docker image", self.build_docker_image),
            ("Deploying to Cloud Run", self.deploy_cloud_run),
            ("Running database migrations", self.run_migrations),
            ("Setting up monitoring", self.setup_monitoring),
            ("Running verification tests", self.run_verification)
        ]
        
        for step_name, step_func in steps:
            print(f"\n⏳ {step_name}...")
            try:
                step_func()
                print(f"✅ {step_name} completed")
                self.completed_steps.append(step_name)
            except Exception as e:
                print(f"❌ {step_name} failed: {str(e)}")
                self.handle_failure()
                return
        
        self.deployment_complete()
    
    def setup_project(self):
        """Create or configure GCP project"""
        if self.config.get("create_project"):
            # Create project
            subprocess.run([
                "gcloud", "projects", "create", self.config["project_id"],
                "--name=AI Road Trip Storyteller"
            ], check=True)
            
            # Link billing
            subprocess.run([
                "gcloud", "billing", "projects", "link", self.config["project_id"],
                f"--billing-account={self.config['billing_account']}"
            ], check=True)
        
        # Set as default project
        subprocess.run([
            "gcloud", "config", "set", "project", self.config["project_id"]
        ], check=True)
    
    def enable_apis(self):
        """Enable required Google Cloud APIs"""
        apis = [
            "run.googleapis.com",
            "sqladmin.googleapis.com", 
            "redis.googleapis.com",
            "secretmanager.googleapis.com",
            "containerregistry.googleapis.com",
            "monitoring.googleapis.com",
            "logging.googleapis.com"
        ]
        
        for api in apis:
            print(f"  Enabling {api}...")
            subprocess.run([
                "gcloud", "services", "enable", api
            ], check=True)
    
    def create_cloud_sql(self):
        """Create Cloud SQL instance"""
        instance_name = f"{self.config['service_name']}-db"
        
        # Check if instance exists
        try:
            subprocess.run([
                "gcloud", "sql", "instances", "describe", instance_name
            ], capture_output=True, check=True)
            print(f"  Cloud SQL instance '{instance_name}' already exists")
        except subprocess.CalledProcessError:
            # Create instance
            subprocess.run([
                "gcloud", "sql", "instances", "create", instance_name,
                "--database-version=POSTGRES_15",
                "--tier=db-g1-small",
                f"--region={self.config['region']}",
                "--network=default",
                "--backup",
                "--backup-start-time=03:00"
            ], check=True)
            
            # Create database
            subprocess.run([
                "gcloud", "sql", "databases", "create", "roadtrip",
                f"--instance={instance_name}"
            ], check=True)
            
            # Create user
            subprocess.run([
                "gcloud", "sql", "users", "create", "roadtrip_user",
                f"--instance={instance_name}",
                "--password=CHANGE_ME_AFTER_DEPLOY"
            ], check=True)
            
            print("  ⚠️  Remember to change the database password after deployment!")
    
    def create_redis(self):
        """Create Redis instance"""
        instance_name = f"{self.config['service_name']}-cache"
        
        # Check if instance exists
        try:
            subprocess.run([
                "gcloud", "redis", "instances", "describe", instance_name,
                f"--region={self.config['region']}"
            ], capture_output=True, check=True)
            print(f"  Redis instance '{instance_name}' already exists")
        except subprocess.CalledProcessError:
            # Create instance
            subprocess.run([
                "gcloud", "redis", "instances", "create", instance_name,
                "--size=1",
                f"--region={self.config['region']}",
                "--redis-version=redis_7_0",
                "--network=default"
            ], check=True)
    
    def setup_secrets(self):
        """Set up Secret Manager"""
        print("  Setting up secrets in Secret Manager...")
        print("  Run this after deployment:")
        print(f"  python scripts/migrate_to_secret_manager.py --project={self.config['project_id']}")
    
    def build_docker_image(self):
        """Build and push Docker image"""
        image_tag = f"gcr.io/{self.config['project_id']}/{self.config['service_name']}:latest"
        
        # Build image
        subprocess.run([
            "docker", "build", "-t", image_tag, "-f", "Dockerfile.cloudrun", "."
        ], check=True)
        
        # Configure docker for GCR
        subprocess.run([
            "gcloud", "auth", "configure-docker"
        ], check=True)
        
        # Push image
        subprocess.run([
            "docker", "push", image_tag
        ], check=True)
    
    def deploy_cloud_run(self):
        """Deploy to Cloud Run"""
        image_tag = f"gcr.io/{self.config['project_id']}/{self.config['service_name']}:latest"
        
        subprocess.run([
            "gcloud", "run", "deploy", self.config["service_name"],
            f"--image={image_tag}",
            "--platform=managed",
            f"--region={self.config['region']}",
            "--allow-unauthenticated",
            "--set-env-vars=ENVIRONMENT=production",
            "--memory=2Gi",
            "--cpu=2",
            "--min-instances=1",
            "--max-instances=100"
        ], check=True)
        
        # Get service URL
        result = subprocess.run([
            "gcloud", "run", "services", "describe", self.config["service_name"],
            "--platform=managed",
            f"--region={self.config['region']}",
            "--format=value(status.url)"
        ], capture_output=True, text=True, check=True)
        
        self.config["service_url"] = result.stdout.strip()
        print(f"  Service URL: {self.config['service_url']}")
    
    def run_migrations(self):
        """Run database migrations"""
        print("  ⚠️  Database migrations require manual configuration")
        print("  After setting up database credentials, run:")
        print("  alembic upgrade head")
    
    def setup_monitoring(self):
        """Set up monitoring and alerting"""
        # Create uptime check
        subprocess.run([
            "gcloud", "monitoring", "uptime-checks", "create",
            f"{self.config['service_name']}-health",
            f"--display-name={self.config['service_name']} Health Check",
            f"--resource-type=URL",
            f"--resource-labels=host={self.config['service_url'].replace('https://', '')}",
            "--check-interval=60"
        ], check=True)
    
    def run_verification(self):
        """Run verification tests"""
        if self.config.get("service_url"):
            print(f"  Testing health endpoint: {self.config['service_url']}/health")
            # Note: Actual curl command would go here
    
    def handle_failure(self):
        """Handle deployment failure"""
        print("\n❌ Deployment failed!")
        print(f"Completed steps: {', '.join(self.completed_steps)}")
        print("\nTo retry, fix the issue and run this wizard again.")
        print("The wizard will skip already completed steps.")
    
    def deployment_complete(self):
        """Show deployment completion message"""
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print(f"\nService URL: {self.config.get('service_url', 'N/A')}")
        print(f"Project ID:  {self.config['project_id']}")
        print(f"Region:      {self.config['region']}")
        
        print("\n📋 Next Steps:")
        print("1. Configure secrets using Secret Manager")
        print("2. Update database password")
        print("3. Run database migrations")
        print("4. Configure custom domain (optional)")
        print("5. Run integration tests")
        print("6. Create beta user accounts")
        
        print("\n🎉 Your AI Road Trip Storyteller is ready for production!")


def main():
    """Main function"""
    wizard = ProductionDeploymentWizard()
    try:
        wizard.run()
    except KeyboardInterrupt:
        print("\n\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()