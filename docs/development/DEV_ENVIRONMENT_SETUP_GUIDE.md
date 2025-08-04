# AI Road Trip Storyteller - Development Environment Setup Guide

This guide will help you set up and run both the backend services and mobile app for the AI Road Trip Storyteller application.

## Prerequisites

- **Docker Desktop** (with Docker Compose v2.37+)
- **Node.js** (v18+ recommended)
- **Python** 3.9+
- **Git**
- **A Google Cloud Project** (for AI services)
- **Expo CLI** (will be installed with npm)

## Quick Start (TL;DR)

```bash
# 1. Clone and setup
git clone <repository-url>
cd roadtrip

# 2. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start backend services
cd infrastructure/docker
docker-compose up -d

# 4. Start mobile app
cd ../../mobile
npm install
npm start
```

## Detailed Setup Instructions

### 1. Environment Configuration

First, create your environment file:

```bash
cp .env.example .env
```

**Essential environment variables to configure:**

```env
# Core
ENVIRONMENT=development
SECRET_KEY=<generate with: openssl rand -hex 32>

# Database (default Docker values)
DATABASE_URL=postgresql://roadtrip:roadtrip@localhost:5432/roadtrip_dev

# Redis (default Docker values)
REDIS_URL=redis://localhost:6379/0

# Google Cloud (REQUIRED for AI features)
GOOGLE_CLOUD_PROJECT=<your-gcp-project-id>
GOOGLE_AI_PROJECT_ID=<your-gcp-project-id>
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>

# JWT Auth
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>

# Mobile App
EXPO_PUBLIC_API_URL=http://localhost:8001
```

### 2. Starting Backend Services

The application uses Docker Compose to manage all backend services:

```bash
cd infrastructure/docker
docker-compose up -d
```

This will start:
- **Knowledge Graph** (Port 8000) - Code intelligence system
- **Backend API** (Port 8001) - Main API server
- **PostgreSQL** (Port 5432) - Database
- **Redis** (Port 6379) - Cache
- **Celery Worker** - Async task processing
- **Celery Beat** - Scheduled tasks
- **Flower** (Port 5555) - Celery monitoring
- **Adminer** (Port 8080) - Database admin UI

**Verify services are running:**

```bash
# Check container status
docker-compose ps

# Check API health
curl http://localhost:8001/health

# Check Knowledge Graph
curl http://localhost:8000/api/health
```

### 3. Database Setup

The database migrations run automatically when the backend starts. To run them manually:

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Mobile App Setup

```bash
cd mobile
npm install
```

**Start the Expo development server:**

```bash
# Regular mode
npm start

# MVP mode (simplified features)
npm run start:mvp
```

**Run on specific platforms:**

```bash
# iOS Simulator
npm run ios

# Android Emulator
npm run android

# Web browser
npm run web
```

### 5. Accessing the Application

- **Backend API Docs**: http://localhost:8001/docs
- **Knowledge Graph Dashboard**: http://localhost:8000
- **Database Admin (Adminer)**: http://localhost:8080
  - Server: `postgres`
  - Username: `roadtrip`
  - Password: `roadtrip`
  - Database: `roadtrip_dev`
- **Celery Monitoring (Flower)**: http://localhost:5555
- **Mobile App**: Follow Expo QR code or simulator instructions

## Google Cloud Setup

The application requires Google Cloud for AI features:

1. **Create a Google Cloud Project**
2. **Enable required APIs:**
   ```bash
   gcloud services enable \
     vertexai.googleapis.com \
     maps-backend.googleapis.com \
     places-backend.googleapis.com \
     texttospeech.googleapis.com \
     speech.googleapis.com
   ```

3. **Create a service account** (for local development):
   ```bash
   gcloud iam service-accounts create roadtrip-dev \
     --display-name="Road Trip Dev Account"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:roadtrip-dev@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

4. **Download credentials:**
   ```bash
   gcloud iam service-accounts keys create credentials.json \
     --iam-account=roadtrip-dev@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

5. **Set environment variable:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
   ```

## Common Issues & Troubleshooting

### Docker Issues

**Problem**: Docker containers won't start
```bash
# Solution 1: Clean restart
docker-compose down -v
docker-compose up -d

# Solution 2: Check logs
docker-compose logs backend
docker-compose logs knowledge-graph
```

**Problem**: Port conflicts
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :8001
lsof -i :5432

# Or on Windows
netstat -ano | findstr :8000
```

### Backend Issues

**Problem**: API returns 500 errors
```bash
# Check backend logs
docker-compose logs -f backend

# Common fixes:
# 1. Ensure database is running
docker-compose ps postgres

# 2. Run migrations
docker-compose exec backend alembic upgrade head

# 3. Check environment variables
docker-compose exec backend env | grep -E "(DATABASE|REDIS|GOOGLE)"
```

**Problem**: Knowledge Graph not connecting
```bash
# Ensure it's running
curl http://localhost:8000/api/health

# Restart if needed
docker-compose restart knowledge-graph
```

### Mobile App Issues

**Problem**: Can't connect to backend
```bash
# For physical devices, use your machine's IP
EXPO_PUBLIC_API_URL=http://YOUR_IP:8001

# Find your IP:
# Mac/Linux: ifconfig | grep inet
# Windows: ipconfig
```

**Problem**: Expo build errors
```bash
# Clear cache and reinstall
rm -rf node_modules
npm cache clean --force
npm install
npx expo start -c
```

### Database Issues

**Problem**: Migration errors
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

## Development Workflow

### Starting Everything

```bash
# Terminal 1: Backend services
cd infrastructure/docker
docker-compose up

# Terminal 2: Mobile app
cd mobile
npm start
```

### Checking Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery
```

### Running Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Mobile tests
cd mobile
npm test
```

### Stopping Services

```bash
# Stop containers (preserves data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

## Additional Resources

- **API Documentation**: http://localhost:8001/docs
- **Project README**: /README.md
- **Claude Instructions**: /CLAUDE.md
- **Mobile Setup Guide**: /docs/guides/MOBILE_DEV_SETUP_GUIDE.md

## Need Help?

1. Check the logs: `docker-compose logs`
2. Verify environment variables are set correctly
3. Ensure all required Google Cloud APIs are enabled
4. Check that ports aren't already in use
5. Try the clean restart procedure above

For development, the Knowledge Graph at http://localhost:8000 provides code intelligence and impact analysis - always consult it before making changes!