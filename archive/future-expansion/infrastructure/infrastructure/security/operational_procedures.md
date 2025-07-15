# Cloud Armor & WAF Operational Procedures

## Table of Contents
1. [Initial Deployment](#initial-deployment)
2. [Security Policy Management](#security-policy-management)
3. [Emergency Response Procedures](#emergency-response-procedures)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Regular Maintenance](#regular-maintenance)
6. [Troubleshooting](#troubleshooting)

## Initial Deployment

### Prerequisites
- Google Cloud Project with billing enabled
- Terraform installed (v1.0+)
- gcloud CLI configured
- Appropriate IAM permissions

### Deployment Steps

1. **Set up Terraform variables**:
```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

2. **Initialize Terraform**:
```bash
terraform init
```

3. **Plan the deployment**:
```bash
terraform plan -out=security.tfplan
```

4. **Apply the configuration**:
```bash
terraform apply security.tfplan
```

5. **Verify deployment**:
```bash
# Check Cloud Armor policy
gcloud compute security-policies describe roadtrip-security-policy-production

# Check load balancer
gcloud compute url-maps describe roadtrip-url-map-production

# Test endpoints
curl -I https://api.roadtripai.com/health
```

## Security Policy Management

### Adding New Rules

1. **Add rule via Terraform** (Recommended):
```hcl
# In cloud_armor.tf, add new rule
rule {
  action   = "deny(403)"
  priority = 5500  # Choose appropriate priority
  match {
    expr {
      expression = "request.headers['user-agent'].matches('.*BadBot.*')"
    }
  }
  description = "Block specific bot"
}
```

2. **Apply changes**:
```bash
terraform plan
terraform apply
```

### Updating Rate Limits

1. **Modify rate limit in Terraform**:
```hcl
# Update existing rule in cloud_armor.tf
rate_limit_threshold {
  count        = 200  # New limit
  interval_sec = 60
}
```

2. **Apply without disruption**:
```bash
terraform apply -target=google_compute_security_policy.roadtrip_policy
```

### Geographic Restrictions

1. **Add country to block list**:
```bash
# In variables_security.tf
variable "blocked_countries" {
  default = ["XX", "YY", "ZZ"]  # Add country codes
}
```

2. **Update policy**:
```bash
terraform apply
```

## Emergency Response Procedures

### Active DDoS Attack

1. **Enable emergency lockdown** (immediate):
```bash
# Enable the emergency rule
gcloud compute security-policies rules update 100 \
  --security-policy=roadtrip-security-policy-production \
  --preview=false

# This blocks all traffic temporarily
```

2. **Analyze attack pattern**:
```bash
# View recent logs
gcloud logging read "resource.type=http_load_balancer AND jsonPayload.enforcedSecurityPolicy.name!=null" \
  --limit=100 \
  --format=json

# Check top attacking IPs
gcloud logging read "resource.type=http_load_balancer" \
  --limit=1000 \
  --format="value(jsonPayload.remoteIp)" | sort | uniq -c | sort -nr | head -20
```

3. **Create targeted block rule**:
```bash
# Block specific IP range
gcloud compute security-policies rules create 150 \
  --security-policy=roadtrip-security-policy-production \
  --action=deny-403 \
  --src-ip-ranges=1.2.3.0/24 \
  --description="Emergency block for active attack"
```

4. **Disable emergency lockdown**:
```bash
gcloud compute security-policies rules update 100 \
  --security-policy=roadtrip-security-policy-production \
  --preview=true
```

### SQL Injection Attack

1. **Check attack logs**:
```bash
# Find SQL injection attempts
gcloud logging read 'resource.type="http_load_balancer" AND 
  jsonPayload.enforcedSecurityPolicy.outcome="DENY" AND 
  jsonPayload.enforcedSecurityPolicy.name=~".*sqli.*"' \
  --limit=50 \
  --format=json
```

2. **Update WAF sensitivity**:
```bash
# Temporarily increase protection
terraform apply -var="sql_injection_sensitivity=high"
```

### High Rate Limit Violations

1. **Identify legitimate traffic**:
```bash
# Check user agents and IPs hitting rate limits
gcloud logging read 'httpRequest.status=429' \
  --limit=100 \
  --format="csv(httpRequest.userAgent,jsonPayload.remoteIp)"
```

2. **Whitelist legitimate services**:
```bash
# Add to Terraform configuration
resource "google_compute_security_policy" "roadtrip_policy" {
  # ... existing config ...
  
  rule {
    action   = "allow"
    priority = 500
    match {
      expr {
        expression = "origin.ip in ['trusted.ip.address/32']"
      }
    }
    description = "Whitelist trusted service"
  }
}
```

## Monitoring and Alerting

### Dashboard Access

1. **Security Dashboard**:
```bash
# Get dashboard URL
terraform output security_dashboard_url

# Or directly access:
# https://console.cloud.google.com/monitoring/dashboards
```

2. **Cloud Armor Dashboard**:
```
https://console.cloud.google.com/net-security/securitypolicies
```

### Key Metrics to Monitor

1. **Request Rate**:
   - Normal: 100-1000 requests/minute
   - Warning: >5000 requests/minute
   - Critical: >10000 requests/minute

2. **Error Rates**:
   - 4xx errors: Should be <5%
   - 5xx errors: Should be <1%
   - 429 (rate limit): Monitor for spikes

3. **Latency**:
   - P50: <200ms
   - P95: <1000ms
   - P99: <2000ms

### Alert Response

1. **DDoS Alert**:
   - Check Cloud Armor adaptive protection status
   - Review attack patterns in dashboard
   - Enable additional rules if needed

2. **High Latency Alert**:
   - Check backend health
   - Review Cloud Run scaling
   - Check for attack patterns

3. **Security Policy Violation**:
   - Review blocked requests
   - Identify false positives
   - Adjust rules as needed

## Regular Maintenance

### Weekly Tasks

1. **Review Security Logs**:
```bash
# Export weekly security report
gcloud logging read "resource.type=cloud_armor_policy" \
  --freshness=7d \
  --format=json > weekly_security_report.json

# Analyze top blocked IPs
cat weekly_security_report.json | jq -r '.jsonPayload.remoteIp' | \
  sort | uniq -c | sort -nr | head -20
```

2. **Update Threat Intelligence**:
```bash
# Pull latest threat feeds (if integrated)
./scripts/update_threat_intel.sh
```

3. **Review False Positives**:
```bash
# Check for legitimate traffic being blocked
gcloud logging read 'jsonPayload.enforcedSecurityPolicy.outcome="DENY" AND 
  httpRequest.userAgent=~".*Mobile.*RoadTrip.*"' \
  --freshness=7d
```

### Monthly Tasks

1. **Security Policy Audit**:
   - Review all active rules
   - Remove obsolete rules
   - Update rate limits based on traffic patterns

2. **Performance Review**:
   - Analyze CDN hit rates
   - Review backend latencies
   - Optimize caching policies

3. **Cost Analysis**:
   - Review Cloud Armor costs
   - Analyze load balancer usage
   - Optimize based on traffic patterns

## Troubleshooting

### Common Issues

1. **Legitimate Users Blocked**:
```bash
# Check if specific IP is blocked
gcloud logging read "jsonPayload.remoteIp='USER_IP'" \
  --freshness=1h \
  --format=json

# Temporary whitelist
gcloud compute security-policies rules create 99 \
  --security-policy=roadtrip-security-policy-production \
  --action=allow \
  --src-ip-ranges=USER_IP/32 \
  --description="Temporary whitelist for investigation"
```

2. **Mobile App Traffic Blocked**:
```bash
# Check mobile app headers
gcloud logging read 'httpRequest.userAgent=~".*RoadTripApp.*" AND 
  httpRequest.status>=400' \
  --limit=50

# Ensure mobile app rule is active
gcloud compute security-policies rules describe 6000 \
  --security-policy=roadtrip-security-policy-production
```

3. **High False Positive Rate**:
```bash
# Analyze blocked legitimate traffic
gcloud logging read 'jsonPayload.enforcedSecurityPolicy.outcome="DENY"' \
  --freshness=1d \
  --format="csv(jsonPayload.enforcedSecurityPolicy.name,httpRequest.requestUrl)"

# Adjust sensitivity
terraform apply -var="waf_sensitivity=low"
```

### Performance Issues

1. **High Latency**:
```bash
# Check backend health
gcloud compute backend-services get-health roadtrip-backend-service-production

# Review load balancer logs
gcloud logging read "resource.type=http_load_balancer AND 
  httpRequest.latency>2" --limit=100
```

2. **CDN Not Caching**:
```bash
# Check cache hit rates
gcloud logging read 'resource.type="http_load_balancer" 
  jsonPayload.cacheDecision!=null' \
  --format="value(jsonPayload.cacheDecision)" | \
  sort | uniq -c
```

### Security Incidents

1. **Data Breach Attempt**:
   - Enable emergency lockdown
   - Capture all logs for forensics
   - Contact security team
   - Review and strengthen rules

2. **Persistent Attacker**:
   - Implement IP-based blocking
   - Enable reCAPTCHA challenges
   - Consider upgrading to Cloud Armor Plus

## Useful Commands

### Quick Status Check
```bash
# Overall health
./scripts/security_health_check.sh

# Active threats
gcloud logging read "severity>=WARNING AND 
  resource.type=cloud_armor_policy" \
  --freshness=1h
```

### Emergency Commands
```bash
# Block all traffic (emergency)
gcloud compute security-policies rules update 100 \
  --security-policy=roadtrip-security-policy-production \
  --preview=false

# Disable all custom rules (troubleshooting)
for i in {1000..8000}; do
  gcloud compute security-policies rules update $i \
    --security-policy=roadtrip-security-policy-production \
    --preview=true 2>/dev/null
done

# Enable basic protection only
terraform apply -var="security_level=basic"
```

### Monitoring Commands
```bash
# Real-time attack monitoring
gcloud alpha monitoring tail "resource.type=http_load_balancer AND 
  jsonPayload.enforcedSecurityPolicy.outcome=DENY"

# Export security metrics
gcloud monitoring read-time-series \
  --filter='metric.type="networksecurity.googleapis.com/https/request_count"' \
  --format=json > security_metrics.json
```