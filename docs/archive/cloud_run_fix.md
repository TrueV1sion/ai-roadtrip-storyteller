# Fix Cloud Run Deployment

## Issue
The deployment failed with "Request contains an invalid argument." This usually means:
1. You're not in the correct directory
2. Missing required files (Dockerfile)
3. Permission issues

## Solution Steps

### 1. Navigate to Your Project Directory
```cmd
cd C:\Users\jared\OneDrive\Desktop\roadtrip
```

### 2. Verify Required Files Exist
```cmd
# Check for Dockerfile
dir Dockerfile

# Check for requirements.txt
dir requirements.txt

# List all files
dir
```

### 3. Create Missing Files (if needed)

If Dockerfile is missing, it should already exist in your project. Make sure you're in the right directory.

### 4. Deploy with Correct Command

Try this more specific command:
```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --port 8000 ^
  --project roadtrip-460720
```

### 5. Alternative: Deploy Simple Test First

Create a simple test to verify Cloud Run works:

Create `test_app.py`:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Cloud Run!'

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

Create `requirements_test.txt`:
```
Flask==2.3.2
```

Create `Dockerfile_test`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY test_app.py requirements_test.txt ./
RUN pip install -r requirements_test.txt
CMD python test_app.py
```

Deploy test:
```cmd
gcloud run deploy test-api --source . --region us-central1 --allow-unauthenticated
```

### 6. Common Fixes

**Fix 1: Use Cloud Build explicitly**
```cmd
# Build container first
gcloud builds submit --tag gcr.io/roadtrip-460720/roadtrip-api .

# Then deploy
gcloud run deploy roadtrip-api ^
  --image gcr.io/roadtrip-460720/roadtrip-api ^
  --region us-central1 ^
  --allow-unauthenticated
```

**Fix 2: Check your location**
```cmd
# Make sure you're in the right directory
echo %CD%

# Should show: C:\Users\jared\OneDrive\Desktop\roadtrip
```

**Fix 3: Use explicit Dockerfile**
```cmd
gcloud run deploy roadtrip-api ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --platform managed ^
  --docker-file Dockerfile
```

### 7. Debug the Error

Get more details:
```cmd
# Check recent builds
gcloud builds list --limit 5

# Check Cloud Run services
gcloud run services list

# Get detailed logs
gcloud logging read "resource.type=cloud_run_revision" --limit 20
```

### 8. Working Deployment Command

Based on your project structure, this should work:
```cmd
cd C:\Users\jared\OneDrive\Desktop\roadtrip
gcloud run deploy roadtrip-api --source . --region us-central1 --allow-unauthenticated --port 8000 --memory 2Gi --project roadtrip-460720
```

## If Still Failing

1. **Check you're in the correct directory** with the Dockerfile
2. **Ensure Dockerfile exists** in the current directory
3. **Try deploying from Cloud Console** (web interface) instead

Let me know what error you get and I can help troubleshoot further!