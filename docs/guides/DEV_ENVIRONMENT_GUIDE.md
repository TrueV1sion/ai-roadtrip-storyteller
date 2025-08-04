# AI Road Trip Storyteller - Development Environment Guide

## Quick Start

1. **Prerequisites Installation**
   ```bash
   # Install required software:
   # - Python 3.9+
   # - Node.js 16+
   # - Docker & Docker Compose
   # - Git
   ```

2. **Setup Environment**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd roadtrip

   # Copy environment template
   cp .env.example .env

   # Edit .env file with your API keys
   # Required: GOOGLE_AI_PROJECT_ID, SECRET_KEY
   ```

3. **Start Development Environment**
   ```bash
   # Make scripts executable
   chmod +x scripts/start_dev_environment.sh
   chmod +x scripts/stop_dev_environment.sh

   # Start all services
   ./scripts/start_dev_environment.sh
   ```

## Accessing the Application

### Web Interfaces
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Knowledge Graph**: http://localhost:8001
- **Mobile App**: Expo will provide a QR code

### Mobile Preview Options

1. **Using Expo Go (Recommended for Quick Preview)**
   - Install Expo Go on your phone
   - Scan the QR code shown in terminal
   - App will load on your device

2. **iOS Simulator**
   ```bash
   cd mobile
   npm run ios
   ```

3. **Android Emulator**
   ```bash
   cd mobile
   npm run android
   ```

4. **Web Browser (Limited Features)**
   ```bash
   cd mobile
   npm run web
   ```

## Required API Keys

### Minimum Required (for basic functionality)
- `GOOGLE_AI_PROJECT_ID` - For AI story generation
- `SECRET_KEY` - For JWT authentication
- `DATABASE_URL` - PostgreSQL connection (auto-configured)
- `REDIS_URL` - Redis connection (auto-configured)

### Optional (for full features)
- `GOOGLE_MAPS_API_KEY` - For navigation features
- `SPOTIFY_CLIENT_ID/SECRET` - For music integration
- `OPENWEATHER_API_KEY` - For weather-based stories
- `TWILIO_*` - For SMS notifications
- `STRIPE_API_KEY` - For payment processing

## Testing the Application

### 1. Test Backend API
```bash
# Open API docs
open http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/health

# Run tests
pytest
```

### 2. Test Mobile App
- Create a test account in the app
- Try the voice recording feature
- Test story generation
- Explore AR features (device only)

### 3. Test Knowledge Graph
```bash
# Search for code
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "voice services"}'
```

## Common Development Tasks

### View Logs
```bash
# Backend logs
tail -f backend/logs/app.log

# Docker service logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Mobile logs
# Check the terminal where npm start is running
```

### Database Operations
```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Access database
docker exec -it roadtrip-postgres psql -U roadtrip roadtrip_dev
```

### Running Tests
```bash
# Backend tests
pytest

# With coverage
pytest --cov=backend/app --cov-report=html

# Mobile tests
cd mobile && npm test
```

### Code Quality
```bash
# Python formatting
black backend/
flake8 backend/

# TypeScript linting
cd mobile && npm run lint
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database Connection Issues
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
cd backend && alembic upgrade head
```

### Mobile App Not Loading
1. Check that backend is running: http://localhost:8000/health
2. Verify EXPO_PUBLIC_API_URL in mobile/.env
3. Clear Expo cache: `expo start -c`

### Missing Dependencies
```bash
# Python
pip install -r requirements.txt

# Node.js
cd mobile && npm install
```

## Stopping the Environment
```bash
# Stop all services gracefully
./scripts/stop_dev_environment.sh

# Or force stop
docker-compose down
pkill -f "uvicorn"
pkill -f "npm"
```

## Production Preview

To test production configuration locally:
```bash
# Use production docker-compose
docker-compose -f docker-compose.prod.yml up

# Access at http://localhost:80
```

## Next Steps

1. **Configure API Keys**: Edit `.env` file with your actual API keys
2. **Test Core Features**: Voice recording, story generation, navigation
3. **Explore Documentation**: Check `/docs` folder for architecture details
4. **Join Development**: See CONTRIBUTING.md for guidelines

## Support

- **Documentation**: `/docs` folder
- **API Reference**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Logs**: Check `backend/logs/` and Docker logs