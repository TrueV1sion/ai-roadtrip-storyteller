# Fix Cloud Run Build Failure

## Check Build Logs

First, view the detailed build logs:

```cmd
# Option 1: Get the latest build ID
gcloud builds list --limit=1 --region=us-central1

# Option 2: View logs directly
gcloud builds log 240a31d8-fa87-44a1-86ea-af9432bdf8e1 --region=us-central1
```

## Common Build Failures & Solutions

### 1. Python Package Installation Issues

Check your requirements.txt for problematic packages:

```cmd
# View requirements.txt
type requirements.txt
```

Common fixes:
- Remove version conflicts
- Update outdated packages
- Remove Windows-specific packages

### 2. Use Cloud Run Specific Dockerfile

You have a `Dockerfile.cloudrun` - let's use it:

```cmd
# Deploy using the Cloud Run specific Dockerfile
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000 ^
  --timeout 60m
```

### 3. Simplify Requirements

Create a minimal `requirements.cloud.txt` with only essential packages:

```txt
fastapi==0.109.2
uvicorn[standard]==0.27.0
pydantic==2.5.3
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.1
httpx==0.26.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
gunicorn==21.2.0
google-cloud-aiplatform==1.40.0
google-cloud-texttospeech==2.15.0
google-cloud-speech==2.23.0
google-cloud-storage==2.14.0
```

Then update Dockerfile to use it:
```dockerfile
COPY requirements.cloud.txt requirements.txt
```

### 4. Quick Fix - Deploy with Buildpacks

Try deploying without Dockerfile (uses Google's buildpacks):

```cmd
# Rename Dockerfile temporarily
ren Dockerfile Dockerfile.backup

# Deploy with buildpacks
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000
```

### 5. Build Locally First

Test the Docker build locally:

```cmd
# Build locally
docker build -t roadtrip-test .

# If it fails, you'll see the exact error
```

### 6. Use Pre-built Image

If builds keep failing, use a pre-built base:

Create `Dockerfile.simple`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend ./backend
COPY healthcheck.sh .

# Make healthcheck executable
RUN chmod +x healthcheck.sh

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Deploy with:
```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated
```

### 7. Check Specific Build Error

To see the exact error:

```cmd
# Open in browser
start https://console.cloud.google.com/cloud-build/builds;region=us-central1/240a31d8-fa87-44a1-86ea-af9432bdf8e1?project=792001900150
```

## Most Likely Issue

Based on the structure, the build is probably failing because:
1. **Package installation timeout** - Some packages take too long
2. **Missing system dependencies** - Some Python packages need system libraries
3. **Memory issues** - Build running out of memory

## Quick Solution

Try this simplified deployment:

```cmd
# 1. Create a .gcloudignore file
echo node_modules > .gcloudignore
echo .git >> .gcloudignore
echo __pycache__ >> .gcloudignore
echo .env >> .gcloudignore

# 2. Deploy with increased timeout
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000 ^
  --timeout 60m ^
  --memory 4Gi
```

Let me know what error you see in the build logs and I can provide a more specific fix!