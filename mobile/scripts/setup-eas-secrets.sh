#!/bin/bash

# EAS Secrets Setup Script
# Configures secure environment variables for production builds

set -e

echo "🔐 EAS Secrets Setup"
echo "==================="
echo ""
echo "This script will help you configure EAS secrets for production builds."
echo "Make sure you have the EAS CLI installed and are logged in."
echo ""

# Check if EAS CLI is installed
if ! command -v eas &> /dev/null; then
    echo "❌ EAS CLI not found. Please install it first:"
    echo "   npm install -g eas-cli"
    exit 1
fi

# Check if logged in
if ! eas whoami &> /dev/null; then
    echo "❌ Not logged in to EAS. Please run:"
    echo "   eas login"
    exit 1
fi

echo "Current EAS account:"
eas whoami
echo ""

# Function to create or update a secret
create_secret() {
    local name=$1
    local description=$2
    local required=$3
    
    echo ""
    echo "📝 $description"
    
    # Check if secret exists
    if eas secret:list | grep -q "$name"; then
        echo "Secret '$name' already exists."
        read -p "Do you want to update it? (y/n): " update
        if [[ $update == "y" ]]; then
            eas secret:delete "$name" --non-interactive || true
        else
            return
        fi
    fi
    
    if [[ $required == "required" ]]; then
        read -sp "Enter value for $name (required): " value
        echo ""
        
        if [[ -z "$value" ]]; then
            echo "❌ Value is required for $name"
            exit 1
        fi
    else
        read -sp "Enter value for $name (optional, press enter to skip): " value
        echo ""
        
        if [[ -z "$value" ]]; then
            echo "⚠️  Skipping $name"
            return
        fi
    fi
    
    # Create the secret
    eas secret:create --scope project --name "$name" --value "$value" --non-interactive
    echo "✅ Secret '$name' created successfully"
}

echo "Setting up production secrets..."
echo "================================"

# Required secrets
create_secret "SENTRY_DSN" "Sentry DSN for crash reporting (format: https://xxx@sentry.io/yyy)" "required"

# iOS App Store secrets
echo ""
echo "📱 iOS App Store Configuration"
echo "These are required for App Store submission:"

create_secret "APPLE_ID" "Your Apple ID email" "optional"
create_secret "ASC_APP_ID" "App Store Connect App ID" "optional"
create_secret "APPLE_TEAM_ID" "Apple Developer Team ID" "optional"

# Android Play Store secrets
echo ""
echo "🤖 Android Play Store Configuration"
echo "Required for Play Store submission:"

if [[ -f "./google-play-service-account.json" ]]; then
    echo "✅ Found google-play-service-account.json"
else
    echo "⚠️  google-play-service-account.json not found"
    echo "   Download it from Google Play Console and place in this directory"
fi

# List all secrets
echo ""
echo "📋 Current EAS Secrets:"
echo "======================="
eas secret:list

echo ""
echo "✅ EAS secrets setup complete!"
echo ""
echo "🔒 Security Notes:"
echo "- Secrets are encrypted and stored securely by Expo"
echo "- They are only available during the build process"
echo "- Never commit secret values to version control"
echo "- Use different values for staging vs production"
echo ""
echo "📝 Next Steps:"
echo "1. Run 'npm run validate:env' to verify configuration"
echo "2. Build with 'eas build --platform all --profile production'"
echo "3. Monitor builds at https://expo.dev/accounts/[your-account]/projects/roadtrip"