#!/usr/bin/env python3
"""
Quick infrastructure setup script for AI Road Trip Storyteller.
Sets up GCP infrastructure and configures the application for production.
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import secrets
import string


class Colors:
    """Terminal colors for better output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
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


def run_command(command: str, capture_output: bool = False) -> Optional[str]:
    """Run a shell command and return output if requested."""
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(command, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {command}")
        if capture_output and e.stderr:
            print_error(f"Error: {e.stderr}")
        return None


def check_prerequisites():
    """Check if required tools are installed."""
    print_header("Checking Prerequisites")
    
    tools = {
        "gcloud": "Google Cloud SDK",
        "docker": "Docker",
        "kubectl": "Kubernetes CLI",
        "terraform": "Terraform (optional)"
    }
    
    missing_tools = []
    for tool, name in tools.items():
        if run_command(f"which {tool}", capture_output=True):
            print_success(f"{name} is installed")
        else:
            missing_tools.append(name)
            print_warning(f"{name} is not installed")
    
    if missing_tools and "Terraform" not in missing_tools:
        print_error("\nMissing required tools. Please install:")
        for tool in missing_tools:
            if tool != "Terraform (optional)":
                print(f"  - {tool}")
        sys.exit(1)
    
    return True


def setup_gcp_project():
    """Set up or select GCP project."""
    print_header("Google Cloud Project Setup")
    
    # Check if already logged in
    account = run_command("gcloud config get-value account", capture_output=True)
    if not account:
        print_info("Please log in to Google Cloud:")
        run_command("gcloud auth login")
    else:
        print_success(f"Logged in as: {account}")
    
    # Get current project
    current_project = run_command("gcloud config get-value project", capture_output=True)
    
    if current_project:
        use_current = input(f"\nUse existing project '{current_project}'? (Y/n): ").lower()
        if use_current != 'n':
            return current_project
    
    # Create new project or select existing
    create_new = input("\nCreate new project? (y/N): ").lower()
    
    if create_new == 'y':
        project_id = input("Enter new project ID (lowercase, hyphens allowed): ").lower()
        project_name = input("Enter project name: ")
        
        print_info(f"Creating project '{project_id}'...")
        if run_command(f"gcloud projects create {project_id} --name='{project_name}'"):
            print_success(f"Project '{project_id}' created")
            run_command(f"gcloud config set project {project_id}")
            
            # Link billing account
            print_info("Linking billing account...")
            billing_accounts = run_command("gcloud billing accounts list --format='value(name)'", capture_output=True)
            if billing_accounts:
                billing_account = billing_accounts.split('\n')[0]
                run_command(f"gcloud billing projects link {project_id} --billing-account={billing_account}")
                print_success("Billing account linked")
            else:
                print_warning("No billing account found. Please set up billing manually.")
            
            return project_id
    else:
        # List existing projects
        print_info("Existing projects:")
        run_command("gcloud projects list")
        project_id = input("\nEnter project ID to use: ")
        run_command(f"gcloud config set project {project_id}")
        return project_id


def enable_apis(project_id: str):
    """Enable required Google Cloud APIs."""
    print_header("Enabling Required APIs")
    
    apis = [
        "compute.googleapis.com",
        "container.googleapis.com",
        "sqladmin.googleapis.com",
        "redis.googleapis.com",
        "secretmanager.googleapis.com",
        "cloudrun.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com",
        "monitoring.googleapis.com",
        "logging.googleapis.com",
        "storage-component.googleapis.com",
        "aiplatform.googleapis.com",
        "texttospeech.googleapis.com",
        "speech.googleapis.com",
        "maps-backend.googleapis.com",
        "places-backend.googleapis.com",
        "geocoding-backend.googleapis.com",
        "routes.googleapis.com"
    ]
    
    print_info(f"Enabling {len(apis)} APIs (this may take a few minutes)...")
    
    for api in apis:
        print(f"  Enabling {api}...", end='', flush=True)
        if run_command(f"gcloud services enable {api} --project={project_id}"):
            print(f" {Colors.GREEN}✓{Colors.END}")
        else:
            print(f" {Colors.RED}✗{Colors.END}")
    
    print_success("APIs enabled")


def create_service_account(project_id: str) -> str:
    """Create service account for the application."""
    print_header("Creating Service Account")
    
    service_account_name = "roadtrip-app"
    service_account_email = f"{service_account_name}@{project_id}.iam.gserviceaccount.com"
    
    # Create service account
    print_info("Creating service account...")
    run_command(f"""gcloud iam service-accounts create {service_account_name} \
        --display-name="Road Trip App Service Account" \
        --project={project_id}""")
    
    # Grant necessary roles
    roles = [
        "roles/aiplatform.user",
        "roles/cloudsql.client",
        "roles/redis.editor",
        "roles/storage.objectAdmin",
        "roles/secretmanager.secretAccessor",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/texttospeech.client",
        "roles/speech.client"
    ]
    
    print_info("Granting IAM roles...")
    for role in roles:
        run_command(f"""gcloud projects add-iam-policy-binding {project_id} \
            --member=serviceAccount:{service_account_email} \
            --role={role}""")
    
    # Create and download key
    key_file = "service-account-key.json"
    print_info("Creating service account key...")
    run_command(f"""gcloud iam service-accounts keys create {key_file} \
        --iam-account={service_account_email} \
        --project={project_id}""")
    
    print_success(f"Service account created: {service_account_email}")
    print_success(f"Key saved to: {key_file}")
    
    return key_file


def setup_cloud_sql(project_id: str) -> Dict[str, str]:
    """Set up Cloud SQL instance."""
    print_header("Setting up Cloud SQL")
    
    instance_name = "roadtrip-db"
    region = "us-central1"
    
    # Check if instance already exists
    existing = run_command(f"gcloud sql instances describe {instance_name} --project={project_id}", capture_output=True)
    
    if not existing:
        print_info("Creating Cloud SQL instance (this will take 5-10 minutes)...")
        run_command(f"""gcloud sql instances create {instance_name} \
            --database-version=POSTGRES_15 \
            --tier=db-g1-small \
            --region={region} \
            --network=default \
            --no-assign-ip \
            --project={project_id}""")
        print_success("Cloud SQL instance created")
    else:
        print_info("Using existing Cloud SQL instance")
    
    # Set root password
    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    run_command(f"""gcloud sql users set-password postgres \
        --instance={instance_name} \
        --password='{password}' \
        --project={project_id}""")
    
    # Create database
    print_info("Creating database...")
    run_command(f"""gcloud sql databases create roadtrip \
        --instance={instance_name} \
        --project={project_id}""")
    
    # Get connection name
    connection_name = run_command(
        f"gcloud sql instances describe {instance_name} --format='value(connectionName)' --project={project_id}",
        capture_output=True
    )
    
    return {
        "instance_name": instance_name,
        "connection_name": connection_name,
        "database": "roadtrip",
        "user": "postgres",
        "password": password
    }


def setup_redis(project_id: str) -> Dict[str, str]:
    """Set up Redis instance."""
    print_header("Setting up Redis")
    
    instance_name = "roadtrip-cache"
    region = "us-central1"
    
    # Check if instance already exists
    existing = run_command(
        f"gcloud redis instances describe {instance_name} --region={region} --project={project_id}",
        capture_output=True
    )
    
    if not existing:
        print_info("Creating Redis instance (this will take 5-10 minutes)...")
        run_command(f"""gcloud redis instances create {instance_name} \
            --size=1 \
            --region={region} \
            --redis-version=redis_7_0 \
            --project={project_id}""")
        print_success("Redis instance created")
    else:
        print_info("Using existing Redis instance")
    
    # Get Redis details
    redis_host = run_command(
        f"gcloud redis instances describe {instance_name} --region={region} --format='value(host)' --project={project_id}",
        capture_output=True
    )
    redis_port = run_command(
        f"gcloud redis instances describe {instance_name} --region={region} --format='value(port)' --project={project_id}",
        capture_output=True
    )
    
    return {
        "host": redis_host,
        "port": redis_port,
        "url": f"redis://{redis_host}:{redis_port}"
    }


def setup_storage_bucket(project_id: str) -> str:
    """Create Cloud Storage bucket."""
    print_header("Setting up Cloud Storage")
    
    bucket_name = f"{project_id}-roadtrip-assets"
    
    # Check if bucket exists
    existing = run_command(f"gsutil ls gs://{bucket_name}", capture_output=True)
    
    if not existing:
        print_info(f"Creating storage bucket '{bucket_name}'...")
        run_command(f"gsutil mb -p {project_id} -c standard -l us-central1 gs://{bucket_name}")
        
        # Set CORS for web access
        cors_json = '''[
          {
            "origin": ["*"],
            "method": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "responseHeader": ["Content-Type"],
            "maxAgeSeconds": 3600
          }
        ]'''
        
        with open('cors.json', 'w') as f:
            f.write(cors_json)
        
        run_command(f"gsutil cors set cors.json gs://{bucket_name}")
        os.remove('cors.json')
        
        print_success(f"Storage bucket created: {bucket_name}")
    else:
        print_info(f"Using existing bucket: {bucket_name}")
    
    return bucket_name


def create_env_file(config: Dict[str, Any]):
    """Create .env file with all configuration."""
    print_header("Creating Environment Configuration")
    
    env_content = f"""# AI Road Trip Storyteller Configuration
# Generated by setup_infrastructure.py

# Core Configuration
ENVIRONMENT=production
APP_VERSION=1.0.0
SECRET_KEY={secrets.token_urlsafe(32)}
JWT_SECRET_KEY={secrets.token_urlsafe(32)}

# Database Configuration
DATABASE_URL=postgresql://{config['db']['user']}:{config['db']['password']}@/{config['db']['database']}?host=/cloudsql/{config['db']['connection_name']}
DB_USER={config['db']['user']}
DB_PASSWORD={config['db']['password']}
DB_NAME={config['db']['database']}
CLOUD_SQL_CONNECTION_NAME={config['db']['connection_name']}

# Redis Configuration
REDIS_URL={config['redis']['url']}
REDIS_HOST={config['redis']['host']}
REDIS_PORT={config['redis']['port']}

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS={config['service_account_key']}
GCP_PROJECT_ID={config['project_id']}
GOOGLE_AI_PROJECT_ID={config['project_id']}
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME={config['bucket_name']}

# API Keys (You need to add these manually)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
TICKETMASTER_API_KEY=your-ticketmaster-api-key
OPENWEATHERMAP_API_KEY=your-openweathermap-api-key
RECREATION_GOV_API_KEY=your-recreation-gov-api-key

# Optional API Keys
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
CHARGEPOINT_API_KEY=your-chargepoint-api-key
VIATOR_API_KEY=your-viator-api-key
RESY_API_KEY=your-resy-api-key
OPENTABLE_API_KEY=your-opentable-api-key
SHELL_RECHARGE_API_KEY=your-shell-recharge-api-key

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
CORS_ORIGINS=["https://your-domain.com"]
TEST_MODE=live
"""
    
    # Backup existing .env if it exists
    if os.path.exists('.env'):
        backup_name = f".env.backup.{int(time.time())}"
        os.rename('.env', backup_name)
        print_info(f"Backed up existing .env to {backup_name}")
    
    # Write new .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print_success(".env file created")
    print_warning("Please add your API keys to the .env file")


def setup_kubernetes_cluster(project_id: str) -> str:
    """Set up GKE cluster."""
    print_header("Setting up Kubernetes Cluster")
    
    cluster_name = "roadtrip-cluster"
    zone = "us-central1-a"
    
    # Check if cluster exists
    existing = run_command(
        f"gcloud container clusters describe {cluster_name} --zone={zone} --project={project_id}",
        capture_output=True
    )
    
    if not existing:
        print_info("Creating GKE cluster (this will take 10-15 minutes)...")
        run_command(f"""gcloud container clusters create {cluster_name} \
            --zone={zone} \
            --num-nodes=3 \
            --machine-type=e2-standard-4 \
            --enable-autoscaling \
            --min-nodes=2 \
            --max-nodes=10 \
            --enable-autorepair \
            --enable-autoupgrade \
            --release-channel=regular \
            --network=default \
            --project={project_id}""")
        print_success("Kubernetes cluster created")
    else:
        print_info("Using existing cluster")
    
    # Get cluster credentials
    print_info("Getting cluster credentials...")
    run_command(f"gcloud container clusters get-credentials {cluster_name} --zone={zone} --project={project_id}")
    
    return cluster_name


def deploy_application():
    """Deploy the application to the cluster."""
    print_header("Deploying Application")
    
    # Build and push Docker image
    print_info("Building Docker image...")
    project_id = run_command("gcloud config get-value project", capture_output=True)
    image_tag = f"gcr.io/{project_id}/roadtrip-app:latest"
    
    run_command(f"docker build -t {image_tag} -f Dockerfile .")
    
    print_info("Pushing image to Container Registry...")
    run_command(f"docker push {image_tag}")
    
    # Apply Kubernetes manifests
    print_info("Deploying to Kubernetes...")
    
    # Create namespace
    run_command("kubectl create namespace roadtrip --dry-run=client -o yaml | kubectl apply -f -")
    
    # Create secrets from .env
    run_command("kubectl create secret generic app-secrets --from-env-file=.env -n roadtrip --dry-run=client -o yaml | kubectl apply -f -")
    
    # Deploy application
    if os.path.exists("infrastructure/k8s"):
        run_command("kubectl apply -f infrastructure/k8s/ -n roadtrip")
        print_success("Application deployed to Kubernetes")
    else:
        print_warning("Kubernetes manifests not found. Please deploy manually.")


def print_next_steps(config: Dict[str, Any]):
    """Print next steps for the user."""
    print_header("Setup Complete! Next Steps")
    
    print(f"""
1. {Colors.BOLD}Add API Keys{Colors.END}
   Edit the .env file and add your API keys:
   - Google Maps API Key
   - Ticketmaster API Key
   - OpenWeatherMap API Key
   - Recreation.gov API Key
   
2. {Colors.BOLD}Enable Google Maps APIs{Colors.END}
   Go to: https://console.cloud.google.com/apis/library
   Enable these APIs for your Maps API key:
   - Maps JavaScript API
   - Places API
   - Geocoding API
   - Directions API
   
3. {Colors.BOLD}Run Database Migrations{Colors.END}
   {Colors.YELLOW}alembic upgrade head{Colors.END}
   
4. {Colors.BOLD}Deploy the Application{Colors.END}
   {Colors.YELLOW}./deploy.sh{Colors.END}
   
5. {Colors.BOLD}Access Monitoring{Colors.END}
   - Health Check: https://your-domain.com/health/detailed
   - Metrics: https://your-domain.com/metrics
   
6. {Colors.BOLD}Configure Domain{Colors.END}
   Update CORS_ORIGINS in .env with your domain

{Colors.BOLD}Important URLs:{Colors.END}
- GCP Console: https://console.cloud.google.com/home/dashboard?project={config['project_id']}
- Kubernetes: {Colors.YELLOW}kubectl get all -n roadtrip{Colors.END}
- Logs: {Colors.YELLOW}kubectl logs -f deployment/roadtrip-api -n roadtrip{Colors.END}

{Colors.GREEN}Your infrastructure is ready!{Colors.END}
""")


def main():
    """Main setup flow."""
    print_header("AI Road Trip Storyteller - Infrastructure Setup")
    
    # Check prerequisites
    check_prerequisites()
    
    # Setup GCP project
    project_id = setup_gcp_project()
    
    # Enable APIs
    enable_apis(project_id)
    
    # Create service account
    service_account_key = create_service_account(project_id)
    
    # Setup Cloud SQL
    db_config = setup_cloud_sql(project_id)
    
    # Setup Redis
    redis_config = setup_redis(project_id)
    
    # Setup Storage
    bucket_name = setup_storage_bucket(project_id)
    
    # Create environment configuration
    config = {
        "project_id": project_id,
        "service_account_key": service_account_key,
        "db": db_config,
        "redis": redis_config,
        "bucket_name": bucket_name
    }
    
    create_env_file(config)
    
    # Optional: Setup Kubernetes
    deploy_k8s = input("\nDeploy to Kubernetes? (y/N): ").lower()
    if deploy_k8s == 'y':
        setup_kubernetes_cluster(project_id)
        deploy_application()
    
    # Print next steps
    print_next_steps(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nSetup failed: {e}")
        sys.exit(1)