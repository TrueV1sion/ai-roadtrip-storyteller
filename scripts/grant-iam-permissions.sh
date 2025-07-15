#!/bin/bash
# Grant IAM permissions - CI/CD compatible
# Usage: ./grant-iam-permissions.sh [project-id] [service-account-email]

set -euo pipefail

# Configuration
PROJECT_ID="${1:-${GCP_PROJECT_ID:-roadtrip-460720}}"
SERVICE_ACCOUNT="${2:-${SERVICE_ACCOUNT:-roadtrip-staging-e6a9121e@${PROJECT_ID}.iam.gserviceaccount.com}}"

# Required roles
ROLES=(
    "roles/aiplatform.user"
    "roles/storage.objectAdmin"
    "roles/secretmanager.secretAccessor"
    "roles/cloudsql.client"
    "roles/redis.editor"
    "roles/texttospeech.client"
    "roles/speech.client"
    "roles/compute.networkUser"
    "roles/vpcaccess.user"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
    "roles/cloudtrace.agent"
)

# Disable interactive prompts
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

echo "Granting IAM permissions"
echo "Project: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"

# Grant each role
for role in "${ROLES[@]}"; do
    echo "Granting $role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="$role" \
        --quiet || echo "Failed to grant $role"
done

echo "IAM permissions grant completed"