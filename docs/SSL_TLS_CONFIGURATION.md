# SSL/TLS Configuration Guide

**Last Updated:** December 14, 2024  
**Document Version:** 1.0  
**Security Level:** High Priority

## Overview

This guide covers SSL/TLS configuration for the Road Trip application, including certificate generation, nginx configuration, and security best practices.

## Table of Contents

1. [Certificate Generation](#certificate-generation)
2. [Nginx SSL Configuration](#nginx-ssl-configuration)
3. [Security Headers](#security-headers)
4. [Testing & Validation](#testing--validation)
5. [Monitoring & Renewal](#monitoring--renewal)
6. [Troubleshooting](#troubleshooting)

## Certificate Generation

### Production Certificates (Let's Encrypt)

Generate production certificates using the provided script:

```bash
# Generate certificates for all domains
sudo python scripts/generate_ssl_certificates.py \
  --env production \
  --email ops@roadtrip.app \
  --domains roadtrip.app www.roadtrip.app api.roadtrip.app admin.roadtrip.app \
  --setup-renewal \
  --dhparam

# For staging/testing
sudo python scripts/generate_ssl_certificates.py \
  --env staging \
  --email ops@roadtrip.app \
  --domains staging.roadtrip.app api-staging.roadtrip.app
```

### Development Certificates (Self-Signed)

For local development:

```bash
# Generate self-signed certificates
python scripts/generate_ssl_certificates.py \
  --env development \
  --self-signed \
  --domains localhost roadtrip.local api.roadtrip.local
```

### Certificate Files

After generation, certificates are stored in:
- **Production**: `/etc/letsencrypt/live/roadtrip.app/`
- **Development**: `./certs/localhost/`

Key files:
- `privkey.pem` - Private key (keep secure!)
- `fullchain.pem` - Certificate + intermediates
- `cert.pem` - Server certificate only
- `chain.pem` - Intermediate certificates

## Nginx SSL Configuration

### 1. Copy SSL Configuration

```bash
# Copy the SSL configuration
sudo cp config/nginx-ssl.conf /etc/nginx/sites-available/roadtrip-ssl

# Create symbolic link
sudo ln -s /etc/nginx/sites-available/roadtrip-ssl /etc/nginx/sites-enabled/

# Remove default site if exists
sudo rm -f /etc/nginx/sites-enabled/default
```

### 2. Generate DH Parameters

```bash
# Generate 2048-bit DH parameters (takes a few minutes)
sudo openssl dhparam -out /etc/letsencrypt/dhparam.pem 2048
```

### 3. Create Admin Password File

```bash
# Create admin password file
sudo htpasswd -c /etc/nginx/admin.htpasswd admin
```

### 4. Test and Reload Nginx

```bash
# Test configuration
sudo nginx -t

# If successful, reload
sudo systemctl reload nginx
```

## Security Headers

Our configuration includes comprehensive security headers:

### 1. Strict-Transport-Security (HSTS)
```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```
- Forces HTTPS for 2 years
- Includes all subdomains
- Ready for HSTS preload list

### 2. Content Security Policy (CSP)
```
Content-Security-Policy: default-src 'self' https:; ...
```
- Restricts resource loading
- Prevents XSS attacks
- Configured for our specific needs

### 3. Other Security Headers
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Privacy protection
- `Permissions-Policy` - Controls browser features

## Testing & Validation

### 1. Local Testing

Test SSL configuration:

```bash
# Basic test
python scripts/test_ssl_configuration.py --domain roadtrip.app

# Full scan with vulnerability tests
python scripts/test_ssl_configuration.py --domain roadtrip.app --full

# Test specific subdomains
python scripts/test_ssl_configuration.py --domain api.roadtrip.app
```

### 2. Online Testing Tools

After deployment, test with:

1. **SSL Labs**: https://www.ssllabs.com/ssltest/
   - Target: A+ rating
   - Tests protocols, ciphers, vulnerabilities

2. **Security Headers**: https://securityheaders.com/
   - Target: A+ rating
   - Tests all security headers

3. **Mozilla Observatory**: https://observatory.mozilla.org/
   - Comprehensive security scan
   - Best practices check

### 3. Expected Results

✅ **Pass Criteria**:
- SSL Labs: A or A+ rating
- Only TLS 1.2 and 1.3 enabled
- Strong cipher suites only
- Valid certificate chain
- OCSP stapling enabled
- All security headers present

❌ **Fail Criteria**:
- Any grade below B
- Weak protocols (SSL, TLS 1.0/1.1)
- Missing security headers
- Certificate warnings
- Vulnerability detected

## Monitoring & Renewal

### 1. Automatic Renewal

Certificates auto-renew via cron:

```bash
# View renewal cron job
sudo crontab -l | grep ssl-renewal

# Test renewal (dry run)
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal
```

### 2. Certificate Monitoring

Set up monitoring alerts:

```bash
# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/roadtrip.app/cert.pem -noout -dates

# Monitor with Prometheus (example)
# Add to prometheus.yml:
# - job_name: 'ssl_expiry'
#   metrics_path: /probe
#   params:
#     module: [tcp_tls]
#   static_configs:
#     - targets:
#       - roadtrip.app:443
```

### 3. Backup Certificates

Before any changes:

```bash
# Backup current certificates
sudo python scripts/generate_ssl_certificates.py \
  --backup \
  --domains roadtrip.app
```

## Troubleshooting

### Common Issues

#### 1. Certificate Not Trusted
```bash
# Check certificate chain
openssl s_client -connect roadtrip.app:443 -showcerts

# Verify intermediate certificates are included
```

#### 2. Mixed Content Warnings
```bash
# Check for HTTP resources
grep -r "http://" /var/www/roadtrip/
# Update all resources to use HTTPS or protocol-relative URLs
```

#### 3. Nginx Won't Start
```bash
# Check error log
sudo tail -f /var/log/nginx/error.log

# Common fixes:
# - Verify certificate paths exist
# - Check file permissions (nginx user must read)
# - Ensure ports 80/443 are free
```

#### 4. Let's Encrypt Rate Limits
```bash
# If hit rate limits, use staging environment
sudo certbot certonly --staging ...

# Or wait (limits reset weekly)
```

### SSL/TLS Best Practices

1. **Use Strong Ciphers Only**
   - Prioritize ECDHE and CHACHA20
   - Disable all legacy ciphers

2. **Enable OCSP Stapling**
   - Reduces latency
   - Improves privacy

3. **Implement CAA Records**
   ```bash
   # Add DNS CAA record
   roadtrip.app. CAA 0 issue "letsencrypt.org"
   ```

4. **Monitor Certificate Transparency**
   - Subscribe to CT logs
   - Get alerts for new certificates

5. **Regular Security Audits**
   - Monthly SSL Labs scans
   - Quarterly penetration testing
   - Annual security review

## Performance Optimization

### 1. HTTP/2 Configuration
Already enabled in our nginx config:
```nginx
listen 443 ssl http2;
```

### 2. SSL Session Caching
Configured for optimal performance:
```nginx
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;
```

### 3. OCSP Stapling
Reduces round trips:
```nginx
ssl_stapling on;
ssl_stapling_verify on;
```

## Deployment Checklist

- [ ] Generate production certificates
- [ ] Generate DH parameters
- [ ] Copy and enable nginx configuration
- [ ] Create admin password file
- [ ] Test nginx configuration
- [ ] Reload nginx
- [ ] Test with local script
- [ ] Verify HTTPS redirect works
- [ ] Check all security headers
- [ ] Test with SSL Labs
- [ ] Set up monitoring
- [ ] Document certificate expiration date
- [ ] Verify auto-renewal is configured

## Emergency Procedures

### Certificate Expired
```bash
# Quick renewal
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Rollback to Previous Certificate
```bash
# Restore from backup
sudo tar -xzf /opt/roadtrip/ssl-backups/roadtrip.app_20241214_120000.tar.gz \
  -C /etc/letsencrypt/live/
sudo systemctl reload nginx
```

### Complete SSL Reset
```bash
# Remove and regenerate everything
sudo certbot delete --cert-name roadtrip.app
sudo rm -rf /etc/letsencrypt/live/roadtrip.app/
# Re-run generation script
```

## Support

For SSL/TLS issues:
1. Check logs: `/var/log/nginx/error.log`
2. Run test script with `--full` flag
3. Contact DevOps team
4. Escalate to security team if needed

---

**Security Note**: Never commit private keys or certificates to version control. Always use secure channels when transferring certificate files.