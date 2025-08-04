#!/bin/bash

# Script to upload source maps to Sentry for production builds
# This should be run after building the app for production

set -e

echo "🚀 Uploading source maps to Sentry..."

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | xargs)
fi

# Check if SENTRY_AUTH_TOKEN is set
if [ -z "$SENTRY_AUTH_TOKEN" ]; then
  echo "❌ Error: SENTRY_AUTH_TOKEN is not set"
  echo "Please set SENTRY_AUTH_TOKEN in your .env file or as an environment variable"
  exit 1
fi

# Check if SENTRY_ORG is set
if [ -z "$SENTRY_ORG" ]; then
  echo "❌ Error: SENTRY_ORG is not set"
  echo "Please set SENTRY_ORG in your .env file or as an environment variable"
  exit 1
fi

# Check if SENTRY_PROJECT is set
if [ -z "$SENTRY_PROJECT" ]; then
  echo "❌ Error: SENTRY_PROJECT is not set"
  echo "Please set SENTRY_PROJECT in your .env file or as an environment variable"
  exit 1
fi

# Get version from package.json
VERSION=$(node -p "require('./package.json').version")
BUILD_NUMBER=$(date +%s)
RELEASE_NAME="roadtrip-mobile@$VERSION+$BUILD_NUMBER"

echo "📦 Release: $RELEASE_NAME"

# Install Sentry CLI if not installed
if ! command -v sentry-cli &> /dev/null; then
  echo "📥 Installing Sentry CLI..."
  npm install -g @sentry/cli
fi

# Create a new release
echo "📝 Creating release..."
sentry-cli releases new "$RELEASE_NAME"

# Upload source maps for iOS
if [ -d "ios/build" ]; then
  echo "📱 Uploading iOS source maps..."
  sentry-cli releases files "$RELEASE_NAME" upload-sourcemaps \
    --dist "$BUILD_NUMBER" \
    --strip-prefix /Users/distiller/project/ \
    --rewrite \
    ios/build/
fi

# Upload source maps for Android
if [ -d "android/app/build/intermediates/sourcemaps" ]; then
  echo "🤖 Uploading Android source maps..."
  sentry-cli releases files "$RELEASE_NAME" upload-sourcemaps \
    --dist "$BUILD_NUMBER" \
    --strip-prefix /Users/distiller/project/ \
    --rewrite \
    android/app/build/intermediates/sourcemaps/react/release/
fi

# Upload source maps for web (if applicable)
if [ -d "web-build" ]; then
  echo "🌐 Uploading web source maps..."
  sentry-cli releases files "$RELEASE_NAME" upload-sourcemaps \
    --dist "$BUILD_NUMBER" \
    --url-prefix "~/" \
    --rewrite \
    web-build/
fi

# Set commits (if in a git repository)
if [ -d ".git" ]; then
  echo "🔗 Associating commits..."
  sentry-cli releases set-commits "$RELEASE_NAME" --auto || true
fi

# Finalize the release
echo "✅ Finalizing release..."
sentry-cli releases finalize "$RELEASE_NAME"

# Optional: Mark release as deployed
echo "🚀 Marking release as deployed..."
sentry-cli releases deploys "$RELEASE_NAME" new -e production

echo "✨ Source maps uploaded successfully!"
echo "📊 View your release at: https://sentry.io/$SENTRY_ORG/$SENTRY_PROJECT/releases/$RELEASE_NAME/"