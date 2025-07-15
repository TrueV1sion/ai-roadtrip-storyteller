# Cloud Armor & WAF Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying enterprise-grade DDoS protection and WAF security for the AI Road Trip Storyteller application on Google Cloud.

## Architecture

```
Internet → Cloud Armor → Global Load Balancer → Cloud Run
                ↓
        Security Policies:
        - DDoS Protection
        - WAF Rules (OWASP)
        - Rate Limiting
        - Geographic Filtering
        - Bot Protection
```

## Prerequisites

1. **Google Cloud Setup**:
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   
   # Initialize and authenticate
   gcloud init
   gcloud auth login
   gcloud config set project roadtrip-460720
   ```

2. **Terraform Setup**:
   ```bash
   # Install Terraform
   wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
   unzip terraform_1.5.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

3. **Required Permissions**:
   - Compute Security Admin
   - Load Balancer Admin
   - Monitoring Admin
   - Cloud Run Admin

## Deployment Steps

### 1. Configure Variables

```bash
cd infrastructure/terraform

# Create variables file
cat > terraform.tfvars <<EOF
project_id = "roadtrip-460720"
region = "us-central1"
environment = "production"

# Domain configuration
domain_name = "roadtripai.com"
subdomain = "api"
ssl_domains = ["api.roadtripai.com", "www.roadtripai.com"]

# Security settings
security_email = "security@roadtripai.com"
global_rate_limit = 1000
api_rate_limit = 100
expensive_endpoint_rate_limit = 20

# Optional: Geographic restrictions
blocked_countries = []  # Add country codes if needed

# Monitoring
notification_channels = []  # Add channel IDs after creating them
EOF
```

### 2. Initialize Terraform

```bash
terraform init

# Download providers
terraform providers
```

### 3. Plan Deployment

```bash
# Review the plan carefully
terraform plan -out=cloud_armor.tfplan

# Save plan for review
terraform show -json cloud_armor.tfplan > plan.json
```

### 4. Deploy Infrastructure

```bash
# Apply the configuration
terraform apply cloud_armor.tfplan

# This will create:
# - Cloud Armor security policies
# - Global HTTP(S) Load Balancer
# - SSL certificates
# - Backend services
# - Monitoring and alerting
```

### 5. Verify Deployment

```bash
# Check Cloud Armor policy
gcloud compute security-policies describe roadtrip-security-policy-production

# Check load balancer
gcloud compute url-maps describe roadtrip-url-map-production

# Get load balancer IP
terraform output load_balancer_ip

# Test health endpoint
curl -I https://api.roadtripai.com/health
```

### 6. Configure DNS

```bash
# Get the load balancer IP
LB_IP=$(terraform output -raw load_balancer_ip)

# Add DNS A record pointing to:
# api.roadtripai.com → ${LB_IP}
```

### 7. Enable Monitoring

```bash
# Create notification channels
gcloud alpha monitoring channels create \
  --display-name="Security Team Email" \
  --type=email \
  --channel-labels=email_address=security@roadtripai.com

# Get channel ID and update terraform.tfvars
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --filter="displayName='Security Team Email'" \
  --format="value(name)")

# Update notification_channels in terraform.tfvars
```

### 8. Test Security Features

```bash
# Test rate limiting
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://api.roadtripai.com/api/health
  sleep 0.1
done

# You should see 429 responses after hitting the rate limit

# Test WAF protection (DO NOT run against production!)
# curl "https://api.roadtripai.com/test?id=1' OR '1'='1"
# Should return 403 Forbidden
```

## Post-Deployment Tasks

### 1. Configure Alerts

```bash
# View security dashboard
echo "Security Dashboard: $(terraform output security_dashboard_url)"

# Test alerts
gcloud alpha monitoring policies list
```

### 2. Set Up Monitoring

```bash
# Install monitoring scripts
sudo cp infrastructure/security/scripts/*.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/*.sh

# Set up cron job for health checks
echo "*/5 * * * * /usr/local/bin/security_health_check.sh" | sudo crontab -
```

### 3. Configure Adaptive Security

```bash
# Create systemd service for adaptive security
sudo cat > /etc/systemd/system/adaptive-security.service <<EOF
[Unit]
Description=Adaptive Security Monitor
After=network.target

[Service]
Type=simple
User=security
Environment="PROJECT_ID=roadtrip-460720"
Environment="ENVIRONMENT=production"
ExecStart=/usr/local/bin/adaptive_security.sh daemon
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable adaptive-security
sudo systemctl start adaptive-security
```

## Mobile App Configuration

### Update Mobile App Headers

```javascript
// In mobile app API client
const apiClient = axios.create({
  baseURL: 'https://api.roadtripai.com',
  headers: {
    'User-Agent': `RoadTripApp/${version}`,
    'X-App-Version': version,
    'X-API-Key': API_KEY, // For premium endpoints
  },
});
```

### Handle Rate Limiting

```javascript
// Implement exponential backoff
async function makeRequest(config) {
  let retries = 0;
  while (retries < 3) {
    try {
      return await apiClient.request(config);
    } catch (error) {
      if (error.response?.status === 429) {
        const retryAfter = error.response.headers['retry-after'] || 60;
        await sleep(retryAfter * 1000);
        retries++;
      } else {
        throw error;
      }
    }
  }
}
```

## Security Best Practices

### 1. Regular Security Reviews

```bash
# Weekly security audit
/usr/local/bin/security_health_check.sh

# Review blocked traffic
gcloud logging read "jsonPayload.enforcedSecurityPolicy.outcome=DENY" \
  --freshness=7d \
  --format=json | jq -r '.jsonPayload.remoteIp' | \
  sort | uniq -c | sort -nr | head -20
```

### 2. Update Security Policies

```bash
# Add new rule via Terraform
# Edit infrastructure/terraform/cloud_armor.tf

# Apply changes
terraform plan -target=google_compute_security_policy.roadtrip_policy
terraform apply -target=google_compute_security_policy.roadtrip_policy
```

### 3. Emergency Response

```bash
# Keep emergency response script ready
/usr/local/bin/emergency_response.sh

# Document emergency contacts
echo "Security Lead: +1-XXX-XXX-XXXX" > /etc/security/contacts.txt
echo "On-Call Engineer: +1-XXX-XXX-XXXX" >> /etc/security/contacts.txt
```

## Troubleshooting

### Issue: SSL Certificate Not Provisioning

```bash
# Check certificate status
gcloud compute ssl-certificates describe roadtrip-ssl-cert-production

# Verify DNS is pointing to load balancer
dig api.roadtripai.com

# Force certificate renewal
gcloud compute ssl-certificates delete roadtrip-ssl-cert-production --quiet
terraform apply -target=google_compute_managed_ssl_certificate.roadtrip_cert
```

### Issue: High Latency

```bash
# Check backend health
gcloud compute backend-services get-health roadtrip-backend-service-production

# Review CDN performance
gcloud logging read "resource.type=http_load_balancer" \
  --format="table(jsonPayload.cacheDecision,jsonPayload.cacheLookup)" \
  --limit=100
```

### Issue: False Positives

```bash
# Identify false positives
gcloud logging read "jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
  httpRequest.userAgent=~'.*RoadTripApp.*'" \
  --freshness=1h

# Whitelist legitimate traffic
# Add to cloud_armor.tf and apply
```

## Rollback Procedures

### Complete Rollback

```bash
# Remove all security infrastructure
terraform destroy -target=google_compute_security_policy.roadtrip_policy
terraform destroy -target=google_compute_url_map.roadtrip_url_map

# Revert to direct Cloud Run access
gcloud run services update roadtrip-backend \
  --allow-unauthenticated
```

### Partial Rollback

```bash
# Disable specific rules
gcloud compute security-policies rules update RULE_PRIORITY \
  --security-policy=roadtrip-security-policy-production \
  --preview=true

# Or remove rules
gcloud compute security-policies rules delete RULE_PRIORITY \
  --security-policy=roadtrip-security-policy-production
```

## Maintenance Schedule

### Daily
- Monitor security dashboard
- Review alert notifications
- Check for anomalies

### Weekly
- Run security health check
- Review false positives
- Update whitelists if needed

### Monthly
- Full security audit
- Performance optimization
- Cost analysis
- Update security policies

### Quarterly
- Penetration testing
- Security policy review
- Update WAF rules
- Training and drills

## Support

For security incidents:
1. Run `/usr/local/bin/emergency_response.sh`
2. Contact security team
3. Follow incident response procedures
4. Document all actions taken

For general support:
- Security Dashboard: [URL from terraform output]
- Documentation: /infrastructure/security/
- Scripts: /infrastructure/security/scripts/