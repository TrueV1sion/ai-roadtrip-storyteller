# Security Hardening Configuration

This document outlines the comprehensive security hardening measures implemented for the AI Road Trip Storyteller application.

## 1. Web Application Firewall (WAF)

### Cloud Armor Policy
- **Location**: `/infrastructure/security/cloud-armor-policy.yaml`
- **Protection Against**:
  - SQL Injection (SQLi)
  - Cross-Site Scripting (XSS)
  - Local/Remote File Inclusion (LFI/RFI)
  - Remote Code Execution (RCE)
  - Session Fixation
  - Protocol Attacks
  - Scanner/Bot Detection

### Rate Limiting
- 100 requests per minute per IP address
- 10-minute ban for violations
- Adaptive protection enabled for DDoS defense

### Geographic Restrictions
- Blocks traffic from high-risk countries (CN, RU, KP, IR)
- Can be customized based on business requirements

## 2. SSL/TLS Configuration

### SSL Policy
- **Minimum TLS Version**: TLS 1.2
- **Profile**: RESTRICTED (most secure)
- **Allowed Ciphers**:
  - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
  - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
  - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256

### HTTPS Configuration
- Automatic HTTP to HTTPS redirect
- Managed SSL certificates for all domains
- HSTS header with preload

### Security Headers
- **Strict-Transport-Security**: max-age=31536000; includeSubDomains; preload
- **X-Content-Type-Options**: nosniff
- **X-Frame-Options**: DENY
- **X-XSS-Protection**: 1; mode=block
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Content-Security-Policy**: Restrictive CSP policy
- **Permissions-Policy**: Minimal permissions (geolocation, microphone only)

## 3. Secret Management

### Automated Secret Rotation
- **Script**: `/scripts/security/secret-rotation.sh`
- **Rotation Period**: 90 days (configurable)
- **Supported Secrets**:
  - JWT secret keys
  - Database passwords
  - Redis passwords
  - Internal API keys
  - CSRF tokens
  - Encryption keys

### Secret Storage
- All secrets stored in Google Secret Manager
- Versioning enabled with 3 versions retained
- Automatic labeling with rotation metadata
- Integration with Cloud Run for automatic updates

### Manual Rotation Required
- External API keys (Google Maps, OpenWeather, etc.)
- Requires provider-specific procedures
- Notifications sent when rotation needed

## 4. Network Security

### Backend Configuration
- Cloud CDN enabled for DDoS protection
- Session affinity for voice streaming
- Custom request/response headers
- Connection draining (60 seconds)

### Health Checks
- HTTPS health checks every 10 seconds
- Automatic failover for unhealthy instances
- Multiple availability zones

## 5. Application Security

### Authentication & Authorization
- JWT tokens with refresh mechanism
- Two-factor authentication support
- CSRF protection on all state-changing operations
- Rate limiting per user and endpoint

### Input Validation
- Pydantic schemas for all API inputs
- SQL injection prevention via ORM
- XSS prevention in templates
- File upload restrictions

### Monitoring & Alerting
- Real-time threat detection
- Automated incident response
- Security event logging
- Integration with Cloud Security Command Center

## 6. Container Security

### Docker Configuration
```dockerfile
# Non-root user
RUN useradd -r -u 1001 appuser
USER 1001

# Minimal base image
FROM python:3.9-slim

# No unnecessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Read-only root filesystem
# Configured in Kubernetes deployment
```

### Kubernetes Security
- Pod Security Policies enforced
- Network Policies for traffic isolation
- Service mesh for mTLS between services
- Regular security scanning of images

## 7. Compliance & Best Practices

### Data Protection
- Encryption at rest (Cloud SQL, Cloud Storage)
- Encryption in transit (TLS 1.2+)
- PII data masking in logs
- GDPR compliance measures

### Access Control
- Principle of least privilege
- Service accounts with minimal permissions
- Regular access reviews
- Audit logging enabled

### Incident Response
- Automated alerting for security events
- Defined escalation procedures
- Regular security drills
- Post-incident analysis process

## 8. Implementation Checklist

### Immediate Actions
- [x] Deploy Cloud Armor WAF policy
- [x] Configure SSL/TLS settings
- [x] Set up secret rotation script
- [ ] Enable security headers in load balancer
- [ ] Configure network policies
- [ ] Set up security monitoring

### Scheduled Tasks
- [ ] Run secret rotation (monthly)
- [ ] Security audit (quarterly)
- [ ] Penetration testing (annually)
- [ ] Update WAF rules (as needed)

### Monitoring
- [ ] Set up security dashboards
- [ ] Configure alert channels
- [ ] Enable audit logging
- [ ] Implement SIEM integration

## 9. Emergency Procedures

### Security Incident Response
1. Detect and assess the incident
2. Contain the threat
3. Investigate root cause
4. Remediate vulnerabilities
5. Document lessons learned

### Emergency Contacts
- Security Team: security@roadtripstoryteller.com
- On-call Engineer: Use PagerDuty
- Google Cloud Support: Premium support ticket

### Rollback Procedures
1. Identify compromised components
2. Isolate affected services
3. Deploy last known good configuration
4. Verify service restoration
5. Conduct post-mortem analysis