# Security Best Practices - AI Road Trip Storyteller

## Overview

This document outlines security best practices for developing, deploying, and maintaining the AI Road Trip Storyteller application. Following these practices will help prevent common vulnerabilities and ensure the security of user data.

## 1. Authentication & Authorization

### Password Security
- **Minimum Requirements**: 12+ characters, uppercase, lowercase, numbers, special characters
- **Hashing**: Use bcrypt with cost factor 12 or higher
- **Storage**: Never store passwords in plain text or reversible encryption
- **Reset Process**: Use secure tokens with expiration (15 minutes max)
- **History**: Prevent reuse of last 5 passwords

### Token Management
```python
# Good: Secure token generation
token = secrets.token_urlsafe(32)

# Bad: Predictable tokens
token = str(uuid.uuid4())  # UUIDs can be predictable
```

### Session Security
- Set secure session timeouts (30 minutes for standard, 5 minutes for admin)
- Regenerate session IDs on login/privilege changes
- Implement absolute session timeouts
- Store sessions server-side (Redis recommended)

### Multi-Factor Authentication (MFA)
- Implement TOTP-based 2FA for all users
- Require MFA for administrative actions
- Provide backup codes for account recovery
- Log all MFA events

## 2. Input Validation & Sanitization

### General Principles
1. **Never trust user input** - Validate everything
2. **Whitelist over blacklist** - Define what's allowed, reject everything else
3. **Validate on both client and server** - Client for UX, server for security
4. **Fail securely** - Reject invalid input, don't try to "fix" it

### Input Validation Examples
```python
# Email validation
def validate_email(email: str) -> bool:
    pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(pattern.match(email)) and len(email) <= 254

# Numeric input validation
def validate_party_size(size: int) -> bool:
    return 1 <= size <= 20  # Business logic limits

# Date validation
def validate_booking_date(date_str: str) -> bool:
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date >= datetime.now()  # No past bookings
    except ValueError:
        return False
```

### SQL Injection Prevention
```python
# Good: Parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE email = %s AND active = %s",
    (email, True)
)

# Bad: String concatenation
query = f"SELECT * FROM users WHERE email = '{email}'"  # NEVER DO THIS
```

### XSS Prevention
```python
# Server-side: Escape all user content
from markupsafe import escape

@app.route('/api/comment')
def get_comment():
    comment = get_user_comment()
    return {
        "content": escape(comment.content),
        "author": escape(comment.author)
    }

# React Native: Use Text component (auto-escapes)
<Text>{userContent}</Text>  // Safe
// Never use dangerouslySetInnerHTML
```

## 3. API Security

### Rate Limiting
```python
# Per-endpoint rate limits
RATE_LIMITS = {
    "/api/auth/login": (5, 300),  # 5 attempts per 5 minutes
    "/api/stories/generate": (10, 60),  # 10 per minute
    "/api/voice-assistant": (30, 60),  # 30 per minute
    "default": (60, 60)  # 60 per minute default
}
```

### API Authentication
- Use Bearer tokens in Authorization header
- Implement token expiration and refresh
- Log all authentication failures
- Use API keys for third-party integrations

### Request/Response Security
```python
# Set security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response
```

## 4. Data Protection

### Encryption at Rest
```python
# Encrypt sensitive fields
from cryptography.fernet import Fernet

class EncryptedField:
    def __init__(self, key):
        self.cipher = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, value: str) -> str:
        return self.cipher.decrypt(value.encode()).decode()
```

### Encryption in Transit
- Enforce HTTPS everywhere (HSTS)
- Use TLS 1.2 minimum
- Implement certificate pinning in mobile app
- Validate SSL certificates

### Sensitive Data Handling
```python
# Redact sensitive data in logs
def sanitize_for_logging(data: dict) -> dict:
    sensitive_fields = ['password', 'token', 'api_key', 'credit_card']
    sanitized = data.copy()
    
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = '[REDACTED]'
    
    return sanitized
```

## 5. Third-Party Integration Security

### API Key Management
```python
# Store API keys securely
import os
from google.cloud import secretmanager

def get_api_key(secret_name: str) -> str:
    """Retrieve API key from Google Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Never hardcode keys
# Bad: api_key = "sk-1234567890abcdef"
# Good: api_key = get_api_key("openai-api-key")
```

### OAuth Implementation
- Validate redirect URIs
- Use state parameter to prevent CSRF
- Implement PKCE for mobile OAuth
- Short-lived access tokens (1 hour max)

## 6. Mobile App Security

### React Native Security
```javascript
// Secure storage for sensitive data
import * as SecureStore from 'expo-secure-store';

// Store tokens securely
await SecureStore.setItemAsync('auth_token', token);

// Never store in AsyncStorage
// Bad: AsyncStorage.setItem('auth_token', token);
```

### API Communication
```javascript
// Certificate pinning
const api = axios.create({
  baseURL: 'https://api.roadtrip.app',
  httpsAgent: new https.Agent({
    ca: fs.readFileSync('./certs/ca.pem'),
    rejectUnauthorized: true
  })
});
```

### Code Security
- Enable ProGuard/R8 for Android
- Use iOS App Transport Security
- Implement jailbreak/root detection
- Obfuscate sensitive business logic

## 7. Infrastructure Security

### Docker Security
```dockerfile
# Run as non-root user
FROM python:3.9-slim

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Switch to non-root user
USER appuser

# Copy and run application
COPY --chown=appuser:appuser . /app
WORKDIR /app
CMD ["python", "main.py"]
```

### Environment Variables
```python
# Validate required environment variables
REQUIRED_ENV_VARS = [
    'SECRET_KEY',
    'DATABASE_URL',
    'REDIS_URL',
    'GOOGLE_MAPS_API_KEY'
]

def validate_environment():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")
```

### Database Security
```sql
-- Principle of least privilege
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON roadtrip.* TO 'app_user'@'localhost';

-- Never grant unnecessary privileges
-- Bad: GRANT ALL PRIVILEGES ON *.* TO 'app_user'@'%';
```

## 8. Logging & Monitoring

### Security Logging
```python
import logging
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type: str, user_id: str, details: dict):
    security_logger.warning({
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'details': sanitize_for_logging(details)
    })

# Log important security events
log_security_event('failed_login', user_id, {'attempts': 5})
log_security_event('privilege_escalation_attempt', user_id, {'target_role': 'admin'})
```

### Monitoring Alerts
Configure alerts for:
- Multiple failed login attempts (5+ in 5 minutes)
- Unusual API usage patterns
- Error rate spikes
- Unauthorized access attempts
- Data exfiltration patterns

## 9. Incident Response

### Preparation
1. **Incident Response Plan**: Document procedures
2. **Contact List**: Security team, legal, PR
3. **Forensics Tools**: Log aggregation, analysis tools
4. **Backup Strategy**: Regular, tested backups

### Detection & Analysis
```python
# Automated threat detection
def detect_suspicious_activity(user_id: str):
    recent_requests = get_user_requests(user_id, minutes=5)
    
    # Check for suspicious patterns
    if len(recent_requests) > 100:
        trigger_alert('excessive_requests', user_id)
    
    if has_sql_injection_attempts(recent_requests):
        trigger_alert('sql_injection_attempt', user_id)
        block_user_temporarily(user_id)
```

### Response Procedures
1. **Contain**: Isolate affected systems
2. **Investigate**: Determine scope and impact
3. **Remediate**: Fix vulnerabilities
4. **Recover**: Restore normal operations
5. **Review**: Post-incident analysis

## 10. Development Security

### Secure Coding Guidelines
```python
# Use type hints and validation
from typing import Optional
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        if not validate_email_format(v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 12:
            raise ValueError('Password too short')
        return v
```

### Code Review Checklist
- [ ] No hardcoded secrets
- [ ] Input validation on all user inputs
- [ ] Proper error handling (no stack traces)
- [ ] Authentication/authorization checks
- [ ] Rate limiting implemented
- [ ] Logging doesn't contain sensitive data
- [ ] SQL queries are parameterized
- [ ] Dependencies are up to date

### Dependency Management
```bash
# Regular dependency scanning
pip install safety
safety check

# Use specific versions
# Bad: requests>=2.0.0
# Good: requests==2.28.1

# Regular updates with testing
pip list --outdated
pip install --upgrade package_name
```

## 11. Security Testing

### Automated Security Tests
```python
import pytest
from security_audit.automated_security_tests import SecurityTester

@pytest.fixture
def security_tester():
    return SecurityTester(base_url="http://localhost:8000")

def test_sql_injection_protection(security_tester):
    """Test SQL injection prevention"""
    security_tester.test_sql_injection()
    assert all(r["passed"] for r in security_tester.results)

def test_xss_protection(security_tester):
    """Test XSS prevention"""
    security_tester.test_xss_vulnerabilities()
    assert all(r["passed"] for r in security_tester.results)
```

### Penetration Testing
- Conduct quarterly penetration tests
- Use both automated and manual testing
- Test from both authenticated and unauthenticated perspectives
- Include mobile app in scope
- Document and track all findings

## 12. Compliance

### Data Privacy (GDPR/CCPA)
```python
# Implement data deletion
@app.route('/api/users/me', methods=['DELETE'])
@require_auth
def delete_user_data(current_user):
    # Anonymize rather than delete for audit trail
    user.email = f"deleted_{user.id}@example.com"
    user.full_name = "Deleted User"
    user.is_active = False
    
    # Delete associated personal data
    delete_user_stories(user.id)
    delete_user_preferences(user.id)
    
    log_security_event('user_data_deleted', user.id, {})
    
    return {"message": "User data deleted"}
```

### Security Certifications
- Maintain SOC 2 Type II compliance
- Regular security audits
- Vulnerability disclosure program
- Security awareness training

## Quick Security Checklist

Before deploying any code:

- [ ] All user inputs validated and sanitized
- [ ] Authentication required for sensitive endpoints
- [ ] Rate limiting configured
- [ ] Security headers set
- [ ] Sensitive data encrypted
- [ ] Error messages don't leak information
- [ ] Dependencies updated and scanned
- [ ] Security tests pass
- [ ] Code reviewed for security issues
- [ ] Deployment uses HTTPS only

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)

## Contact

For security concerns or vulnerability reports:
- Email: security@roadtripapp.com
- PGP Key: [Public key fingerprint]
- Bug Bounty: https://roadtripapp.com/security/bounty