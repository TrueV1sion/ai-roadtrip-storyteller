# Production Environment Configuration Guide

## Overview

This guide documents the secure production environment configuration for the RoadTrip AI Storyteller mobile app. All sensitive API keys have been removed from the client and are managed through backend proxy endpoints.

## Environment Variables Structure

### 1. Client-Safe Variables (`.env.production`)

These variables are safe to expose in the mobile app:

```bash
# Backend API Configuration
EXPO_PUBLIC_API_URL=https://roadtrip-mvp-792001900150.us-central1.run.app
EXPO_PUBLIC_ENVIRONMENT=production

# Feature Flags
EXPO_PUBLIC_MVP_MODE=false
EXPO_PUBLIC_ENABLE_BOOKING=true
EXPO_PUBLIC_ENABLE_VOICE=true
EXPO_PUBLIC_ENABLE_AR=true
EXPO_PUBLIC_ENABLE_GAMES=true
EXPO_PUBLIC_ENABLE_MUSIC=true
EXPO_PUBLIC_ENABLE_SOCIAL=true

# App Configuration
EXPO_PUBLIC_APP_NAME=AI Road Trip Storyteller
EXPO_PUBLIC_APP_VERSION=1.0.0

# Monitoring (client-safe DSN only)
EXPO_PUBLIC_SENTRY_DSN=https://your-public-dsn@sentry.io/project-id
```

### 2. Backend-Only Variables (Never Exposed to Client)

These are configured in Google Secret Manager for the backend:

```bash
# AI Services
VERTEX_AI_PROJECT=roadtrip-mvp
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Third-Party APIs (Backend Proxy)
GOOGLE_MAPS_API_KEY=AIza...
OPENWEATHER_API_KEY=abc123...
TICKETMASTER_API_KEY=xyz789...
OPENTABLE_API_KEY=def456...
RECREATION_GOV_API_KEY=ghi789...
VIATOR_API_KEY=jkl012...
SPOTIFY_CLIENT_ID=mno345...
SPOTIFY_CLIENT_SECRET=pqr678...

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_REFRESH_SECRET_KEY=your-refresh-secret

# Monitoring (Backend)
SENTRY_AUTH_TOKEN=your-auth-token
```

## EAS Build Configuration

### Updated `eas.json` for Production

```json
{
  "build": {
    "production": {
      "distribution": "store",
      "ios": {
        "buildConfiguration": "Release",
        "bundleIdentifier": "com.roadtrip.app",
        "infoPlist": {
          "NSLocationWhenInUseUsageDescription": "AI Road Trip Storyteller needs your location to provide navigation and location-based stories.",
          "NSLocationAlwaysAndWhenInUseUsageDescription": "AI Road Trip Storyteller needs your location to provide navigation and stories even when the app is in the background.",
          "NSMicrophoneUsageDescription": "AI Road Trip Storyteller needs microphone access for voice commands.",
          "NSSpeechRecognitionUsageDescription": "AI Road Trip Storyteller uses speech recognition to understand your voice commands.",
          "NSCameraUsageDescription": "AI Road Trip Storyteller needs camera access for AR features.",
          "NSPhotoLibraryUsageDescription": "AI Road Trip Storyteller needs photo library access to save your journey memories."
        }
      },
      "android": {
        "buildType": "app-bundle",
        "gradleCommand": ":app:bundleRelease"
      },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://roadtrip-mvp-792001900150.us-central1.run.app",
        "EXPO_PUBLIC_ENVIRONMENT": "production",
        "EXPO_PUBLIC_SENTRY_DSN": "$SENTRY_DSN",
        "NODE_ENV": "production"
      }
    }
  }
}
```

## Setting Up EAS Secrets

### 1. Configure EAS Secrets

```bash
# Set up production secrets (these are build-time only)
eas secret:create --scope project --name SENTRY_DSN --value "your-sentry-dsn"
eas secret:create --scope project --name APPLE_ID --value "your-apple-id"
eas secret:create --scope project --name ASC_APP_ID --value "your-app-store-connect-id"
eas secret:create --scope project --name APPLE_TEAM_ID --value "your-team-id"
```

### 2. List and Verify Secrets

```bash
# List all secrets
eas secret:list

# Verify specific secret (shows metadata only, not value)
eas secret:info SENTRY_DSN
```

## Backend Proxy Endpoints

All sensitive API calls go through these backend proxy endpoints:

### Maps Services
- `POST /api/proxy/maps/places` - Google Places search
- `POST /api/proxy/maps/directions` - Google Directions
- `POST /api/proxy/maps/geocode` - Geocoding service
- `GET /api/proxy/maps/tiles/:z/:x/:y` - Map tiles

### Weather Services
- `GET /api/proxy/weather/current/:lat/:lon` - Current weather
- `GET /api/proxy/weather/forecast/:lat/:lon` - Weather forecast

### Booking Services
- `POST /api/proxy/booking/ticketmaster/search` - Event search
- `POST /api/proxy/booking/opentable/search` - Restaurant search
- `POST /api/proxy/booking/recreation/search` - Recreation search
- `POST /api/proxy/booking/viator/search` - Tour search

### Music Services
- `POST /api/proxy/music/spotify/auth` - Spotify authentication
- `GET /api/proxy/music/spotify/recommendations` - Music recommendations

## Production Build Process

### 1. Set Environment

```bash
# Create production .env file
cp .env.example .env.production

# Edit with production values
nano .env.production
```

### 2. Build Commands

```bash
# Clean build
rm -rf node_modules ios/Pods
npm install
cd ios && pod install && cd ..

# Production build with EAS
NODE_ENV=production eas build --platform all --profile production

# Or platform-specific
NODE_ENV=production eas build --platform ios --profile production
NODE_ENV=production eas build --platform android --profile production
```

### 3. Verify Build Configuration

```bash
# Check environment in build
eas build:inspect --platform ios --profile production
```

## Security Checklist

### Before Production Build
- [ ] All API keys removed from client code
- [ ] Environment variables reviewed
- [ ] Proxy endpoints tested
- [ ] Certificate pinning enabled
- [ ] Code obfuscation configured
- [ ] Source maps extraction setup

### After Production Build
- [ ] No API keys in APK/IPA
- [ ] Environment variables correct
- [ ] Sentry configured properly
- [ ] All features working through proxy
- [ ] Performance acceptable
- [ ] Security scan passed

## Monitoring Production

### 1. Environment Variable Usage

Monitor which environment variables are being used:

```javascript
// In app initialization
if (__DEV__) {
  console.log('Environment:', {
    API_URL: process.env.EXPO_PUBLIC_API_URL,
    ENV: process.env.EXPO_PUBLIC_ENVIRONMENT,
    FEATURES: {
      booking: process.env.EXPO_PUBLIC_ENABLE_BOOKING,
      voice: process.env.EXPO_PUBLIC_ENABLE_VOICE,
      ar: process.env.EXPO_PUBLIC_ENABLE_AR,
    }
  });
}
```

### 2. API Proxy Health

Monitor backend proxy endpoints:

```bash
# Health check
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# Proxy status
curl https://roadtrip-mvp-792001900150.us-central1.run.app/api/proxy/status
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Check EAS secrets are configured
   - Verify `.env.production` exists
   - Ensure build profile uses correct env

2. **API Calls Failing**
   - Verify backend is running
   - Check proxy endpoints
   - Confirm network connectivity

3. **Build Failures**
   - Review EAS build logs
   - Check environment validation
   - Verify all dependencies

### Debug Commands

```bash
# Check current environment
npx expo env:info

# Validate configuration
npx expo doctor

# Test production config locally
NODE_ENV=production npx expo start
```

## Migration from Development

When moving from development to production:

1. Update API URL to production backend
2. Disable development features (if any)
3. Enable all security features
4. Remove any development logging
5. Configure monitoring properly
6. Test all proxy endpoints

## Summary

The production environment is configured with:
- ✅ No API keys in client code
- ✅ All sensitive calls through backend proxy
- ✅ Secure EAS secret management
- ✅ Proper permission descriptions
- ✅ Production-ready build configuration
- ✅ Monitoring and error tracking setup

This configuration ensures maximum security while maintaining full functionality of the app.