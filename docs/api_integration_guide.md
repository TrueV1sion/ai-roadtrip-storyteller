# API Integration Setup Guide

This guide provides detailed instructions for setting up all external API integrations required by the AI Road Trip Storyteller application.

## Table of Contents
1. [Google Cloud Platform APIs](#google-cloud-platform-apis)
2. [Third-Party Booking APIs](#third-party-booking-apis)
3. [Entertainment APIs](#entertainment-apis)
4. [Weather and Traffic APIs](#weather-and-traffic-apis)
5. [Configuration Validation](#configuration-validation)
6. [Testing Procedures](#testing-procedures)
7. [Error Handling](#error-handling)

## Google Cloud Platform APIs

### 1. Google Maps Platform

**Required APIs:**
- Maps JavaScript API
- Directions API
- Places API
- Roads API
- Geocoding API

**Setup Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable billing (required for Maps APIs)
4. Navigate to "APIs & Services" > "Library"
5. Search and enable each required API
6. Go to "Credentials" > "Create Credentials" > "API Key"
7. Restrict the API key:
   - Application restrictions: HTTP referrers for web, Android/iOS apps for mobile
   - API restrictions: Select only the enabled APIs

**Configuration Parameters:**
```env
GOOGLE_MAPS_API_KEY=your_api_key_here
GOOGLE_MAPS_WEB_KEY=your_web_specific_key_here
GOOGLE_MAPS_MOBILE_KEY=your_mobile_specific_key_here
```

**Quota Limits:**
- Directions API: 50,000 requests/day
- Places API: 150,000 requests/day
- Consider implementing caching to reduce API calls

### 2. Google Cloud Text-to-Speech

**Setup Steps:**
1. Enable the Cloud Text-to-Speech API
2. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Create new service account
   - Grant "Cloud Text-to-Speech User" role
   - Create and download JSON key file
3. Set up authentication

**Configuration Parameters:**
```env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_TTS_VOICE_NAME=en-US-Wavenet-D
GOOGLE_TTS_LANGUAGE_CODE=en-US
GOOGLE_TTS_AUDIO_ENCODING=MP3
```

### 3. Google Cloud Speech-to-Text

**Setup Steps:**
1. Enable the Cloud Speech-to-Text API
2. Use the same service account as TTS
3. Grant "Cloud Speech-to-Text User" role

**Configuration Parameters:**
```env
GOOGLE_STT_LANGUAGE_CODE=en-US
GOOGLE_STT_ENABLE_WORD_TIME_OFFSETS=true
GOOGLE_STT_MODEL=latest_long
```

### 4. Vertex AI

**Setup Steps:**
1. Enable Vertex AI API
2. Grant service account "Vertex AI User" role
3. Select your preferred model region

**Configuration Parameters:**
```env
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_TOKENS=4096
```

## Third-Party Booking APIs

### 1. OpenTable API

**Registration:**
1. Visit [OpenTable Connect](https://www.opentable.com/developers)
2. Apply for partner access
3. Complete the partner agreement
4. Wait for approval (typically 5-7 business days)

**Configuration Parameters:**
```env
OPENTABLE_CLIENT_ID=your_client_id
OPENTABLE_CLIENT_SECRET=your_client_secret
OPENTABLE_API_VERSION=v2
OPENTABLE_BASE_URL=https://api.opentable.com
```

**Key Endpoints:**
- Restaurant search: `/api/restaurants`
- Availability: `/api/availability`
- Reservations: `/api/reservations`

### 2. Yelp Fusion API

**Setup Steps:**
1. Go to [Yelp Developers](https://www.yelp.com/developers)
2. Create an app
3. Get your API key

**Configuration Parameters:**
```env
YELP_API_KEY=your_api_key
YELP_API_BASE_URL=https://api.yelp.com/v3
```

### 3. Ticketmaster API

**Setup Steps:**
1. Register at [Ticketmaster Developer Portal](https://developer.ticketmaster.com/)
2. Create a new app
3. Get your API key

**Configuration Parameters:**
```env
TICKETMASTER_API_KEY=your_api_key
TICKETMASTER_SECRET=your_secret
TICKETMASTER_BASE_URL=https://app.ticketmaster.com/discovery/v2
```

### 4. Viator API

**Setup Steps:**
1. Apply at [Viator Partner Portal](https://supplier.viator.com/)
2. Complete partner onboarding
3. Receive API credentials

**Configuration Parameters:**
```env
VIATOR_API_KEY=your_api_key
VIATOR_PARTNER_ID=your_partner_id
VIATOR_BASE_URL=https://api.viator.com/partner
```

## Entertainment APIs

### 1. Spotify Web API

**Setup Steps:**
1. Go to [Spotify for Developers](https://developer.spotify.com/)
2. Create an app
3. Note your Client ID and Client Secret
4. Set redirect URIs for OAuth

**Configuration Parameters:**
```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=yourapp://spotify-callback
SPOTIFY_SCOPES=streaming,user-read-playback-state,user-modify-playback-state
```

### 2. Apple Music API

**Setup Steps:**
1. Enroll in [Apple Developer Program](https://developer.apple.com/)
2. Create a MusicKit identifier
3. Generate a private key
4. Create developer token

**Configuration Parameters:**
```env
APPLE_MUSIC_TEAM_ID=your_team_id
APPLE_MUSIC_KEY_ID=your_key_id
APPLE_MUSIC_PRIVATE_KEY_PATH=/path/to/private_key.p8
```

## Weather and Traffic APIs

### 1. OpenWeatherMap API

**Setup Steps:**
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Get your API key
3. Choose appropriate subscription plan

**Configuration Parameters:**
```env
OPENWEATHER_API_KEY=your_api_key
OPENWEATHER_BASE_URL=https://api.openweathermap.org/data/2.5
OPENWEATHER_UNITS=imperial
```

### 2. HERE Traffic API

**Setup Steps:**
1. Register at [HERE Developer](https://developer.here.com/)
2. Create a project
3. Generate API key

**Configuration Parameters:**
```env
HERE_API_KEY=your_api_key
HERE_APP_ID=your_app_id
HERE_BASE_URL=https://traffic.ls.hereapi.com/traffic/6.3
```

## Configuration Validation

Run the validation script to ensure all APIs are properly configured:

```bash
python scripts/validate_api_config.py
```

The script will:
- Check for missing environment variables
- Validate API key formats
- Test basic connectivity to each service
- Report any configuration issues

## Testing Procedures

### Google Maps API Test
```python
# Test directions request
response = directions_service.get_directions(
    origin="San Francisco, CA",
    destination="Los Angeles, CA"
)
assert response.status == "OK"
```

### OpenTable API Test
```python
# Test restaurant search
restaurants = opentable_client.search_restaurants(
    location="San Francisco",
    date="2024-12-25",
    party_size=4
)
assert len(restaurants) > 0
```

### Spotify API Test
```python
# Test authentication
token = spotify_auth.get_access_token()
assert token is not None
```

## Error Handling

### Fallback Strategies

1. **Google Maps Failure:**
   - Cache recent route data
   - Use offline map tiles
   - Provide basic distance/time estimates

2. **Booking API Failures:**
   - Queue reservation requests for retry
   - Provide direct links to partner websites
   - Store user preferences for manual booking

3. **Entertainment API Failures:**
   - Use local music library
   - Provide cached playlists
   - Continue with storytelling only

### Rate Limiting

Implement exponential backoff for all APIs:

```python
def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

### Monitoring

Set up alerts for:
- API quota usage > 80%
- Authentication failures
- Repeated timeout errors
- Fallback activation

## Security Best Practices

1. **Never commit API keys to version control**
2. **Use environment-specific keys** (dev/staging/prod)
3. **Implement key rotation** every 90 days
4. **Use secret management services** in production
5. **Apply API key restrictions** based on:
   - IP addresses (backend)
   - Bundle IDs (mobile)
   - HTTP referrers (web)

## Support Resources

- Google Cloud Support: https://cloud.google.com/support
- OpenTable Partner Support: partners@opentable.com
- Ticketmaster Developer Forum: https://developer.ticketmaster.com/forum
- Spotify Developer Community: https://community.spotify.com/t5/Spotify-for-Developers/bd-p/Spotify_Developer