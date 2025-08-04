#!/bin/bash
# Quick fix for Vertex AI by updating environment variables only

echo "[QUICK FIX] Updating Vertex AI environment variables..."
echo "========================================="

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

# Update environment variables to force Vertex AI usage
echo "[UPDATE] Setting environment variables..."
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --update-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --update-env-vars="GOOGLE_AI_PROJECT_ID=$PROJECT_ID" \
  --update-env-vars="GOOGLE_AI_LOCATION=$REGION" \
  --update-env-vars="VERTEX_AI_LOCATION=$REGION" \
  --update-env-vars="USE_VERTEX_AI=true" \
  --update-env-vars="DISABLE_GEMINI_API_KEY=true" \
  --update-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account/key.json"

echo ""
echo "[WAIT] Waiting for changes to propagate..."
sleep 20

echo ""
echo "[TEST] Testing health endpoint..."
response=$(curl -s https://roadtrip-mvp-792001900150.us-central1.run.app/health)
echo "$response" | python -m json.tool || echo "$response"

echo ""
echo "[COMPLETE] Environment variables updated!"
echo ""
echo "Note: If still seeing generativelanguage API errors, the deployed code"
echo "may need to be updated to use Vertex AI instead of the Gemini API."