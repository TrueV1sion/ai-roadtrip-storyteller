#!/bin/bash
STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
    --region=us-central1 --format="value(status.url)" --project=roadtrip-460720)

echo "Staging Environment Status:"
echo "=========================="
echo "URL: $STAGING_URL"
echo ""
echo "Health Check:"
curl -s "$STAGING_URL/health" | python3 -m json.tool
echo ""
echo "Root Endpoint:"
curl -s "$STAGING_URL/" | python3 -m json.tool
