#!/bin/bash
# Deploy the fixed backend with Vertex AI instead of Generative Language API

set -e

echo "[DEPLOY] Deploying Vertex AI fix to production"
echo "=============================================="

# Variables
PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"
SERVICE_ACCOUNT="roadtrip-mvp-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if we're in the backend directory
if [ ! -f "mvp_health.py" ]; then
    echo "[ERROR] Must run from backend directory"
    exit 1
fi

# Verify the fix is in place
echo "[CHECK] Verifying Vertex AI implementation..."
if grep -q "google.generativeai" mvp_health.py; then
    echo "[ERROR] mvp_health.py still contains google.generativeai!"
    echo "The fix was not applied correctly."
    exit 1
fi

if ! grep -q "vertexai" mvp_health.py; then
    echo "[ERROR] mvp_health.py does not import vertexai!"
    echo "The fix was not applied correctly."
    exit 1
fi

echo "[CHECK] Vertex AI implementation verified!"

# Create minimal Dockerfile for MVP
echo "[BUILD] Creating optimized Dockerfile..."
cat > Dockerfile.mvp << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only essential files
COPY mvp_health.py .
COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the MVP health app
CMD ["python", "mvp_health.py"]
EOF

# Build the image
echo "[BUILD] Building Docker image..."
docker build -f Dockerfile.mvp -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:vertex-fix .

# Push to Container Registry
echo "[PUSH] Pushing image to GCR..."
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:vertex-fix

# Deploy to Cloud Run
echo "[DEPLOY] Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:vertex-fix \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars "GOOGLE_AI_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GOOGLE_AI_LOCATION=${REGION}" \
    --set-env-vars "GOOGLE_AI_MODEL=gemini-1.5-flash" \
    --set-env-vars "USE_VERTEX_AI=true" \
    --set-env-vars "ENVIRONMENT=production" \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 10

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "[SUCCESS] Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "[TEST] Testing the health endpoint..."
curl -s "${SERVICE_URL}/health" | python -m json.tool

echo ""
echo "[INFO] The Vertex AI fix has been deployed successfully!"
echo "The backend should no longer return 403 errors for AI requests."