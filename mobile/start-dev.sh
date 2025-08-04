#!/bin/bash
# Simple Expo startup script with fixes

echo "🚀 Starting AI Road Trip Mobile App..."
echo "===================================="

# Set environment variables
export EXPO_PUBLIC_API_URL=http://localhost:8000
export NODE_OPTIONS="--max-old-space-size=4096"

# Clear caches
echo "Clearing caches..."
rm -rf .expo node_modules/.cache

# Start Expo with specific options
echo "Starting Expo..."
npx expo start --tunnel --clear

echo ""
echo "📱 To view the app:"
echo "  1. Install Expo Go on your phone"
echo "  2. Scan the QR code above"
echo "  3. Or press 'w' for web browser"