# Credential Rotation Guide for AI Road Trip Storyteller

## 🚨 CRITICAL: Immediate Action Required

Exposed credentials have been found in the codebase. Follow this guide immediately to secure your production deployment.

### Exposed Credentials (MUST ROTATE NOW):
- **Google Maps API Key**: `AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ`
- **Ticketmaster API Key**: `5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo`
- **OpenWeatherMap API Key**: `d7aa0dc75ed0dae38f627ed48d3e3bf1`

## 📋 Emergency Rotation Checklist

### Step 1: Run Emergency Rotation Script
```bash
cd /path/to/roadtrip
python scripts/security/emergency_credential_rotation.py
```

This script will:
- Disable exposed API keys (where possible)
- Generate new internal secrets (JWT, CSRF, encryption keys)
- Update Google Secret Manager
- Provide manual rotation instructions for external APIs

### Step 2: Complete Manual API Key Rotations

#### Google Maps API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select project: `roadtrip-460720`
3. Find the exposed key and delete it
4. Create a new API key with restrictions:
   - Application restrictions: HTTP referrers
   - Add: `https://roadtrip.app/*`, `https://*.roadtrip.app/*`
   - API restrictions: Maps JavaScript API, Places API, Directions API
5. Update Secret Manager:
   ```bash
   echo -n "YOUR_NEW_KEY" | gcloud secrets versions add roadtrip-google-maps-key --data-file=-
   ```

#### Ticketmaster API Key
1. Contact Ticketmaster Partner Support immediately
   - Email: apisupport@ticketmaster.com
   - Subject: "URGENT: API Key Compromise - Need Immediate Rotation"
   - Include your partner account details
2. Once you receive new credentials:
   ```bash
   echo -n "NEW_API_KEY" | gcloud secrets versions add roadtrip-ticketmaster-key --data-file=-
   ```

#### OpenWeatherMap API Key
1. Log in to [OpenWeatherMap](https://openweathermap.org/api_keys)
2. Generate a new API key named `roadtrip-prod-[date]`
3. Delete the old API key
4. Update Secret Manager:
   ```bash
   echo -n "NEW_API_KEY" | gcloud secrets versions add roadtrip-openweather-key --data-file=-
   ```

### Step 3: Update Configuration
```bash
# Update Secret Manager integration
python scripts/security/update_secret_manager_integration.py

# Validate security
python scripts/security/validate_credential_security.py
```

### Step 4: Deploy Updated Configuration
```bash
# Deploy to Cloud Run with new secrets
gcloud run deploy roadtrip-api \
  --image gcr.io/roadtrip-460720/roadtrip-api:latest \
  --region us-central1 \
  --project roadtrip-460720 \
  --update-env-vars "FORCE_SECRET_REFRESH=true"

# Verify deployment
curl https://api.roadtrip.app/health
```

## 🔐 Secret Manager Integration

### Configuration
All secrets are stored in Google Secret Manager with the following naming convention:
- `roadtrip-google-maps-key`
- `roadtrip-ticketmaster-key`
- `roadtrip-openweather-key`
- `roadtrip-database-url`
- `roadtrip-jwt-secret`
- `roadtrip-csrf-secret`
- `roadtrip-redis-url`
- `roadtrip-secret-key`
- `roadtrip-encryption-key`

### Access Secrets in Code
```python
from backend.app.core.secret_manager import secret_manager

# Get a secret
api_key = secret_manager.get_secret("roadtrip-google-maps-key")

# Verify all secrets are accessible
results = secret_manager.verify_all_secrets()
```

### Service Account Permissions
Ensure your service account has the following roles:
```bash
gcloud projects add-iam-policy-binding roadtrip-460720 \
  --member="serviceAccount:roadtrip-api@roadtrip-460720.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 🔄 Automated Rotation Setup

### Enable Automated Rotation
```bash
python scripts/security/setup_automated_rotation.py
```

This creates:
- Cloud Function for automated rotation
- Cloud Scheduler jobs with the following schedule:
  - Internal secrets: Every 3 months
  - Database credentials: Every 6 months
  - API key checks: Monthly (manual rotation required)

### Rotation Schedule
| Secret Type | Rotation Frequency | Method |
|------------|-------------------|---------|
| JWT Secret | 90 days | Automated |
| CSRF Secret | 90 days | Automated |
| Encryption Key | 90 days | Automated |
| Database Password | 180 days | Semi-automated |
| API Keys | As needed | Manual |

### Test Rotation
```bash
# Test internal secret rotation
gcloud scheduler jobs run rotate-internal-secrets --location=us-central1

# View rotation logs
gcloud logging read 'resource.labels.function_name="credential-rotation"' --limit=50
```

## 📊 Monitoring and Alerts

### Dashboard
Access the credential rotation dashboard:
1. Go to [Cloud Console](https://console.cloud.google.com)
2. Navigate to Monitoring > Dashboards
3. Select "Credential Rotation Dashboard"

### Metrics Tracked
- Rotation success rate
- Days since last rotation
- Failed rotation attempts
- Secret access patterns

### Alerts
Alerts are configured for:
- Rotation failures
- Secrets older than threshold
- Unauthorized access attempts
- Suspicious access patterns

## 🚨 Emergency Procedures

### Credential Compromise Response
1. **Immediate Actions**:
   ```bash
   # Disable compromised credentials
   python scripts/security/emergency_credential_rotation.py
   
   # Check for unauthorized usage
   gcloud logging read 'protoPayload.authenticationInfo.principalEmail!~"^serviceAccount"' --limit=100
   ```

2. **Rotate All Secrets**:
   ```bash
   # Force rotation of all internal secrets
   ./scripts/security/secret-rotation.sh --force-all
   ```

3. **Audit Access**:
   ```bash
   # Check recent secret access
   gcloud logging read 'resource.type="secretmanager.googleapis.com/Secret"' --limit=200
   ```

### Rollback Failed Rotation
If a rotation causes issues:
```bash
# Rollback specific secret
./scripts/security/rollback_credential.sh roadtrip-460720 roadtrip-jwt-secret

# Rollback to specific version
./scripts/security/rollback_credential.sh roadtrip-460720 roadtrip-jwt-secret 2
```

## 🛡️ Security Best Practices

### Development
1. **Never commit secrets to version control**
2. Use `.env` files locally (added to `.gitignore`)
3. Always use Secret Manager in production
4. Enable secret scanning in CI/CD

### Production
1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Regular Rotation**: Follow the rotation schedule
3. **Audit Logging**: Monitor all secret access
4. **Encryption at Rest**: All secrets are encrypted in Secret Manager
5. **Zero-Trust**: Verify identity for all secret access

### Code Review Checklist
- [ ] No hardcoded credentials
- [ ] All secrets accessed via Secret Manager
- [ ] Error handling for secret access failures
- [ ] No secrets in logs or error messages
- [ ] Proper secret caching (if implemented)

## 📝 Validation Commands

### Pre-Deployment Validation
```bash
# Validate no exposed credentials
python scripts/security/validate_credential_security.py

# Verify Secret Manager access
gcloud secrets list --project=roadtrip-460720

# Test secret access
gcloud secrets versions access latest --secret=roadtrip-jwt-secret
```

### Post-Deployment Validation
```bash
# Check service health
curl https://api.roadtrip.app/health

# Verify API functionality
curl https://api.roadtrip.app/api/v1/test-auth

# Monitor logs for errors
gcloud logging read 'severity>=ERROR' --limit=50
```

## 🔍 Troubleshooting

### Common Issues

#### Secret Access Denied
```bash
# Check service account permissions
gcloud projects get-iam-policy roadtrip-460720 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:roadtrip-api@*"

# Grant missing permissions
gcloud projects add-iam-policy-binding roadtrip-460720 \
  --member="serviceAccount:roadtrip-api@roadtrip-460720.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Rotation Failure
```bash
# Check Cloud Function logs
gcloud functions logs read credential-rotation --limit=50

# Manually trigger rotation
gcloud functions call credential-rotation \
  --data='{"secrets":["roadtrip-jwt-secret"]}'
```

#### Service Not Picking Up New Secrets
```bash
# Force service restart
gcloud run services update roadtrip-api \
  --region=us-central1 \
  --project=roadtrip-460720 \
  --clear-env-vars \
  --update-env-vars="FORCE_RELOAD=$(date +%s)"
```

## 📞 Support Contacts

### Internal
- Security Team: security@roadtrip.app
- DevOps Team: devops@roadtrip.app
- On-Call: +1-XXX-XXX-XXXX

### External API Support
- Google Cloud Support: [Console Support](https://console.cloud.google.com/support)
- Ticketmaster API: apisupport@ticketmaster.com
- OpenWeatherMap: support@openweathermap.org

## 📅 Next Steps

1. **Immediate** (Within 1 hour):
   - Complete emergency credential rotation
   - Deploy updated configuration
   - Verify service functionality

2. **Short-term** (Within 24 hours):
   - Set up automated rotation
   - Configure monitoring alerts
   - Document any custom rotation procedures

3. **Long-term** (Within 1 week):
   - Security audit of entire codebase
   - Implement secret scanning in CI/CD
   - Train team on security best practices

---

**Remember**: Security is everyone's responsibility. If you discover any exposed credentials or security issues, report them immediately to the security team.