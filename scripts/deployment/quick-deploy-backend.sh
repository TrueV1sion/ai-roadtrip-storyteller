#!/bin/bash

# Quick deployment script for backend

set -e

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-backend-production"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building and deploying backend..."

# Build the image locally and push directly
cd backend
docker build -t ${IMAGE_NAME}:latest -f Dockerfile .
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --service-account roadtrip-mvp-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --concurrency 80 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --set-env-vars "ENVIRONMENT=production,APP_NAME=RoadTrip Backend,LOG_LEVEL=INFO,REDIS_ENABLED=true,CACHE_TTL=3600,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},VERTEX_AI_LOCATION=us-central1,MASTER_KEY_LOCATION=/app/keys/master.key,CORS_ALLOWED_ORIGINS=https://roadtrip-mvp-792001900150.us-central1.run.app;http://localhost:3000;http://localhost:19006" \
    --set-secrets "DATABASE_URL=database-url:latest,REDIS_URL=redis-url:latest,JWT_SECRET_KEY=jwt-secret-key:latest,JWT_REFRESH_SECRET_KEY=jwt-refresh-secret-key:latest,GOOGLE_MAPS_API_KEY=google-maps-api-key:latest,OPENWEATHER_API_KEY=openweather-api-key:latest,TICKETMASTER_API_KEY=ticketmaster-api-key:latest,OPENTABLE_API_KEY=opentable-api-key:latest,VIATOR_API_KEY=viator-api-key:latest,RECREATION_GOV_API_KEY=recreation-gov-api-key:latest,SPOTIFY_CLIENT_ID=spotify-client-id:latest,SPOTIFY_CLIENT_SECRET=spotify-client-secret:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest,TWILIO_FROM_PHONE=twilio-from-phone:latest,SENDGRID_API_KEY=sendgrid-api-key:latest,ENCRYPTION_KEY=encryption-key:latest"

echo "Deployment complete!"