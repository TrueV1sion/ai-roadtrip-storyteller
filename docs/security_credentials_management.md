# Security Credentials Management

This document outlines the credential management practices implemented in the AI Road Trip Storyteller application to ensure secure handling of sensitive information.

## Overview

Proper credential management is a critical security concern for any application. We've implemented a comprehensive approach to ensure that sensitive information such as API keys, database credentials, and authentication secrets are handled securely throughout the application lifecycle.

## Credential Storage

### Backend (Server-side) Credentials

#### Google Secret Manager

For the backend application, we use Google Secret Manager as the primary secure storage for credentials:

- Database connection strings
- JWT signing keys
- API keys for external services (Google Maps, Vertex AI, etc.)
- OAuth client secrets

The application retrieves these secrets at runtime using the Google Cloud SDK, which authenticates using Application Default Credentials (ADC).

```python
# Example from config.py
def _get_secret(secret_id: str, project_id: str, version: str = "latest") -> Optional[str]:
    """Fetches a secret from Google Secret Manager."""
    if not project_id:
        logger.warning("Project ID not configured. Cannot fetch secrets.")
        return None
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except (NotFound, PermissionDenied) as e:
        logger.warning(f"Could not access secret '{secret_id}' in project '{project_id}': {e}. Check secret existence and permissions.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching secret '{secret_id}': {e}")
        return None
```

#### Environment Variables Fallback

For development environments or where Google Secret Manager is not available, we support environment variables as a fallback, loaded via:

- `.env` files (not committed to version control)
- Environment variables set in the deployment environment

### Mobile (Client-side) Credentials

For the mobile application, we use Expo's secure environment handling:

1. Environment variables are defined in the Expo configuration:

```javascript
// app.config.js
export default {
  // ...
  extra: {
    AZURE_TTS_KEY: process.env.EXPO_PUBLIC_AZURE_TTS_KEY,
    AWS_POLLY_KEY: process.env.EXPO_PUBLIC_AWS_POLLY_KEY,
    GOOGLE_TTS_KEY: process.env.EXPO_PUBLIC_GOOGLE_TTS_KEY,
    GOOGLE_AI_API_KEY: process.env.EXPO_PUBLIC_GOOGLE_AI_API_KEY,
    // ...
  }
}
```

2. Sensitive data is retrieved from the configuration and used securely:

```typescript
// env.ts
import Constants from 'expo-constants';
const extra = Constants.expoConfig?.extra || {};
export const AZURE_TTS_KEY = extra.AZURE_TTS_KEY as string || '';
```

### Infrastructure Credentials

For infrastructure defined with Terraform, we've implemented AWS Secrets Manager:

1. Sensitive values are defined as Terraform variables marked as sensitive:

```hcl
variable "db_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}
```

2. These values are stored securely in AWS Secrets Manager:

```hcl
resource "aws_secretsmanager_secret" "database_url" {
  name        = "roadtrip/database_url"
  description = "Database connection URL for the RoadTrip application"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
}
```

3. Applications access these secrets securely via environment variables provided by the container orchestration:

```hcl
secrets = [
  { 
    name = "DATABASE_URL", 
    valueFrom = aws_secretsmanager_secret_version.database_url.arn 
  },
  {
    name = "SECRET_KEY",
    valueFrom = aws_secretsmanager_secret_version.jwt_secret.arn
  }
]
```

## Secure Communication

All API keys and sensitive credentials are only transmitted over secure channels:

1. HTTPS for all API communications
2. Secure WebSockets for real-time features
3. Signed HTTPS URLs for media access

## Credential Rotation

We support secure credential rotation:

1. Database credentials can be rotated without application downtime
2. JWT signing keys can be rotated with a grace period for existing tokens
3. API keys for external services can be rotated with zero downtime

## Best Practices Implemented

1. **No Hardcoded Credentials**: No credentials are hardcoded in the application code
2. **Secure Storage**: All credentials are stored in secure credential managers
3. **Principle of Least Privilege**: Each credential has the minimum permissions necessary
4. **Audit Logging**: All credential access is logged for security monitoring
5. **Encryption**: All credentials are encrypted both in transit and at rest
6. **Separation of Environments**: Development, staging, and production environments use different credentials

## Security Validation

During our security review, we conducted a thorough scan for hardcoded credentials:

1. Identified instances of credentials in infrastructure code
2. Refactored sensitive values to use AWS Secrets Manager
3. Implemented secure environment variable handling
4. Removed all instances of hardcoded credentials
5. Added validation to prevent future credential leakage

## Developer Guidelines

When working with credentials:

1. **Never hardcode** credentials in application code
2. **Never commit** credentials to version control
3. **Always use** the provided credential management systems
4. For local development, use `.env` files that are `.gitignore`d
5. For new credentials, follow the established pattern for your tier:
   - Backend: Add to Google Secret Manager
   - Mobile: Add to Expo configuration
   - Infrastructure: Add to AWS Secrets Manager