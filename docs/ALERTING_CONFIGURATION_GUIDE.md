# Alerting Configuration Guide

## Overview

The AI Road Trip Storyteller uses a multi-tier alerting system to ensure rapid response to production issues. This guide covers alert configuration, routing, and best practices.

## Alert Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Application │────▶│  Prometheus  │────▶│AlertManager │
│   Metrics   │     │    Rules     │     │   Router    │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                    ┌───────────────────────────┴────────────────┐
                    │                                            │
                    ▼                                            ▼
            ┌─────────────┐                            ┌─────────────┐
            │    Slack    │                            │  PagerDuty  │
            │  Channels   │                            │  (Critical) │
            └─────────────┘                            └─────────────┘
```

## Alert Severity Levels

### Critical (P1)
- **Response Time**: < 5 minutes
- **Channels**: PagerDuty + Slack #roadtrip-critical
- **Examples**:
  - Service down (availability < 99%)
  - Database connection pool exhausted
  - Security breach detected
  - Payment processing failures

### Warning (P2)
- **Response Time**: < 30 minutes
- **Channels**: Slack team channels
- **Examples**:
  - High error rate (> 5%)
  - Slow response times (p95 > 1s)
  - Low cache hit rate
  - Disk space < 15%

### Info (P3)
- **Response Time**: < 4 hours
- **Channels**: Slack #roadtrip-alerts
- **Examples**:
  - Deployment notifications
  - Certificate expiry warnings (> 30 days)
  - Scheduled maintenance reminders

## Alert Configuration

### 1. Slack Integration

```bash
# Set up Slack webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Configure channels in alertmanager-config.yaml
receivers:
  - name: 'default'
    slack_configs:
      - api_url: $SLACK_WEBHOOK_URL
        channel: '#roadtrip-alerts'
        title: 'AI Road Trip Alert'
        icon_emoji: ':rotating_light:'
```

### 2. PagerDuty Integration

```bash
# Set up PagerDuty integration
export PAGERDUTY_SERVICE_KEY="your-service-key"

# Create escalation policy in PagerDuty
# 1. On-call engineer (immediate)
# 2. Team lead (5 minutes)
# 3. CTO (15 minutes)
```

### 3. Email Configuration

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@roadtrip.app'
  smtp_auth_username: 'alerts@roadtrip.app'
  smtp_auth_password: '$SMTP_PASSWORD'
  smtp_require_tls: true
```

## Alert Rules

### Application Alerts

```yaml
# High Error Rate
- alert: HighErrorRate
  expr: |
    (sum(rate(http_requests_total{status=~"5.."}[5m]))
     / sum(rate(http_requests_total[5m]))) > 0.05
  for: 5m
  labels:
    severity: critical
    service: api
  annotations:
    summary: "High error rate: {{ $value | humanizePercentage }}"
    runbook: "https://wiki.roadtrip.app/runbooks/high-error-rate"

# Slow Response Time
- alert: SlowResponseTime
  expr: |
    histogram_quantile(0.95, 
      sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
    ) > 1.0
  for: 5m
  labels:
    severity: warning
    service: api
  annotations:
    summary: "Slow API responses: {{ $value }}s p95"
```

### Business Alerts

```yaml
# Low Booking Conversion
- alert: LowBookingConversion
  expr: |
    (sum(rate(booking_completed_total[1h]))
     / sum(rate(booking_initiated_total[1h]))) < 0.05
  for: 30m
  labels:
    severity: warning
    service: business
  annotations:
    summary: "Booking conversion: {{ $value | humanizePercentage }}"
    dashboard: "https://grafana.roadtrip.app/d/business-metrics"

# Revenue Drop
- alert: RevenueDropDetected
  expr: |
    rate(revenue_total[1h]) < 0.8 * rate(revenue_total[1h] offset 1w)
  for: 1h
  labels:
    severity: critical
    service: business
  annotations:
    summary: "Revenue dropped 20% compared to last week"
```

### Security Alerts

```yaml
# Failed Login Spike
- alert: FailedLoginSpike
  expr: sum(rate(auth_login_failed_total[5m])) > 10
  for: 5m
  labels:
    severity: warning
    service: security
  annotations:
    summary: "High failed login rate: {{ $value }}/sec"

# 2FA Bypass Attempts
- alert: TwoFactorBypassAttempts
  expr: sum(rate(auth_2fa_failed_total[5m])) > 20
  for: 5m
  labels:
    severity: critical
    service: security
  annotations:
    summary: "Possible 2FA bypass attempt"
    action: "Block source IPs immediately"
```

## Alert Routing

### Route Configuration

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  
  routes:
    # Critical alerts → PagerDuty
    - match:
        severity: critical
      receiver: pagerduty-critical
      group_wait: 10s
      repeat_interval: 30m
      
    # Security alerts → Security team
    - match:
        service: security
      receiver: security-team
      group_wait: 10s
      
    # Business alerts → Business team
    - match:
        service: business
      receiver: business-team
      repeat_interval: 6h
```

### Alert Grouping

Alerts are grouped to reduce noise:
- By alert name (same type of issue)
- By service (related components)
- By cluster (same environment)

## Runbooks

Each alert should have a runbook with:

### 1. Alert Context
```markdown
## Alert: HighErrorRate

**Severity**: Critical
**Service**: API
**Team**: Backend Engineering

## Description
The API error rate has exceeded 5% for more than 5 minutes.
```

### 2. Investigation Steps
```markdown
## Investigation

1. Check Grafana dashboard: https://grafana.roadtrip.app/d/api-overview
2. Review recent deployments: `kubectl rollout history deployment/api`
3. Check error logs: `kubectl logs -l app=api --tail=100`
4. Verify external dependencies (database, Redis, third-party APIs)
```

### 3. Remediation Actions
```markdown
## Actions

### Immediate Response
1. If deployment-related: `kubectl rollout undo deployment/api`
2. If database issues: Check connection pool metrics
3. If external API: Enable circuit breaker

### Follow-up
1. Create incident report
2. Update monitoring thresholds if needed
3. Schedule post-mortem
```

## Testing Alerts

### 1. Test Alert Routing
```bash
# Send test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "service": "test"
    },
    "annotations": {
      "summary": "This is a test alert"
    }
  }]'
```

### 2. Validate Alert Rules
```bash
# Check rule syntax
promtool check rules /etc/prometheus/rules/*.yml

# Test rule evaluation
promtool test rules test_alerts.yml
```

### 3. Silence Alerts During Maintenance
```bash
# Create silence via API
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "service", "value": "api"}
    ],
    "startsAt": "2024-01-15T10:00:00Z",
    "endsAt": "2024-01-15T12:00:00Z",
    "createdBy": "maintenance",
    "comment": "Scheduled maintenance window"
  }'
```

## On-Call Best Practices

### 1. Response Protocol
1. **Acknowledge** alert within SLA
2. **Assess** severity and impact
3. **Communicate** status in Slack
4. **Investigate** using runbook
5. **Remediate** following procedures
6. **Document** actions taken

### 2. Escalation Path
```
L1: On-call Engineer (0-5 min)
L2: Team Lead (5-15 min)
L3: Engineering Manager (15-30 min)
L4: CTO (30+ min)
```

### 3. Post-Incident Process
1. Create incident report within 24h
2. Schedule post-mortem within 48h
3. Update runbooks with learnings
4. Implement preventive measures

## Alert Tuning

### Reducing False Positives
1. **Adjust thresholds** based on historical data
2. **Add time windows** to avoid transient spikes
3. **Use percentiles** instead of averages
4. **Consider business hours** for non-critical alerts

### Example Tuning
```yaml
# Before: Too sensitive
expr: error_rate > 0.01
for: 1m

# After: More reasonable
expr: error_rate > 0.05
for: 5m
```

## Integration with CI/CD

### Deployment Annotations
```yaml
# Annotate deployments in Grafana
- name: Annotate Deployment
  run: |
    curl -X POST $GRAFANA_URL/api/annotations \
      -H "Authorization: Bearer $GRAFANA_API_KEY" \
      -d '{
        "dashboardId": 1,
        "tags": ["deployment", "v$VERSION"],
        "text": "Deployed version $VERSION"
      }'
```

### Automatic Silence During Deploy
```bash
# Create silence before deployment
./scripts/create_silence.sh --duration 30m --service api

# Deploy application
kubectl apply -f deployment.yaml

# Remove silence after validation
./scripts/remove_silence.sh --id $SILENCE_ID
```

## Monitoring the Monitors

### Alert Manager Health
```yaml
- alert: AlertManagerDown
  expr: up{job="alertmanager"} == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "AlertManager is down!"
```

### Dead Man's Switch
```yaml
- alert: DeadMansSwitch
  expr: vector(1)
  labels:
    severity: none
  annotations:
    summary: "Alerting pipeline is healthy"
```

## Compliance and Audit

### Alert History
- All alerts stored for 90 days
- Incident reports archived indefinitely
- PagerDuty logs retained for 1 year
- Slack messages retained per workspace policy

### Security Considerations
- Sanitize sensitive data in alerts
- Use secure webhooks (HTTPS only)
- Rotate integration keys quarterly
- Audit alert access monthly

## Resources

- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [AlertManager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PagerDuty Integration Guide](https://support.pagerduty.com/docs/prometheus)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)