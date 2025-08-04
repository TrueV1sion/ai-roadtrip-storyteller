# Final Production Deployment Checklist

## Pre-Deployment Verification ✓

### Code Readiness
- [x] All dependencies in requirements.txt
- [x] No import errors on startup
- [x] Gunicorn configuration fixed
- [x] Cloud Build configuration validated
- [x] All bare except blocks removed
- [x] Database transaction management implemented
- [x] Security headers hardened
- [x] JWT keys ready for Secret Manager

### Database
- [ ] Run latest migrations: `alembic upgrade head`
- [ ] Verify migration success
- [ ] Run consistency check: `python -c "from app.core.database_consistency import run_consistency_check"`
- [ ] Backup existing data (if applicable)

### Secrets & Configuration
- [ ] Generate JWT keys: `cd scripts/security && python generate_jwt_keys.py --project-id roadtrip-mvp`
- [ ] Run secret setup: `cd infrastructure/scripts && ./setup-secrets.sh roadtrip-mvp`
- [ ] Update critical secrets with real values:
  - [ ] DATABASE_URL (production connection string)
  - [ ] GOOGLE_MAPS_API_KEY
  - [ ] OPENWEATHERMAP_API_KEY
  - [ ] TICKETMASTER_API_KEY & SECRET
  - [ ] At least one booking partner API key
- [ ] Validate secrets: `./validate-secrets.sh roadtrip-mvp`

---

## Staging Deployment

### 1. Pre-Deployment Tests
```bash
# Test the application locally
cd backend
pip install -r requirements.txt
pytest tests/unit/
python -m app.main  # Verify startup
```

### 2. Deploy to Staging
```bash
# Use simplified config for initial deployment
gcloud builds submit \
  --config=backend/cloudbuild-prod-clean.yaml \
  --project=roadtrip-mvp \
  --substitutions=_SERVICE_NAME=roadtrip-backend-staging,_REGION=us-central1
```

### 3. Staging Verification
- [ ] Check deployment logs for errors
- [ ] Verify health endpoint: `curl https://roadtrip-backend-staging-[hash].run.app/health`
- [ ] Test core endpoints:
  - [ ] `/docs` - API documentation loads
  - [ ] `/api/v1/auth/test` - Auth endpoints work
  - [ ] `/api/v1/stories/test` - Story generation works
- [ ] Check monitoring dashboards
- [ ] Review application logs for errors

### 4. Performance Testing
- [ ] Run basic load test
- [ ] Verify AI operations complete within timeout
- [ ] Check database connection pooling
- [ ] Monitor memory usage

---

## Production Deployment

### 1. Final Pre-Production Checks
- [ ] All staging tests passed
- [ ] No critical errors in staging logs
- [ ] All required API keys are set (not placeholders)
- [ ] Database backup completed
- [ ] Rollback plan documented

### 2. Production Deployment
```bash
# Full-featured production deployment
gcloud builds submit \
  --config=backend/cloudbuild.yaml \
  --project=roadtrip-mvp \
  --substitutions=_SERVICE_NAME=roadtrip-backend,_REGION=us-central1
```

### 3. Production Verification
- [ ] Monitor deployment progress
- [ ] Check for any deployment errors
- [ ] Verify health endpoint
- [ ] Test critical user flows:
  - [ ] User registration
  - [ ] Login/authentication
  - [ ] Story generation
  - [ ] At least one booking integration
- [ ] Monitor error rates
- [ ] Check performance metrics

### 4. Post-Deployment
- [ ] Update DNS records (if needed)
- [ ] Configure monitoring alerts
- [ ] Document deployment details
- [ ] Notify team of successful deployment

---

## Rollback Procedure

If issues are detected:

1. **Immediate Rollback**:
```bash
gcloud run services update-traffic roadtrip-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --project=roadtrip-mvp \
  --region=us-central1
```

2. **Investigate Issues**:
- Check error logs
- Review monitoring dashboards
- Identify root cause

3. **Fix and Redeploy**:
- Apply fixes
- Test in staging first
- Redeploy to production

---

## Monitoring Setup

### Essential Alerts
- [ ] High error rate (>1% 5xx errors)
- [ ] High latency (p95 > 5 seconds)
- [ ] Database connection failures
- [ ] Memory usage > 80%
- [ ] Failed health checks

### Dashboards to Monitor
- [ ] Cloud Run metrics
- [ ] Error logs
- [ ] Database performance
- [ ] API response times
- [ ] External API integration status

---

## Mobile App Considerations

### Backend API Ready ✅
The backend is ready to support the mobile app with:
- Secure authentication endpoints
- Story generation APIs
- Booking integrations
- Voice personality support

### Mobile App Requirements 🚧
Before app store submission (4-5 weeks):
- [ ] Remove all console.log statements
- [ ] Implement secure API key storage
- [ ] Add certificate pinning
- [ ] Configure crash reporting (Sentry)
- [ ] Optimize bundle size
- [ ] Complete security audit
- [ ] Prepare app store assets

---

## Success Criteria

Deployment is successful when:
- [x] Backend deployed without errors
- [ ] All health checks passing
- [ ] No critical errors in first 24 hours
- [ ] Core features functional
- [ ] Performance within acceptable limits
- [ ] Monitoring and alerting operational

---

## Support Information

### Key Documentation
- API Documentation: `https://[YOUR_DOMAIN]/docs`
- Deployment Guide: `CLOUDBUILD_FIX_SUMMARY.md`
- Security Guide: `BACKEND_SECURITY_AUDIT_REPORT.md`
- Transaction Guide: `TRANSACTION_MANAGEMENT_GUIDE.md`

### Emergency Contacts
- DevOps Lead: [Contact]
- Backend Lead: [Contact]
- Security Lead: [Contact]

### Useful Commands
```bash
# View service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-backend" --limit=50

# Check service status
gcloud run services describe roadtrip-backend --region=us-central1

# Update environment variables
gcloud run services update roadtrip-backend --update-env-vars KEY=VALUE --region=us-central1
```

---

This checklist ensures a smooth deployment process with proper verification at each step.