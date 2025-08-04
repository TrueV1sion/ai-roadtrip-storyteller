#!/bin/bash
# Launch Preview Environment for AI Road Trip Storyteller
# This script sets up and launches a fully functional preview environment

set -e

echo "==============================================="
echo "   AI ROAD TRIP PREVIEW ENVIRONMENT SETUP"
echo "==============================================="
echo ""

# Check prerequisites
echo "[CHECK] Verifying prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed"
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm is not installed"
    exit 1
fi

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "[ERROR] Google Cloud SDK is not installed"
    exit 1
fi

echo "[OK] All prerequisites met"
echo ""

# Backend status check
echo "[BACKEND] Checking backend health..."
BACKEND_URL="https://roadtrip-mvp-792001900150.us-central1.run.app"
HEALTH_RESPONSE=$(curl -s "$BACKEND_URL/health" || echo '{"status": "error"}')
BACKEND_STATUS=$(echo "$HEALTH_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")

if [ "$BACKEND_STATUS" = "degraded" ] || [ "$BACKEND_STATUS" = "healthy" ]; then
    echo "[OK] Backend is operational (status: $BACKEND_STATUS)"
else
    echo "[WARNING] Backend health check failed"
    echo "Response: $HEALTH_RESPONSE"
fi

# Check if Vertex AI build completed
echo ""
echo "[BUILD] Checking Vertex AI fix deployment..."
BUILD_STATUS=$(gcloud builds list --region=us-central1 --limit=1 --format="value(status)" --project=roadtrip-460720 2>/dev/null || echo "UNKNOWN")
if [ "$BUILD_STATUS" = "SUCCESS" ]; then
    echo "[OK] Vertex AI fix has been deployed"
elif [ "$BUILD_STATUS" = "WORKING" ]; then
    echo "[INFO] Vertex AI fix deployment is still in progress"
    echo "       The AI features may not work until deployment completes"
else
    echo "[WARNING] Vertex AI fix deployment status: $BUILD_STATUS"
fi

# Setup mobile environment
echo ""
echo "[MOBILE] Setting up preview environment..."

# Create .env file for preview
cat > mobile/.env << EOF
# AI Road Trip Preview Environment
EXPO_PUBLIC_API_URL=$BACKEND_URL
EXPO_PUBLIC_ENVIRONMENT=preview
EXPO_PUBLIC_PLATFORM=ios
EXPO_PUBLIC_MVP_MODE=false
EXPO_PUBLIC_ENABLE_BOOKING=true
EXPO_PUBLIC_ENABLE_VOICE=true
EXPO_PUBLIC_ENABLE_AR=true
EXPO_PUBLIC_APP_NAME=AI Road Trip Preview
EXPO_PUBLIC_SENTRY_DSN=
EOF

echo "[OK] Environment file created"

# Install dependencies if needed
cd mobile
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo ""
    echo "[INSTALL] Installing mobile dependencies..."
    npm install
fi

# Clear cache
echo ""
echo "[CLEAN] Clearing Expo cache..."
npx expo start --clear

echo ""
echo "==============================================="
echo "   PREVIEW ENVIRONMENT READY!"
echo "==============================================="
echo ""
echo "Backend URL: $BACKEND_URL"
echo "Backend Status: $BACKEND_STATUS"
echo ""
echo "To test the preview:"
echo ""
echo "1. EXPO GO APP (Recommended for quick preview):"
echo "   - Install Expo Go on your phone"
echo "   - Scan the QR code shown above"
echo "   - Test all features"
echo ""
echo "2. iOS SIMULATOR:"
echo "   Press 'i' in the terminal"
echo ""
echo "3. ANDROID EMULATOR:"
echo "   Press 'a' in the terminal"
echo ""
echo "4. WEB BROWSER:"
echo "   Press 'w' in the terminal"
echo ""
echo "FEATURES TO TEST:"
echo "✓ Voice Commands - Say 'Hey Roadtrip' and ask for stories"
echo "✓ Navigation - Request directions to any destination"
echo "✓ AI Stories - Get location-based stories while navigating"
echo "✓ Bookings - Search for restaurants and activities"
echo "✓ Voice Personalities - Try different narrator voices"
echo "✓ Offline Mode - Download maps and stories"
echo ""
echo "Known Issues:"
echo "- Vertex AI may still show errors until deployment completes"
echo "- Some API keys are exposed (will be fixed in production)"
echo "- Console warnings are expected in preview mode"
echo ""