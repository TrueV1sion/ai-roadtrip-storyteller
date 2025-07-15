#!/bin/bash
# Deploy clean version with only Vertex AI (no Generative Language API)

set -e

echo "🧹 Cleaning up problematic files..."
# Remove any main_*.py files that might use google.generativeai
rm -f app/main_minimal.py
rm -f app/main_mvp.py
rm -f app/main_enhanced.py
rm -f app/main_production.py
rm -f app/main_performance.py

echo "✅ Verifying no google.generativeai usage..."
if grep -r "google\.generativeai\|import genai" app/ --include="*.py" | grep -v __pycache__; then
    echo "❌ ERROR: Found google.generativeai usage in files above!"
    exit 1
else
    echo "✅ No google.generativeai usage found"
fi

echo "📋 Verifying Vertex AI usage..."
if grep -r "vertexai\|UnifiedAIClient" app/ --include="*.py" | grep -v __pycache__ | head -5; then
    echo "✅ Vertex AI is being used"
else
    echo "⚠️  WARNING: Could not find Vertex AI usage"
fi

echo "🔍 Checking main.py exists..."
if [ ! -f "app/main.py" ]; then
    echo "❌ ERROR: app/main.py not found!"
    exit 1
else
    echo "✅ app/main.py exists"
fi

echo "🔍 Verifying Dockerfile configuration..."
if grep -q "app.main:app" Dockerfile; then
    echo "✅ Dockerfile correctly configured to use app.main:app"
else
    echo "❌ ERROR: Dockerfile not configured correctly!"
    exit 1
fi

# Set your project ID
PROJECT_ID="gen-lang-client-0492208227"
SERVICE_NAME="roadtrip-backend"
REGION="us-central1"

echo "🚀 Building and deploying to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"

# Build and deploy
gcloud run deploy $SERVICE_NAME \
    --source . \
    --project $PROJECT_ID \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_AI_PROJECT_ID=$PROJECT_ID,GOOGLE_AI_LOCATION=$REGION,GOOGLE_AI_MODEL=gemini-1.5-flash" \
    --service-account "vertex-ai-user@$PROJECT_ID.iam.gserviceaccount.com" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10

echo "✅ Deployment complete!"
echo ""
echo "🧪 Testing the deployment..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"

# Test health endpoint
echo "Testing health endpoint..."
curl -s "$SERVICE_URL/health" | jq .

# Test voice assistant endpoint
echo ""
echo "Testing voice assistant endpoint..."
curl -X POST "$SERVICE_URL/api/voice-assistant/interact" \
    -H "Content-Type: application/json" \
    -d '{
        "user_input": "Navigate to Golden Gate Bridge",
        "context": {
            "origin": "San Francisco, CA"
        }
    }' | jq .

echo ""
echo "🎉 Deployment and testing complete!"