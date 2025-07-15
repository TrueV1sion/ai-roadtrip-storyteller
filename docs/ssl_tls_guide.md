# SSL/TLS Configuration Guide

This guide covers SSL/TLS setup for secure HTTPS connections in production.

## Overview

The AI Road Trip Storyteller uses industry-standard SSL/TLS configuration to ensure:
- **Encrypted connections** between clients and servers
- **Authentication** to prevent man-in-the-middle attacks
- **Data integrity** during transmission
- **SEO benefits** and user trust indicators

## SSL/TLS Architecture

```
┌─────────────┐  HTTPS   ┌──────────────┐  HTTP   ┌─────────────┐
│   Client    │─────────▶│ Load Balancer│────────▶│   Backend   │
│  (Mobile)   │    443   │  (SSL Term)  │   8000  │   (API)     │
└─────────────┘          └──────────────┘         └─────────────┘
                               │
                               ▼
                         ┌──────────────┐
                         │ Certificate  │
                         │  (Let's      │
                         │  Encrypt)    │
                         └──────────────┘
```

## Configuration by Platform

### 1. Cloud Run (Recommended)

Cloud Run automatically handles SSL/TLS termination:

```bash
# Deploy with automatic SSL
gcloud run deploy roadtrip-api \
    --image gcr.io/PROJECT_ID/roadtrip-api:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated

# Map custom domain with automatic SSL
gcloud run domain-mappings create \
    --service roadtrip-api \
    --domain api.roadtrip.app \
    --region us-central1
```

**Advantages:**
- Zero configuration required
- Automatic certificate provisioning and renewal
- Global anycast IP addresses
- Built-in DDoS protection

### 2. Kubernetes with cert-manager

For GKE or self-managed Kubernetes:

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Apply SSL configuration
kubectl apply -f infrastructure/ssl/kubernetes-ssl.yaml

# Verify certificate status
kubectl get certificate -n roadtrip-prod
```

### 3. Docker Compose (Development/Small Scale)

For single-server deployments:

```bash
# Generate certificates
sudo ./infrastructure/ssl/generate-certs.sh --letsencrypt

# Start services with SSL
docker-compose -f infrastructure/ssl/docker-compose-ssl.yml up -d

# Verify SSL is working
curl -I https://api.roadtrip.app
```

## SSL/TLS Configuration Details

### Security Headers

All deployments include these security headers:

```nginx
# HTTP Strict Transport Security (HSTS)
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload

# Prevent clickjacking
X-Frame-Options: DENY

# Prevent MIME type sniffing
X-Content-Type-Options: nosniff

# XSS Protection
X-XSS-Protection: 1; mode=block

# Referrer Policy
Referrer-Policy: strict-origin-when-cross-origin

# Content Security Policy
Content-Security-Policy: default-src 'self'; ...
```

### Cipher Suites

Modern cipher suite configuration (TLS 1.2+):

```
- ECDHE-ECDSA-AES128-GCM-SHA256
- ECDHE-RSA-AES128-GCM-SHA256
- ECDHE-ECDSA-AES256-GCM-SHA384
- ECDHE-RSA-AES256-GCM-SHA384
- ECDHE-ECDSA-CHACHA20-POLY1305
- ECDHE-RSA-CHACHA20-POLY1305
```

### Certificate Types

| Type | Use Case | Provider | Auto-Renewal |
|------|----------|----------|--------------|
| Let's Encrypt | Production | Free | Yes |
| Google-managed | Cloud Run | Free | Yes |
| Self-signed | Development | Manual | No |
| Commercial | Enterprise | Paid | Varies |

## Setup Instructions

### Prerequisites

1. **Domain Control**: Ability to update DNS records
2. **Port Access**: 80 and 443 open in firewall
3. **Valid Email**: For Let's Encrypt notifications

### Step 1: DNS Configuration

Point your domain to the server:

```bash
# A record for apex domain
api.roadtrip.app.    300    IN    A    35.241.20.123

# Or CNAME for subdomain
api.roadtrip.app.    300    IN    CNAME    roadtrip-api-abc123.a.run.app.
```

### Step 2: Generate Certificates

#### Option A: Let's Encrypt (Production)

```bash
# Automated setup
sudo ./infrastructure/ssl/generate-certs.sh --letsencrypt \
    --domain api.roadtrip.app \
    --email admin@roadtrip.app
```

#### Option B: Self-Signed (Testing)

```bash
# Quick setup for testing
./infrastructure/ssl/generate-certs.sh --self-signed \
    --domain api.roadtrip.app
```

### Step 3: Configure Application

Update backend settings:

```python
# backend/app/core/config.py
ENVIRONMENT = "production"
FORCE_HTTPS = True
SECURE_COOKIES = True
```

### Step 4: Deploy and Verify

```bash
# Deploy with SSL
docker-compose -f infrastructure/ssl/docker-compose-ssl.yml up -d

# Test SSL configuration
openssl s_client -connect api.roadtrip.app:443 -tls1_2

# Check SSL Labs rating
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.roadtrip.app
```

## Certificate Management

### Auto-Renewal Setup

For Let's Encrypt certificates:

```bash
# Test renewal
certbot renew --dry-run

# View renewal status
certbot certificates

# Force renewal (if needed)
certbot renew --force-renewal
```

### Manual Renewal Process

1. **Generate new certificate**
   ```bash
   certbot certonly --standalone -d api.roadtrip.app
   ```

2. **Update certificate files**
   ```bash
   cp /etc/letsencrypt/live/api.roadtrip.app/* /etc/nginx/ssl/
   ```

3. **Reload services**
   ```bash
   nginx -s reload
   ```

### Certificate Monitoring

Set up alerts for expiring certificates:

```yaml
# monitoring/cert-expiry-alert.yaml
alert: CertificateExpiringSoon
expr: ssl_cert_expiry_days < 30
for: 1h
annotations:
  summary: "SSL certificate expiring soon"
  description: "Certificate for {{ $labels.domain }} expires in {{ $value }} days"
```

## Troubleshooting

### Common Issues

1. **Certificate Not Trusted**
   - Check certificate chain is complete
   - Ensure intermediate certificates are included
   - Verify domain matches certificate

2. **Mixed Content Warnings**
   - Ensure all resources use HTTPS
   - Update hardcoded HTTP URLs
   - Check API calls use HTTPS

3. **Renewal Failures**
   - Verify port 80 is accessible
   - Check DNS still points to server
   - Review certbot logs: `/var/log/letsencrypt/`

4. **Performance Issues**
   - Enable OCSP stapling
   - Use session resumption
   - Implement HTTP/2

### Debug Commands

```bash
# Check certificate details
openssl x509 -in /etc/nginx/ssl/fullchain.pem -text -noout

# Verify certificate chain
openssl verify -CAfile /etc/nginx/ssl/chain.pem /etc/nginx/ssl/fullchain.pem

# Test SSL handshake
openssl s_client -connect api.roadtrip.app:443 -servername api.roadtrip.app

# Check cipher support
nmap --script ssl-enum-ciphers -p 443 api.roadtrip.app

# Monitor certificate expiry
echo | openssl s_client -servername api.roadtrip.app -connect api.roadtrip.app:443 2>/dev/null | openssl x509 -noout -dates
```

## Security Best Practices

### 1. Strong Configuration

- Use TLS 1.2 minimum (prefer 1.3)
- Disable weak ciphers
- Enable Perfect Forward Secrecy
- Implement HSTS with preload

### 2. Certificate Security

- Protect private keys (chmod 600)
- Use strong key size (2048-bit minimum)
- Implement Certificate Transparency
- Monitor for unauthorized certificates

### 3. Ongoing Maintenance

- Regular security scans
- Keep software updated
- Monitor for vulnerabilities
- Test disaster recovery

## Performance Optimization

### 1. Enable HTTP/2

```nginx
listen 443 ssl http2;
```

### 2. OCSP Stapling

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
```

### 3. Session Resumption

```nginx
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;
```

### 4. Early Data (0-RTT)

```nginx
ssl_early_data on;
```

## Mobile App Configuration

Update mobile app to enforce HTTPS:

```typescript
// mobile/src/config/api.ts
const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000'
  : 'https://api.roadtrip.app';

// Force certificate pinning (optional)
const certificateHashes = [
  'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
];
```

## Cost Considerations

| Solution | Certificate Cost | Infrastructure Cost | Complexity |
|----------|-----------------|---------------------|------------|
| Cloud Run | Free | ~$50/month | Low |
| Kubernetes | Free | ~$100/month | Medium |
| Traditional | Free-$200/year | ~$20/month | High |

## Compliance

SSL/TLS configuration meets requirements for:
- PCI DSS (payment processing)
- HIPAA (health information)
- GDPR (data protection)
- SOC 2 (security controls)

## Next Steps

1. **Choose deployment platform** (Cloud Run recommended)
2. **Configure DNS** for your domain
3. **Run setup script** for your platform
4. **Verify SSL rating** (target: A+)
5. **Set up monitoring** for certificate expiry
6. **Document renewal procedures** for your team

## Resources

- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [NGINX SSL Best Practices](https://nginx.org/en/docs/http/configuring_https_servers.html)