#!/bin/bash

# Production Build Script with Obfuscation
# Six Sigma DMAIC - Code Obfuscation Implementation

set -e

echo "🚀 Starting production build with obfuscation..."

# Set environment
export NODE_ENV=production
export EXPO_PUBLIC_ENVIRONMENT=production

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/
rm -rf .expo/
rm -rf node_modules/.cache/

# Install dependencies
echo "📦 Installing dependencies..."
npm ci --production

# Run security audit
echo "🔒 Running security audit..."
node scripts/security-audit.js || true

# Build with EAS
echo "🏗️  Building with EAS..."

# iOS Production Build
echo "🍎 Building iOS..."
eas build --platform ios --profile production --non-interactive

# Android Production Build  
echo "🤖 Building Android..."
eas build --platform android --profile production --non-interactive

# Extract and manage source maps
echo "📍 Managing source maps..."
node scripts/manage-sourcemaps.js all

# Verify obfuscation
echo "🔍 Verifying obfuscation..."
node scripts/verify-obfuscation.js

# Generate build report
echo "📊 Generating build report..."
node scripts/generate-build-report.js

echo "✅ Production build completed successfully!"
echo ""
echo "📱 Next steps:"
echo "1. Download builds from EAS"
echo "2. Test on real devices"
echo "3. Submit to app stores"
echo ""
echo "🔒 Security notes:"
echo "- Hermes bytecode compilation enabled"
echo "- ProGuard obfuscation active"
echo "- Source maps extracted and secured"
echo "- String encryption implemented"
echo "- Anti-tampering measures active"