# Immediate Action Plan - RoadTrip Launch

## Priority 1: Fix Vertex AI (1-2 days)

### The Problem
```
Backend Health Check shows:
"gemini_ai": "error: 403 Forbidden - API_KEY_SERVICE_BLOCKED"
```

### Root Causes (Most Likely)
1. Vertex AI API not enabled in Google Cloud Console
2. Service account missing required permissions
3. API key restrictions blocking the service

### Fix Steps

#### Step 1: Enable Vertex AI API
```bash
# Check if API is enabled
gcloud services list --enabled | grep aiplatform

# If not enabled, run:
gcloud services enable aiplatform.googleapis.com --project=roadtrip-mvp
```

#### Step 2: Verify Service Account Permissions
```bash
# Check current service account
gcloud iam service-accounts list --project=roadtrip-mvp

# Add Vertex AI permissions
gcloud projects add-iam-policy-binding roadtrip-mvp \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@roadtrip-mvp.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Also add if needed:
gcloud projects add-iam-policy-binding roadtrip-mvp \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@roadtrip-mvp.iam.gserviceaccount.com" \
  --role="roles/aiplatform.developer"
```

#### Step 3: Update Production Configuration
```bash
# Check current environment variables
gcloud run services describe roadtrip-backend \
  --platform managed \
  --region us-central1 \
  --format export > service.yaml

# Update with correct project ID and location
gcloud run services update roadtrip-backend \
  --update-env-vars GOOGLE_AI_PROJECT_ID=roadtrip-mvp,GOOGLE_AI_LOCATION=us-central1
```

#### Step 4: Test the Fix
```bash
# Test health endpoint
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# Test story generation directly
curl -X POST https://roadtrip-mvp-792001900150.us-central1.run.app/api/v1/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "location": {"latitude": 37.7749, "longitude": -122.4194},
    "interests": ["history", "architecture"],
    "user_id": "test"
  }'
```

## Priority 2: Verify All Integrations (2-3 days)

### Check Each Integration
```bash
# Create a test script
cat > test_integrations.py << 'EOF'
import requests
import json

BASE_URL = "https://roadtrip-mvp-792001900150.us-central1.run.app"

# Test endpoints
endpoints = [
    ("/health", "GET", None),
    ("/api/v1/stories/generate", "POST", {
        "location": {"latitude": 40.7128, "longitude": -74.0060},
        "interests": ["history"],
        "user_id": "test"
    }),
    ("/api/v1/voice/personalities", "GET", None),
    ("/api/v1/maps/search-nearby", "POST", {
        "location": {"latitude": 40.7128, "longitude": -74.0060},
        "radius": 5000,
        "types": ["restaurant"]
    })
]

for endpoint, method, data in endpoints:
    url = BASE_URL + endpoint
    print(f"\nTesting {method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        else:
            response = requests.post(url, json=data)
        
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {str(e)}")
EOF

python test_integrations.py
```

## Priority 3: Production Mobile Build (3-4 days)

### Pre-Build Checklist
- [ ] Run environment validation
  ```bash
  cd mobile
  npm run validate:env
  ```

- [ ] Run security audit
  ```bash
  npm run security:audit
  ```

- [ ] Update version number
  ```bash
  # In app.config.js
  version: "1.0.0" -> "1.0.1"
  ```

### Build Commands
```bash
# Install dependencies
cd mobile
npm install

# Set up EAS
eas login
eas build:configure

# Production builds
NODE_ENV=production eas build --platform ios --profile production
NODE_ENV=production eas build --platform android --profile production
```

### Post-Build Testing
1. Download builds from EAS
2. Test on real devices
3. Verify all features work
4. Check performance metrics

## Priority 4: App Store Preparation (1 week)

### Required Assets
- [ ] App icon (1024x1024)
- [ ] Screenshots (iPhone and iPad)
- [ ] App preview video (optional but recommended)
- [ ] Privacy policy URL
- [ ] Terms of service URL
- [ ] App description (short and long)
- [ ] Keywords
- [ ] Support URL

### App Store Listing
```
Title: RoadTrip AI Storyteller
Subtitle: Your Magical Journey Companion
Category: Travel
Age Rating: 4+

Description:
Transform your road trips into magical adventures with AI-powered storytelling. 
Get personalized stories about the places you visit, discover hidden gems, 
and make bookings on the go.

Features:
• AI-generated stories tailored to your location and interests
• 20+ unique voice personalities
• Real-time navigation with story triggers
• Book restaurants, activities, and attractions
• Works offline with downloaded content
```

## Timeline Summary

### Week 1 (Immediate)
- **Day 1-2**: Fix Vertex AI configuration
- **Day 3**: Test all integrations
- **Day 4-5**: Fix any broken integrations
- **Day 6-7**: Initial mobile production build

### Week 2
- **Day 1-3**: Mobile app testing on devices
- **Day 4-5**: Create app store assets
- **Day 6-7**: Write policies and prepare submission

### Week 3
- **Day 1-2**: Submit to app stores
- **Day 3-7**: Address any review feedback

### Week 4
- **Launch! 🚀**

## Success Metrics

### Technical Success
- [ ] All health checks passing
- [ ] <3s response time for story generation
- [ ] 99%+ crash-free rate
- [ ] All integrations functional

### Business Success
- [ ] First 100 users in week 1
- [ ] 5+ bookings in first month
- [ ] 4.5+ star rating
- [ ] <$500/month infrastructure cost

## Emergency Contacts

### Google Cloud Support
- Console: https://console.cloud.google.com/support
- Vertex AI Issues: Check quotas and API enablement

### EAS/Expo Support
- Forums: https://forums.expo.dev
- Priority support (if purchased)

### Critical Commands
```bash
# Rollback if needed
gcloud run services update-traffic roadtrip-backend --to-revisions=PREVIOUS_REVISION=100

# Emergency logs
gcloud run services logs read roadtrip-backend --limit=100

# Scale down to save costs
gcloud run services update roadtrip-backend --max-instances=1
```

---
**Remember**: The app is 85% complete. These are configuration issues, not fundamental problems. Stay focused on the immediate blockers and launch in 4-5 weeks!