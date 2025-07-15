# Fix Cloud Run Port Issue

## The Problem
Your container failed to start and listen on port 8000. This happens when:
1. The app is trying to connect to a database that doesn't exist
2. The PORT environment variable isn't being used correctly
3. Missing environment variables cause the app to crash

## Quick Fix Solutions

### Solution 1: Deploy with Environment Variables for Mock Mode

Deploy with mock mode enabled (no external dependencies):

```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000 ^
  --set-env-vars="MOCK_REDIS=true,USE_MOCK_APIS=true,SKIP_DB_CHECK=true,ENVIRONMENT=development"
```

### Solution 2: Create a Cloud Run Specific Startup Script

Create `start_cloudrun.sh`:

```bash
#!/bin/bash
# Start script for Cloud Run
export MOCK_REDIS=true
export USE_MOCK_APIS=true
export SKIP_DB_CHECK=true
export DATABASE_URL=sqlite:///./roadtrip.db

# Use PORT from environment or default to 8000
PORT=${PORT:-8000}

echo "Starting on port $PORT"
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Then update your Dockerfile's last line:
```dockerfile
COPY start_cloudrun.sh .
RUN chmod +x start_cloudrun.sh
CMD ["./start_cloudrun.sh"]
```

### Solution 3: Use a Simplified Dockerfile

Create `Dockerfile.cloudrun.simple`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy redis httpx pydantic python-jose passlib

# Copy app
COPY backend ./backend

# Set environment variables
ENV MOCK_REDIS=true
ENV USE_MOCK_APIS=true
ENV SKIP_DB_CHECK=true
ENV DATABASE_URL=sqlite:///./roadtrip.db

EXPOSE 8000

# Use PORT environment variable
CMD exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Deploy with:
```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated
```

### Solution 4: Check the Logs First

View the exact error:
```cmd
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-api" --limit 50
```

Or open in browser:
https://console.cloud.google.com/logs/viewer?project=roadtrip-460720&resource=cloud_run_revision/service_name/roadtrip-api

### Solution 5: Deploy a Test App First

Let's verify Cloud Run works with a simple app:

Create `test_app.py`:
```python
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from Cloud Run!", "port": os.getenv("PORT", "8000")}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

Create `Dockerfile.test`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY test_app.py .
CMD ["python", "test_app.py"]
```

Deploy test:
```cmd
copy Dockerfile Dockerfile.backup
copy Dockerfile.test Dockerfile
gcloud run deploy test-api --source . --region us-central1 --allow-unauthenticated
```

## Most Likely Fix

The app is probably trying to connect to PostgreSQL/Redis on startup. Deploy with mock mode:

```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000 ^
  --timeout 300 ^
  --set-env-vars="MOCK_REDIS=true,USE_MOCK_APIS=true,SKIP_DB_CHECK=true,DATABASE_URL=sqlite:///./app.db,ENVIRONMENT=production,SECRET_KEY=temp-secret-key,JWT_SECRET_KEY=temp-jwt-key"
```

## What's Happening

Your app is likely:
1. Trying to connect to PostgreSQL (which doesn't exist in Cloud Run)
2. Trying to connect to Redis (which doesn't exist)
3. Failing fast because of missing connections

The solution is to either:
- Use mock mode (recommended for testing)
- Set up Cloud SQL and Memorystore
- Use SQLite for simple deployment

Try Solution 1 first - it should work immediately!