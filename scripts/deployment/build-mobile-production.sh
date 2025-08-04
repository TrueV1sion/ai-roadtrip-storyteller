#!/bin/bash
# Build and deploy mobile apps for production
# This script handles both iOS and Android builds with security hardening

set -euo pipefail

# Configuration
PLATFORM="${1:-all}"  # ios, android, or all
BUILD_TYPE="${2:-production}"  # production or preview

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}📱 Building Mobile Apps for Production${NC}"
echo -e "${BLUE}Platform: ${PLATFORM}${NC}"
echo -e "${BLUE}Build Type: ${BUILD_TYPE}${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    # Check if EAS CLI is installed
    if ! command -v eas &> /dev/null; then
        echo -e "${RED}❌ EAS CLI not found${NC}"
        echo "Install with: npm install -g eas-cli"
        exit 1
    fi
    
    # Check if in mobile directory
    if [ ! -f "package.json" ] || [ ! -f "app.config.js" ]; then
        echo -e "${RED}❌ Not in mobile directory${NC}"
        echo "Please cd to mobile/ directory"
        exit 1
    fi
    
    # Check environment variables
    if [ "$BUILD_TYPE" == "production" ]; then
        REQUIRED_VARS="SENTRY_DSN APPLE_ID ASC_APP_ID APPLE_TEAM_ID"
        for var in $REQUIRED_VARS; do
            if [ -z "${!var:-}" ]; then
                echo -e "${RED}❌ Missing required environment variable: $var${NC}"
                exit 1
            fi
        done
    fi
    
    echo -e "${GREEN}✅ Prerequisites checked${NC}"
}

# Clean console logs
remove_console_logs() {
    echo -e "${YELLOW}🧹 Removing console.log statements...${NC}"
    
    # Run the console log removal script
    if [ -f "../scripts/utilities/remove-console-logs.js" ]; then
        node ../scripts/utilities/remove-console-logs.js
    else
        # Inline removal using sed
        find src -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | \
        xargs sed -i.bak '/console\.\(log\|warn\|error\|info\|debug\)/d'
        
        # Remove backup files
        find src -name "*.bak" -delete
    fi
    
    echo -e "${GREEN}✅ Console logs removed${NC}"
}

# Run security audit
security_audit() {
    echo -e "${YELLOW}🔒 Running security audit...${NC}"
    
    # Check for hardcoded API keys
    echo "Checking for hardcoded API keys..."
    if grep -r "AIza\|AKIA\|api_key.*=.*['\"]" src/; then
        echo -e "${RED}❌ Found hardcoded API keys!${NC}"
        exit 1
    fi
    
    # Check for insecure storage usage
    echo "Checking for insecure storage..."
    if grep -r "AsyncStorage\." src/ | grep -v "SecureStore"; then
        echo -e "${YELLOW}⚠️  Found AsyncStorage usage - should use SecureStore${NC}"
    fi
    
    # Run npm audit
    echo "Running npm audit..."
    npm audit --production
    
    echo -e "${GREEN}✅ Security audit completed${NC}"
}

# Update version numbers
update_versions() {
    echo -e "${YELLOW}📝 Updating version numbers...${NC}"
    
    # Get current version from package.json
    CURRENT_VERSION=$(node -p "require('./package.json').version")
    
    # Increment patch version
    IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
    PATCH=$((VERSION_PARTS[2] + 1))
    NEW_VERSION="${VERSION_PARTS[0]}.${VERSION_PARTS[1]}.$PATCH"
    
    # Update package.json
    npm version $NEW_VERSION --no-git-tag-version
    
    # Update app.config.js
    sed -i "s/version: '.*'/version: '$NEW_VERSION'/" app.config.js
    
    echo -e "${GREEN}✅ Version updated to $NEW_VERSION${NC}"
}

# Build iOS app
build_ios() {
    echo -e "${PURPLE}🍎 Building iOS app...${NC}"
    
    # Clean build cache
    echo "Cleaning build cache..."
    rm -rf ios/build
    
    # Install pods
    echo "Installing CocoaPods..."
    cd ios && pod install && cd ..
    
    # Build with EAS
    echo "Starting EAS build..."
    eas build --platform ios --profile $BUILD_TYPE --non-interactive
    
    echo -e "${GREEN}✅ iOS build submitted${NC}"
}

# Build Android app
build_android() {
    echo -e "${PURPLE}🤖 Building Android app...${NC}"
    
    # Clean build cache
    echo "Cleaning build cache..."
    rm -rf android/app/build
    
    # Build with EAS
    echo "Starting EAS build..."
    eas build --platform android --profile $BUILD_TYPE --non-interactive
    
    echo -e "${GREEN}✅ Android build submitted${NC}"
}

# Submit to app stores
submit_to_stores() {
    echo -e "${YELLOW}📤 Submitting to app stores...${NC}"
    
    if [ "$PLATFORM" == "ios" ] || [ "$PLATFORM" == "all" ]; then
        echo -e "${PURPLE}Submitting to App Store Connect...${NC}"
        eas submit --platform ios --latest --non-interactive
    fi
    
    if [ "$PLATFORM" == "android" ] || [ "$PLATFORM" == "all" ]; then
        echo -e "${PURPLE}Submitting to Google Play Console...${NC}"
        eas submit --platform android --latest --non-interactive
    fi
    
    echo -e "${GREEN}✅ Apps submitted to stores${NC}"
}

# Main execution
main() {
    check_prerequisites
    
    if [ "$BUILD_TYPE" == "production" ]; then
        remove_console_logs
        security_audit
        update_versions
    fi
    
    # Build based on platform
    case "$PLATFORM" in
        ios)
            build_ios
            ;;
        android)
            build_android
            ;;
        all)
            build_ios
            build_android
            ;;
        *)
            echo -e "${RED}❌ Invalid platform: $PLATFORM${NC}"
            echo "Valid platforms: ios, android, all"
            exit 1
            ;;
    esac
    
    # Submit if production build
    if [ "$BUILD_TYPE" == "production" ]; then
        read -p "Submit to app stores? (yes/no): " submit
        if [ "$submit" == "yes" ]; then
            submit_to_stores
        fi
    fi
    
    echo -e "${GREEN}🎉 Mobile build process complete!${NC}"
    echo -e "${BLUE}Monitor build progress at: https://expo.dev${NC}"
}

# Run main function
main