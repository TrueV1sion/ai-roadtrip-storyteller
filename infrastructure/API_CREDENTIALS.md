# RoadTrip API Credentials Guide

This guide explains which API credentials are required for the RoadTrip application, how to obtain them, and what features they enable.

## Required API Keys (Core Functionality)

These APIs are essential for the basic operation of the RoadTrip application:

### 1. Google Maps API Key
- **Purpose**: Navigation, directions, places search, geocoding
- **Cost**: Pay-as-you-go, ~$200 free monthly credit
- **How to obtain**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com)
  2. Enable Maps JavaScript API, Places API, Geocoding API, Directions API
  3. Create an API key and restrict it to your domains
- **Features affected if missing**: No navigation, no place search, no map display

### 2. OpenWeatherMap API Key
- **Purpose**: Real-time weather data along routes
- **Cost**: Free tier available (1,000 calls/day)
- **How to obtain**:
  1. Sign up at [openweathermap.org](https://openweathermap.org/api)
  2. Generate API key from dashboard
- **Features affected if missing**: No weather information, safety warnings disabled

### 3. Ticketmaster API Key
- **Purpose**: Event discovery and booking
- **Cost**: Free for developers
- **How to obtain**:
  1. Register at [developer.ticketmaster.com](https://developer.ticketmaster.com)
  2. Create an app to get API key and secret
- **Features affected if missing**: No event discovery or booking

### 4. Recreation.gov API Key
- **Purpose**: Campground and recreation area booking
- **Cost**: Free
- **How to obtain**:
  1. Apply at [recreation.gov/api](https://www.recreation.gov/api)
  2. Approval may take 1-2 weeks
- **Features affected if missing**: No campground booking

## Optional API Keys (Enhanced Features)

These APIs enable additional features but are not required for basic functionality:

### Restaurant Booking

#### OpenTable API
- **Purpose**: Restaurant reservations
- **Cost**: Partner program required
- **How to obtain**: Contact OpenTable for partner access
- **Alternative**: Features work in demo mode without API

#### Resy API
- **Purpose**: Premium restaurant reservations
- **Cost**: Partner program required
- **How to obtain**: Apply through Resy partner program
- **Alternative**: Features work in demo mode without API

### Travel & Activities

#### Viator API
- **Purpose**: Tours and activities booking
- **Cost**: Commission-based (no upfront cost)
- **How to obtain**: Apply at [viatorapi.viator.com](https://viatorapi.viator.com)
- **Features affected**: No tour booking integration

### Music Integration

#### Spotify API
- **Purpose**: Road trip playlists, music control
- **Cost**: Free
- **How to obtain**:
  1. Create app at [developer.spotify.com](https://developer.spotify.com)
  2. Get Client ID and Secret
- **Features affected**: No Spotify integration, fallback to device music

### EV Charging

#### Shell Recharge API
- **Purpose**: EV charging station discovery
- **Cost**: Contact for pricing
- **How to obtain**: Contact Shell Recharge for developer access
- **Features affected**: Limited EV charging info

#### ChargePoint API
- **Purpose**: ChargePoint network integration
- **Cost**: Contact for pricing
- **How to obtain**: Apply through ChargePoint developer program
- **Features affected**: No ChargePoint station data

### Flight Tracking

#### Multiple providers supported (any one is sufficient):
- **FlightStats**: Professional flight data (paid)
- **FlightAware**: Comprehensive flight tracking (paid)
- **AviationStack**: Simple flight data (free tier available)
- **FlightLabs**: Flight status API (free tier available)

**Features affected**: No real-time flight tracking

### Airport Services

#### Priority Pass API
- **Purpose**: Airport lounge access
- **Cost**: Partner program
- **How to obtain**: Contact Priority Pass for API access
- **Features affected**: No lounge booking

### Communication Services

#### Twilio
- **Purpose**: SMS notifications, 2FA
- **Cost**: Pay-per-message (~$0.0075/SMS)
- **How to obtain**: Sign up at [twilio.com](https://www.twilio.com)
- **Features affected**: No SMS features

#### SendGrid
- **Purpose**: Transactional emails
- **Cost**: Free tier (100 emails/day)
- **How to obtain**: Sign up at [sendgrid.com](https://sendgrid.com)
- **Features affected**: No email notifications

## Setting Up Credentials

### Initial Setup (Creates Placeholders)
```bash
cd infrastructure/scripts
./setup-secrets.sh [PROJECT_ID]
```

### Update a Specific Secret
```bash
# Example: Set Google Maps API key
echo -n "your-actual-api-key" | gcloud secrets versions add roadtrip-google-maps-key --data-file=-
```

### Validate Configuration
```bash
./validate-secrets.sh [PROJECT_ID]
```

## Priority Order for Implementation

1. **Immediate (Required for MVP)**:
   - Google Maps API Key
   - OpenWeatherMap API Key
   - Database and Redis URLs

2. **Phase 1 (Core Features)**:
   - Ticketmaster API
   - Recreation.gov API
   - Spotify API (for music features)

3. **Phase 2 (Enhanced Booking)**:
   - Viator API
   - OpenTable or Resy API
   - Flight tracking API (choose one)

4. **Phase 3 (Additional Features)**:
   - EV charging APIs
   - Airport service APIs
   - Communication APIs (Twilio/SendGrid)

## Cost Estimates

### Minimal Operation (MVP)
- Google Maps: ~$50-200/month (depending on usage)
- OpenWeatherMap: Free tier sufficient
- Total: ~$50-200/month

### Full Feature Set
- All APIs: ~$200-500/month (depending on usage)
- Most costs are usage-based and scale with users

## Demo Mode

The application includes demo/mock modes for most integrations, allowing you to:
- Test features without API keys
- Develop against mock data
- Demonstrate functionality to stakeholders

To enable demo mode, the application automatically falls back when API keys are not configured.