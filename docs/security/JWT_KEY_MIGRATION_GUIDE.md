# JWT Key Migration Guide

This guide explains how to migrate JWT keys from filesystem storage to Google Secret Manager for production security.

## Overview

JWT private keys should never be stored in the filesystem or version control. This migration moves them to Google Secret Manager, providing:

- Secure key storage with encryption at rest
- Access control via IAM policies
- Key rotation support
- Audit logging
- Automatic key versioning

## Prerequisites

1. Google Cloud project with Secret Manager API enabled
2. Service account with Secret Manager Admin role
3. Python environment with required dependencies

## Migration Steps

### 1. Generate New Keys (Fresh Installation)

If you're setting up a new environment without existing keys:

```bash
cd scripts/security
python generate_jwt_keys.py --project-id your-project-id
```

This will:
- Generate a new 4096-bit RSA key pair
- Store keys in Google Secret Manager
- Create a local backup (delete after verification)

### 2. Migrate Existing Keys

If you have existing JWT keys in `backend/app/core/keys/`:

```bash
cd scripts/security
python migrate_existing_keys.py --project-id your-project-id
```

Verify the migration:

```bash
python migrate_existing_keys.py --project-id your-project-id --verify-only
```

After verification, remove local keys:

```bash
python migrate_existing_keys.py --project-id your-project-id --delete-local
```

### 3. Update Application Code

The application uses a new `SecureJWTManager` that automatically loads keys from Secret Manager:

```python
# Old way (file-based)
from app.core.jwt_manager import jwt_manager

# New way (Secret Manager-based)
from app.core.jwt_secret_manager import secure_jwt_manager
```

The module maintains backward compatibility, so existing code using the convenience functions will continue to work.

### 4. Update Deployment Configuration

Ensure your Cloud Run service has the necessary IAM permissions:

```bash
gcloud run services update roadtrip-backend \
    --service-account=roadtrip-backend-sa@your-project.iam.gserviceaccount.com
```

Grant Secret Manager access:

```bash
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:roadtrip-backend-sa@your-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 5. Test the Migration

Run the following tests:

```python
# Test token creation
from app.core.jwt_secret_manager import create_access_token, decode_token

token = create_access_token(subject="test-user")
payload = decode_token(token)
assert payload["sub"] == "test-user"
```

## Key Rotation

Rotate keys periodically for enhanced security:

```bash
cd scripts/security
python rotate_jwt_keys.py --project-id your-project-id
```

This will:
- Generate a new key pair
- Update the current key for signing
- Keep old keys for validating existing tokens
- Remove keys older than the retention limit

## Secret Manager Structure

Keys are stored with the following naming convention:

- `roadtrip-jwt-key-metadata` - Metadata about all keys
- `roadtrip-jwt-private-key-{key-id}` - Private key for signing
- `roadtrip-jwt-public-key-{key-id}` - Public key for verification

## Environment-Specific Behavior

### Development
- Falls back to local key generation if Secret Manager unavailable
- Keys stored in `backend/app/core/keys/` (git-ignored)
- No Secret Manager required

### Production
- Secret Manager is mandatory
- No local key storage
- Keys cached in memory after first load
- Automatic retry on Secret Manager failures

## Security Best Practices

1. **Never commit keys to version control**
   - Add `backend/app/core/keys/` to `.gitignore`
   - Delete any historical commits containing keys

2. **Use strong key sizes**
   - Default: 4096 bits
   - Minimum: 2048 bits

3. **Rotate keys regularly**
   - Recommended: Every 90 days
   - Critical: After any security incident

4. **Monitor access logs**
   - Enable Cloud Audit Logs for Secret Manager
   - Alert on unauthorized access attempts

5. **Limit access**
   - Use least-privilege IAM policies
   - Separate service accounts for different environments

## Troubleshooting

### "JWT keys not found in Secret Manager"
- Ensure the project ID is correct
- Verify Secret Manager API is enabled
- Check service account permissions

### "Failed to initialize Secret Manager client"
- Verify Google Cloud credentials are configured
- Check network connectivity
- Ensure the google-cloud-secret-manager package is installed

### "Token validation failed after rotation"
- Old tokens remain valid until expiration
- Ensure all keys from metadata are loaded
- Check that the key ID in token header exists

## Rollback Procedure

If issues occur after migration:

1. Revert to the previous jwt_manager module
2. Restore local keys from backup
3. Investigate and fix issues
4. Retry migration

## Monitoring

Add these metrics to your monitoring:

- JWT creation success/failure rate
- Token validation errors
- Secret Manager API latency
- Key rotation events

## Next Steps

After successful migration:

1. Remove all local key files
2. Update documentation
3. Train team on new key rotation process
4. Set up automated key rotation
5. Configure alerts for key-related errors