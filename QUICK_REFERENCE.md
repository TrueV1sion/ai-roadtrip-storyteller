# RoadTrip Quick Reference Card

## 🚀 Production URLs
- **Backend API**: https://roadtrip-mvp-792001900150.us-central1.run.app
- **API Docs**: https://roadtrip-mvp-792001900150.us-central1.run.app/docs
- **Health Check**: https://roadtrip-mvp-792001900150.us-central1.run.app/health

## 🔧 Current Status (Jan 2025)
- **Backend**: ✅ Deployed (Vertex AI blocked)
- **Mobile**: ✅ Security complete, needs production build
- **Database**: ✅ Running on Cloud SQL
- **Redis**: ✅ Caching active

## 🚨 Main Blocker
```bash
# Vertex AI returning 403 - Fix with:
gcloud services enable aiplatform.googleapis.com --project=roadtrip-mvp
```

## 📱 Mobile Commands
```bash
# Development
cd mobile && npm start

# Production Build
NODE_ENV=production eas build --platform all --profile production

# Security Check
npm run validate:env
npm run security:audit
```

## 🔐 Backend Commands
```bash
# Check logs
gcloud run services logs read roadtrip-backend --limit=50

# Update environment
gcloud run services update roadtrip-backend \
  --update-env-vars KEY=value

# Deploy new version
gcloud run deploy roadtrip-backend \
  --source . \
  --region us-central1
```

## 🧪 Quick Tests
```bash
# Test AI (currently broken)
curl -X POST https://roadtrip-mvp-792001900150.us-central1.run.app/api/v1/stories/generate \
  -H "Content-Type: application/json" \
  -d '{"location":{"latitude":37.7749,"longitude":-122.4194},"interests":["history"],"user_id":"test"}'

# Test Maps (should work)
curl -X POST https://roadtrip-mvp-792001900150.us-central1.run.app/api/v1/maps/search-nearby \
  -H "Content-Type: application/json" \
  -d '{"location":{"latitude":37.7749,"longitude":-122.4194},"radius":5000,"types":["restaurant"]}'
```

## 📊 Architecture
```
Mobile App (React Native)
    ↓
Backend API (FastAPI)
    ↓
Services:
- Vertex AI (Gemini 2.0) - BLOCKED
- Google Maps - ✅ Working
- PostgreSQL - ✅ Working
- Redis Cache - ✅ Working
```

## 💰 Costs
- **Current**: ~$200/month
- **At 10k users**: ~$1,850/month
- **Revenue**: 2-8% commission on bookings

## 🎯 Launch Timeline
1. **Fix AI** (1-2 days)
2. **Test Everything** (3-4 days)
3. **Mobile Build** (1 week)
4. **App Store** (2-3 weeks)
5. **Total**: 4-5 weeks to launch

## 🆘 If Something Breaks
```bash
# Check backend health
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# View error logs
gcloud run services logs read roadtrip-backend --limit=100 | grep ERROR

# Rollback
gcloud run services update-traffic roadtrip-backend \
  --to-revisions=PREVIOUS_REVISION=100
```

## 📝 Key Files
- **Truth**: `/PROJECT_TRUTH_2025.md`
- **Action Plan**: `/IMMEDIATE_ACTION_PLAN.md`
- **Backend Config**: `/backend/app/core/config.py`
- **Mobile Config**: `/mobile/src/config/api.ts`

---
**Remember**: We're 85% done. Just fix Vertex AI and ship it! 🚢