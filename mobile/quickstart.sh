#!/bin/bash

# AI Road Trip - Quick Start Script for Test Drive
# This script sets up and launches the mobile app for testing

echo "🚗 AI Road Trip - Quick Start for Test Drive"
echo "=========================================="

# Check if we're in the mobile directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in the mobile directory. Please run from the mobile folder."
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists node; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is not installed. Please install npm"
    exit 1
fi

if ! command_exists expo; then
    echo "📦 Installing Expo CLI..."
    npm install -g expo-cli
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✅ Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp .env.example .env
    echo "📝 Please update .env with your configuration"
fi

# Clear caches
echo "🧹 Clearing caches..."
npx expo start -c &>/dev/null &
EXPO_PID=$!
sleep 5
kill $EXPO_PID 2>/dev/null

# Platform selection
echo ""
echo "📱 Select your platform:"
echo "1) iOS Simulator (Mac only)"
echo "2) Android Emulator"
echo "3) Physical Device (Expo Go)"
echo "4) Web Browser"
echo "5) Development Build (iOS)"
echo "6) Development Build (Android)"

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo "🍎 Starting iOS Simulator..."
        npm run ios
        ;;
    2)
        echo "🤖 Starting Android Emulator..."
        npm run android
        ;;
    3)
        echo "📱 Starting for Physical Device..."
        echo ""
        echo "⚠️  IMPORTANT: For physical device testing:"
        echo "1. Install Expo Go from App Store/Play Store"
        echo "2. Make sure your phone and computer are on the same network"
        echo "3. Update EXPO_PUBLIC_DEV_API_URL in .env with your computer's IP"
        echo ""
        echo "Your computer's IP addresses:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "  - " $2}'
        else
            ip addr | grep "inet " | grep -v 127.0.0.1 | awk '{print "  - " $2}' | cut -d'/' -f1
        fi
        echo ""
        read -p "Press Enter to continue..."
        npx expo start --tunnel
        ;;
    4)
        echo "🌐 Starting Web Browser..."
        npm run web
        ;;
    5)
        echo "🍎 Building for iOS Device..."
        echo "This requires EAS CLI and Apple Developer account"
        if ! command_exists eas; then
            echo "📦 Installing EAS CLI..."
            npm install -g eas-cli
        fi
        eas build --platform ios --profile development
        ;;
    6)
        echo "🤖 Building for Android Device..."
        echo "This requires EAS CLI"
        if ! command_exists eas; then
            echo "📦 Installing EAS CLI..."
            npm install -g eas-cli
        fi
        eas build --platform android --profile development
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Quick Start Complete!"
echo ""
echo "📝 Next Steps:"
echo "1. Make sure backend is deployed and accessible"
echo "2. Test voice commands: 'Hey Roadtrip, start navigation'"
echo "3. Grant location and microphone permissions when prompted"
echo "4. Try driving mode for the full experience"
echo ""
echo "🐛 Troubleshooting:"
echo "- If voice doesn't work: Rebuild with development profile (option 5 or 6)"
echo "- If backend connection fails: Check .env configuration"
echo "- If location fails: Check device settings for permissions"
echo ""
echo "Have a great test drive! 🚗✨"