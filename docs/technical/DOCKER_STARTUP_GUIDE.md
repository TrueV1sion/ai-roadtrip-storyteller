# Docker Development Environment Setup

## Quick Start

### 1. Start Docker Desktop

**Windows:**
- Open Docker Desktop from Start Menu
- Wait for "Docker Desktop is running" in system tray

**macOS:**
- Open Docker from Applications
- Or run: `open -a Docker`

**Linux:**
```bash
sudo systemctl start docker
```

### 2. Start Development Environment

Once Docker is running, execute:

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Wait for services (about 10 seconds)
sleep 10

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the Application

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health/detailed

## Alternative: Use Helper Scripts

We've created several helper scripts for you:

1. **Full Docker Setup** (Recommended):
   ```bash
   ./start_dev.sh
   ```

2. **Mock Mode** (No Docker Required):
   ```bash
   python3 start_local.py
   ```

3. **Quick Deploy to Cloud**:
   ```bash
   ./quick_deploy.sh
   ```

## Docker Commands Reference

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Check service status
docker-compose ps

# Connect to PostgreSQL
docker-compose exec db psql -U roadtrip -d roadtrip

# Connect to Redis CLI
docker-compose exec redis redis-cli
```

## Troubleshooting

### "Cannot connect to Docker daemon"
- Ensure Docker Desktop is running
- Check Docker icon in system tray/menu bar
- Try: `docker info` to verify

### "Port already in use"
- Another service is using port 5432 (PostgreSQL) or 6379 (Redis)
- Stop conflicting services or change ports in docker-compose.yml

### "Database connection failed"
- Wait 10-15 seconds after starting services
- Check logs: `docker-compose logs db`
- Ensure DATABASE_URL in .env is correct

## Development Workflow

1. **Start Docker services** (once per session)
2. **Run migrations** (after model changes)
3. **Start API server** with hot reload
4. **Make changes** - server auto-reloads
5. **Run tests** as needed
6. **Stop services** when done

## Next Steps

After starting the development environment:

1. **Test the APIs**:
   ```bash
   python3 test_apis_simple.py
   ```

2. **Create a test user**:
   ```bash
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "testpass123", "full_name": "Test User"}'
   ```

3. **Try the voice assistant**:
   ```bash
   curl -X POST http://localhost:8000/api/voice-assistant/interact \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Plan a trip to Disneyland", "context": {"origin": "San Francisco"}}'
   ```

## Mobile App Development

To run the React Native app:

```bash
cd mobile
npm install
npm start
```

Then:
- Press `i` for iOS simulator
- Press `a` for Android emulator
- Scan QR code for physical device