#!/usr/bin/env python3
"""
Setup automated credential rotation for AI Road Trip Storyteller
Configures Cloud Scheduler jobs for regular rotation
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Dict, List

PROJECT_ID = "roadtrip-460720"
REGION = "us-central1"

# Rotation schedules
ROTATION_SCHEDULES = {
    "internal-secrets": {
        "description": "Rotate internal secrets (JWT, CSRF, encryption keys)",
        "schedule": "0 2 * */3 *",  # Every 3 months at 2 AM
        "secrets": [
            "roadtrip-jwt-secret",
            "roadtrip-csrf-secret",
            "roadtrip-secret-key",
            "roadtrip-encryption-key"
        ]
    },
    "database-credentials": {
        "description": "Rotate database passwords",
        "schedule": "0 3 1 */6 *",  # Every 6 months on 1st at 3 AM
        "secrets": [
            "roadtrip-database-password",
            "roadtrip-redis-password"
        ]
    },
    "api-keys-check": {
        "description": "Check API keys for rotation (manual process)",
        "schedule": "0 9 1 * *",  # Monthly on 1st at 9 AM
        "secrets": [
            "roadtrip-google-maps-key",
            "roadtrip-ticketmaster-key",
            "roadtrip-openweather-key"
        ]
    }
}

def create_cloud_function():
    """Create Cloud Function for automated rotation"""
    
    function_code = '''import os
import json
import secrets
from datetime import datetime
from google.cloud import secretmanager
from google.cloud import logging

# Initialize clients
secret_client = secretmanager.SecretManagerServiceClient()
logging_client = logging.Client()
logger = logging_client.logger("credential-rotation")

def rotate_secret(request):
    """Cloud Function to rotate secrets"""
    
    request_json = request.get_json()
    secret_ids = request_json.get("secrets", [])
    project_id = os.environ.get("PROJECT_ID", "roadtrip-460720")
    
    results = {"rotated": [], "failed": [], "skipped": []}
    
    for secret_id in secret_ids:
        try:
            # Check if it's an internal secret that can be auto-generated
            if any(keyword in secret_id for keyword in ["jwt", "csrf", "encryption", "secret-key"]):
                # Generate new secret value
                new_value = secrets.token_urlsafe(64)
                
                # Add new version
                parent = f"projects/{project_id}/secrets/{secret_id}"
                response = secret_client.add_secret_version(
                    request={
                        "parent": parent,
                        "payload": {"data": new_value.encode("UTF-8")}
                    }
                )
                
                # Update labels
                secret_client.update_secret(
                    request={
                        "secret": {
                            "name": parent,
                            "labels": {
                                "last-rotation": str(int(datetime.now().timestamp())),
                                "rotation-type": "automated"
                            }
                        },
                        "update_mask": {"paths": ["labels"]}
                    }
                )
                
                results["rotated"].append(secret_id)
                logger.log_text(f"Successfully rotated {secret_id}", severity="INFO")
                
            else:
                # External API keys need manual rotation
                results["skipped"].append(secret_id)
                logger.log_text(f"Skipped {secret_id} - requires manual rotation", severity="WARNING")
                
        except Exception as e:
            results["failed"].append({"secret": secret_id, "error": str(e)})
            logger.log_text(f"Failed to rotate {secret_id}: {str(e)}", severity="ERROR")
    
    # Trigger service restart if any secrets were rotated
    if results["rotated"]:
        try:
            # Update Cloud Run service to pick up new secrets
            import subprocess
            subprocess.run([
                "gcloud", "run", "services", "update", "roadtrip-api",
                "--region", "us-central1",
                "--project", project_id,
                "--no-traffic"
            ], check=True)
            logger.log_text("Triggered service restart", severity="INFO")
        except Exception as e:
            logger.log_text(f"Failed to restart service: {str(e)}", severity="ERROR")
    
    return results
'''
    
    # Write function code
    os.makedirs("functions/credential-rotation", exist_ok=True)
    with open("functions/credential-rotation/main.py", "w") as f:
        f.write(function_code)
    
    # Create requirements.txt
    requirements = """google-cloud-secret-manager==2.16.0
google-cloud-logging==3.5.0
"""
    
    with open("functions/credential-rotation/requirements.txt", "w") as f:
        f.write(requirements)
    
    print("Created Cloud Function code")

def deploy_cloud_function():
    """Deploy the rotation Cloud Function"""
    print("Deploying Cloud Function for credential rotation...")
    
    cmd = [
        "gcloud", "functions", "deploy", "credential-rotation",
        "--runtime", "python39",
        "--trigger-http",
        "--entry-point", "rotate_secret",
        "--source", "functions/credential-rotation",
        "--region", REGION,
        "--project", PROJECT_ID,
        "--set-env-vars", f"PROJECT_ID={PROJECT_ID}",
        "--service-account", f"credential-rotation@{PROJECT_ID}.iam.gserviceaccount.com",
        "--allow-unauthenticated"  # Will be secured by Cloud Scheduler
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Cloud Function deployed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy Cloud Function: {e}")
        return False

def create_scheduler_jobs():
    """Create Cloud Scheduler jobs for rotation"""
    print("\nCreating Cloud Scheduler jobs...")
    
    # Get Cloud Function URL
    function_url = f"https://{REGION}-{PROJECT_ID}.cloudfunctions.net/credential-rotation"
    
    for job_name, config in ROTATION_SCHEDULES.items():
        print(f"\nCreating job: {job_name}")
        
        # Create job
        cmd = [
            "gcloud", "scheduler", "jobs", "create", "http",
            f"rotate-{job_name}",
            "--location", REGION,
            "--schedule", config["schedule"],
            "--uri", function_url,
            "--http-method", "POST",
            "--headers", "Content-Type=application/json",
            "--message-body", json.dumps({"secrets": config["secrets"]}),
            "--description", config["description"],
            "--project", PROJECT_ID
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Created scheduler job: rotate-{job_name}")
        except subprocess.CalledProcessError:
            # Job might already exist, try updating
            cmd[3] = "update"
            try:
                subprocess.run(cmd, check=True)
                print(f"✅ Updated scheduler job: rotate-{job_name}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to create/update job: {e}")

def create_rotation_alerts():
    """Create alerts for rotation failures"""
    print("\nCreating monitoring alerts...")
    
    alert_config = {
        "displayName": "Credential Rotation Failure",
        "conditions": [{
            "displayName": "Cloud Function errors",
            "conditionThreshold": {
                "filter": f'resource.type="cloud_function" '
                         f'resource.labels.function_name="credential-rotation" '
                         f'metric.type="logging.googleapis.com/log_entry_count" '
                         f'severity="ERROR"',
                "comparison": "COMPARISON_GT",
                "thresholdValue": 0,
                "duration": "60s"
            }
        }],
        "notificationChannels": [],  # Add your notification channels
        "alertStrategy": {
            "autoClose": "1800s"
        }
    }
    
    # Save alert configuration
    with open("monitoring/alerts/credential-rotation-alert.json", "w") as f:
        json.dump(alert_config, f, indent=2)
    
    print("✅ Alert configuration created")

def create_rotation_dashboard():
    """Create a monitoring dashboard for credential rotation"""
    dashboard_config = {
        "displayName": "Credential Rotation Dashboard",
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                {
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Rotation Success Rate",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/credential/rotation_success"',
                                    "aggregation": {
                                        "alignmentPeriod": "3600s",
                                        "perSeriesAligner": "ALIGN_RATE"
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "xPos": 6,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Days Since Last Rotation",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/credential/age_days"',
                                    "aggregation": {
                                        "alignmentPeriod": "3600s",
                                        "perSeriesAligner": "ALIGN_MAX"
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "yPos": 4,
                    "width": 12,
                    "height": 4,
                    "widget": {
                        "title": "Rotation History",
                        "xyChart": {
                            "dataSets": [{
                                "timeSeriesQuery": {
                                    "timeSeriesFilter": {
                                        "filter": 'metric.type="logging.googleapis.com/log_entry_count" '
                                                 'resource.type="cloud_function" '
                                                 'resource.labels.function_name="credential-rotation"'
                                    }
                                }
                            }]
                        }
                    }
                }
            ]
        }
    }
    
    # Save dashboard configuration
    os.makedirs("monitoring/dashboards", exist_ok=True)
    with open("monitoring/dashboards/credential-rotation-dashboard.json", "w") as f:
        json.dump(dashboard_config, f, indent=2)
    
    print("✅ Dashboard configuration created")

def create_rollback_procedures():
    """Create rollback procedures for failed rotations"""
    rollback_script = '''#!/bin/bash
#
# Rollback procedure for failed credential rotation
#

set -euo pipefail

PROJECT_ID="${1:-roadtrip-460720}"
SECRET_ID="${2:-}"
VERSION="${3:-}"

if [[ -z "$SECRET_ID" ]]; then
    echo "Usage: $0 [PROJECT_ID] SECRET_ID [VERSION]"
    echo "Example: $0 roadtrip-460720 roadtrip-jwt-secret 2"
    exit 1
fi

echo "Rolling back secret: $SECRET_ID to version: ${VERSION:-previous}"

# If no version specified, get the second-to-latest
if [[ -z "$VERSION" ]]; then
    VERSION=$(gcloud secrets versions list "$SECRET_ID" \\
        --project="$PROJECT_ID" \\
        --format="value(name)" \\
        --filter="state:ENABLED" \\
        --sort-by="~createTime" \\
        | head -n 2 | tail -n 1)
fi

echo "Target version: $VERSION"

# Disable current version
CURRENT=$(gcloud secrets versions list "$SECRET_ID" \\
    --project="$PROJECT_ID" \\
    --format="value(name)" \\
    --filter="state:ENABLED" \\
    --sort-by="~createTime" \\
    | head -n 1)

echo "Disabling current version: $CURRENT"
gcloud secrets versions disable "$CURRENT" \\
    --secret="$SECRET_ID" \\
    --project="$PROJECT_ID"

# Enable target version
echo "Enabling version: $VERSION"
gcloud secrets versions enable "$VERSION" \\
    --secret="$SECRET_ID" \\
    --project="$PROJECT_ID"

# Update service
echo "Restarting service..."
gcloud run services update roadtrip-api \\
    --region=us-central1 \\
    --project="$PROJECT_ID" \\
    --no-traffic

echo "Rollback complete!"
echo "Verify service health: https://api.roadtripstoryteller.com/health"
'''
    
    with open("scripts/security/rollback_credential.sh", "w") as f:
        f.write(rollback_script)
    os.chmod("scripts/security/rollback_credential.sh", 0o755)
    
    print("✅ Rollback procedures created")

def main():
    """Setup automated credential rotation"""
    print("Setting up Automated Credential Rotation")
    print("=" * 80)
    
    # Create service account for rotation
    print("\n1. Creating service account...")
    try:
        subprocess.run([
            "gcloud", "iam", "service-accounts", "create",
            "credential-rotation",
            "--display-name", "Credential Rotation Service",
            "--project", PROJECT_ID
        ], check=True)
        print("✅ Service account created")
    except Exception as e:
        print("⏭️  Service account already exists")
    
    # Grant necessary permissions
    print("\n2. Granting permissions...")
    sa_email = f"credential-rotation@{PROJECT_ID}.iam.gserviceaccount.com"
    
    roles = [
        "roles/secretmanager.admin",
        "roles/cloudfunctions.invoker",
        "roles/run.admin",
        "roles/logging.logWriter"
    ]
    
    for role in roles:
        try:
            subprocess.run([
                "gcloud", "projects", "add-iam-policy-binding",
                PROJECT_ID,
                f"--member=serviceAccount:{sa_email}",
                f"--role={role}"
            ], check=True, capture_output=True)
            print(f"✅ Granted {role}")
        except Exception as e:
            print(f"⏭️  {role} already granted")
    
    # Create Cloud Function
    print("\n3. Creating Cloud Function...")
    create_cloud_function()
    
    # Deploy Cloud Function
    if deploy_cloud_function():
        # Create scheduler jobs
        create_scheduler_jobs()
    
    # Create monitoring
    print("\n4. Setting up monitoring...")
    create_rotation_alerts()
    create_rotation_dashboard()
    
    # Create rollback procedures
    print("\n5. Creating rollback procedures...")
    create_rollback_procedures()
    
    print("\n" + "=" * 80)
    print("AUTOMATED ROTATION SETUP COMPLETE")
    print("=" * 80)
    print("\nRotation Schedule:")
    for job, config in ROTATION_SCHEDULES.items():
        print(f"  {job}: {config['schedule']} - {config['description']}")
    
    print("\nNext Steps:")
    print("1. Test rotation: gcloud scheduler jobs run rotate-internal-secrets --location=us-central1")
    print("2. View logs: gcloud logging read 'resource.labels.function_name=\"credential-rotation\"'")
    print("3. Monitor dashboard: Console > Monitoring > Dashboards > Credential Rotation")
    print("4. Set up notification channels for alerts")

if __name__ == "__main__":
    main()