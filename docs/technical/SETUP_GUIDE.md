# AI Road Trip Storyteller - Setup Guide

**Last Updated:** December 10, 2024  
**Estimated Setup Time:** 30-45 minutes  
**Prerequisites:** Python 3.9+, Node.js 16+, Docker, Git

## Quick Start (5 minutes)

```bash
# Clone the repository
git clone https://github.com/your-org/ai-road-trip-storyteller.git
cd ai-road-trip-storyteller

# Run the automated setup
python configure_apis_simple.py

# Start the development environment
docker-compose up -d
python start_local.py

# Access the application
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Detailed Setup Instructions

### 1. Environment Setup

#### System Requirements
- **Python:** 3.9 or higher
- **Node.js:** 16.0 or higher  
- **Docker:** 20.10 or higher
- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** 10GB free space

#### Clone Repository
```bash
git clone https://github.com/your-org/ai-road-trip-storyteller.git
cd ai-road-trip-storyteller
```

### 2. Backend Setup

#### Create Python Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

#### Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Essential Configuration
DATABASE_URL=postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip
REDIS_URL=redis://localhost:6379
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-change-in-production

# Required API Keys (get these first)
GOOGLE_MAPS_API_KEY=your-google-maps-key
TICKETMASTER_API_KEY=your-ticketmaster-key  
OPENWEATHERMAP_API_KEY=your-weather-key
RECREATION_GOV_API_KEY=your-recreation-key

# Google Cloud Configuration (for AI features)
GOOGLE_AI_PROJECT_ID=your-gcp-project-id
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=your-storage-bucket

# Optional Features
SPOTIFY_CLIENT_ID=your-spotify-id
SPOTIFY_CLIENT_SECRET=your-spotify-secret

# Development Settings
TEST_MODE=mock  # Use 'live' for real API calls
LOG_LEVEL=INFO
APP_VERSION=1.0.0
```

#### Interactive Configuration (Recommended)
```bash
# This wizard will help you set up all API keys
python configure_apis_simple.py
```

### 3. Database Setup

#### Start PostgreSQL and Redis
```bash
# Using Docker Compose (recommended)
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

#### Run Database Migrations
```bash
# Create database schema
alembic upgrade head

# Verify migrations
alembic current
```

### 4. Google Cloud Setup

#### Create GCP Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Note your Project ID

#### Enable Required APIs
```bash
# Run the automated setup script
python setup_apis_comprehensive.py

# Or manually enable via Console:
# - Vertex AI API
# - Cloud Storage API
# - Maps JavaScript API
# - Places API
# - Directions API
# - Cloud Text-to-Speech API
# - Cloud Speech-to-Text API
```

#### Create Service Account
```bash
# Using gcloud CLI
gcloud iam service-accounts create roadtrip-app \
    --display-name="Road Trip App Service Account"

# Download credentials
gcloud iam service-accounts keys create credentials.json \
    --iam-account=roadtrip-app@YOUR-PROJECT-ID.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials.json"
```

### 5. Mobile App Setup

#### Navigate to Mobile Directory
```bash
cd mobile
```

#### Install Dependencies
```bash
npm install
# or
yarn install
```

#### iOS Setup (macOS only)
```bash
cd ios
pod install
cd ..
```

#### Configure Mobile Environment
Create `mobile/src/config/env.ts`:

```typescript
export const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000'
  : 'https://api.yourapp.com';

export const GOOGLE_MAPS_API_KEY = 'your-google-maps-key';
```

### 6. Start Development Environment

#### Option 1: Full Stack with Docker
```bash
# From project root
docker-compose up -d
python start_local.py
```

#### Option 2: Manual Start

Terminal 1 - Backend:
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Mobile:
```bash
cd mobile
npm start
# Press 'i' for iOS, 'a' for Android, 'w' for web
```

### 7. Verify Installation

#### Backend Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","timestamp":"..."}
```

#### API Documentation
Open http://localhost:8000/docs in your browser

#### Database Connection
```bash
python -c "from backend.app.database import engine; print('Database connected!')"
```

### 8. API Key Configuration Guide

#### Google Maps API
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable Maps JavaScript API, Places API, Directions API
3. Create API key with restrictions:
   - HTTP referrers: `http://localhost:*`
   - API restrictions: Maps, Places, Directions

#### Ticketmaster API
1. Register at [Ticketmaster Developer Portal](https://developer.ticketmaster.com)
2. Create new app
3. Copy Consumer Key as `TICKETMASTER_API_KEY`

#### OpenWeatherMap API
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Generate API key (free tier sufficient)
3. Add to `.env` as `OPENWEATHERMAP_API_KEY`

#### Recreation.gov API
1. Apply at [Recreation.gov API](https://www.recreation.gov/api)
2. Wait for approval (1-2 days)
3. Use provided key as `RECREATION_GOV_API_KEY`

#### Spotify (Optional)
1. Go to [Spotify Dashboard](https://developer.spotify.com/dashboard)
2. Create app
3. Add redirect URI: `http://localhost:8000/api/spotify/callback`
4. Copy Client ID and Secret

### 9. Common Issues & Solutions

#### Issue: Database Connection Failed
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

#### Issue: Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
uvicorn backend.app.main:app --port 8001
```

#### Issue: Google Cloud Authentication Failed
```bash
# Verify credentials file exists
ls -la credentials.json

# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Re-authenticate
gcloud auth application-default login
```

#### Issue: Mobile Build Failed
```bash
# Clear cache
cd mobile
npm start -- --clear
rm -rf node_modules
npm install

# For iOS issues
cd ios
pod deintegrate
pod install
```

### 10. Development Workflow

#### Running Tests
```bash
# Backend tests
pytest
pytest --cov=backend/app  # With coverage

# Mobile tests
cd mobile
npm test
```

#### Code Quality Checks
```bash
# Python
black backend/
ruff check backend/
mypy backend/app

# JavaScript/TypeScript
cd mobile
npm run lint
npm run typecheck
```

#### Using Mock Mode
```bash
# In .env file
TEST_MODE=mock

# This enables development without all API keys
# Switches to mock data for partner integrations
```

### 11. Production Deployment Preparation

#### Build Production Images
```bash
docker build -t roadtrip-backend:latest .
```

#### Environment Variables for Production
```bash
# Never commit .env files!
# Use secret management service

# Required for production:
- DATABASE_URL (production database)
- REDIS_URL (production Redis)
- SECRET_KEY (generate new secure key)
- All API keys with production access
```

#### Pre-deployment Checklist
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] SSL certificates ready
- [ ] Monitoring configured
- [ ] Backup strategy implemented

## Next Steps

1. **Run Demo**: `python demo_backend.py` for a quick UI demo
2. **Explore API**: Visit http://localhost:8000/docs
3. **Test Voice**: Try the voice assistant endpoint
4. **Mobile Development**: Run mobile app on device/simulator

## Support

- **Documentation**: See `/docs` directory
- **Issues**: GitHub Issues
- **Updates**: Check CLAUDE.md for AI assistant guidance

---

*For production deployment, see DEPLOYMENT_GUIDE.md*