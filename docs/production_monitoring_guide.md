# Production Monitoring Guide

This guide covers the comprehensive monitoring setup for the AI Road Trip Storyteller production environment.

## Overview

Our monitoring stack provides:
- **Real-time metrics** with Prometheus
- **Visual dashboards** with Grafana
- **Alerting** via multiple channels
- **Log aggregation** with structured logging
- **Performance tracking** for all services

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Application │────▶│  Prometheus  │────▶│   Grafana   │
│  Metrics    │     │   (Metrics)  │     │(Dashboards) │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ Alert Manager│────▶│Slack/PD/Email│
                    └──────────────┘     └─────────────┘
```

## Setup Instructions

### 1. Deploy Monitoring Stack

```bash
# Using Docker Compose
docker-compose --profile monitoring up -d

# Or using Kubernetes
kubectl apply -f infrastructure/monitoring/
```

### 2. Configure Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'roadtrip-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
      
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 3. Import Dashboards

Dashboards are automatically provisioned from:
- `infrastructure/monitoring/grafana-dashboards.json`
- `infrastructure/monitoring/grafana-security-dashboard.json`

Manual import:
1. Navigate to Grafana (http://localhost:3000)
2. Go to Dashboards → Import
3. Upload JSON files or paste content

### 4. Configure Alerts

```bash
# Apply alert rules
kubectl apply -f infrastructure/monitoring/prometheus-alerts.yaml

# Configure Alert Manager
kubectl apply -f infrastructure/monitoring/alertmanager-config.yaml
```

## Key Metrics

### Application Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `http_request_duration_seconds` | API response time | p95 > 1s |
| `http_requests_total` | Request count by status | 5xx rate > 5% |
| `active_users_total` | Currently active users | - |
| `ai_request_duration_seconds` | AI service latency | p95 > 3s |
| `booking_conversion_rate` | Booking success rate | < 5% |

### Infrastructure Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `node_cpu_seconds_total` | CPU usage | > 80% |
| `node_memory_MemAvailable_bytes` | Available memory | < 15% |
| `node_filesystem_avail_bytes` | Disk space | < 15% |
| `up` | Service availability | = 0 |

### Business Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `booking_initiated_total` | Bookings started | - |
| `booking_completed_total` | Bookings completed | - |
| `revenue_total` | Total revenue | - |
| `commission_earned_total` | Commission earned | - |

### Security Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `auth_login_failed_total` | Failed login attempts | > 10/min |
| `security_incident_total` | Security incidents | > 5/min |
| `user_2fa_enabled` | Users with 2FA | - |
| `rate_limit_exceeded_total` | Rate limit violations | > 100/min |

## Dashboards

### 1. Production Overview Dashboard

**URL**: `/d/roadtrip-prod-overview`

Panels include:
- API Response Time (p95)
- Request Rate by Status
- Active Users
- Error Rate
- Database Connection Pool
- Top Slow Queries
- AI Service Response Time
- Booking Conversion Rate
- Redis Cache Hit Rate
- Request Latency Heatmap

### 2. Security Dashboard

**URL**: `/d/roadtrip-security`

Panels include:
- Failed Login Attempts
- 2FA Adoption Rate
- Active Threats
- Blocked IPs
- Authentication Events
- Security Events by Type
- Recent Security Incidents
- Rate Limiting
- Security Score

### 3. Custom Dashboards

Create custom dashboards for:
- Revenue tracking
- User journey analytics
- Infrastructure deep-dive
- Partner API performance

## Alert Configuration

### Alert Channels

1. **Slack** (Default)
   ```yaml
   webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   channel: #roadtrip-alerts
   ```

2. **PagerDuty** (Critical)
   ```yaml
   integration_key: YOUR_PAGERDUTY_KEY
   severity: critical
   ```

3. **Email** (Backup)
   ```yaml
   smtp_host: smtp.gmail.com:587
   smtp_auth_username: alerts@roadtrip.app
   ```

### Alert Routing

```yaml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default'
  routes:
  - match:
      severity: critical
    receiver: pagerduty
  - match:
      severity: warning
    receiver: slack
  - match:
      service: security
    receiver: security-team
```

## Log Monitoring

### Structured Logging

All logs follow this format:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "roadtrip-api",
  "request_id": "abc-123",
  "user_id": "user-456",
  "message": "Booking completed",
  "metadata": {
    "booking_id": "book-789",
    "provider": "opentable",
    "commission": 2.50
  }
}
```

### Log Queries

Common queries for troubleshooting:

```promql
# Error rate by service
sum(rate(log_entries_total{level="ERROR"}[5m])) by (service)

# Slow queries
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Failed bookings
sum(rate(booking_failed_total[1h])) by (provider, error_type)

# Security incidents
sum(security_incident_total) by (type, severity)
```

## Performance Monitoring

### SLIs (Service Level Indicators)

1. **Availability**: Percentage of successful requests
   ```promql
   sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
   ```

2. **Latency**: 95th percentile response time
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
   ```

3. **Error Rate**: Percentage of failed requests
   ```promql
   sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
   ```

### SLOs (Service Level Objectives)

- Availability: 99.9% (43.2 minutes downtime/month)
- Latency: p95 < 500ms, p99 < 1s
- Error Rate: < 0.1%

## Troubleshooting

### High CPU Usage

1. Check top consumers:
   ```promql
   topk(5, rate(process_cpu_seconds_total[5m]))
   ```

2. Identify endpoints:
   ```promql
   topk(10, sum(rate(http_request_duration_seconds_count[5m])) by (endpoint))
   ```

### Memory Leaks

1. Monitor memory growth:
   ```promql
   rate(process_resident_memory_bytes[1h])
   ```

2. Check for patterns:
   ```promql
   process_resident_memory_bytes - process_resident_memory_bytes offset 1h
   ```

### Database Issues

1. Connection pool status:
   ```promql
   db_connection_pool_used / db_connection_pool_size
   ```

2. Slow queries:
   ```promql
   topk(10, db_query_duration_seconds) by (query)
   ```

## Best Practices

### 1. Dashboard Design

- Keep dashboards focused (single purpose)
- Use consistent color schemes
- Include context in panel descriptions
- Set appropriate refresh intervals

### 2. Alert Tuning

- Start with conservative thresholds
- Use multi-window alerts to reduce noise
- Include runbooks in alert descriptions
- Test alerts regularly

### 3. Metric Naming

Follow Prometheus naming conventions:
- Use underscores, not dashes
- End counters with `_total`
- Use base units (seconds, bytes)
- Include unit in metric name

### 4. Retention Policies

- Metrics: 30 days (15s resolution)
- Logs: 7 days (searchable), 30 days (archive)
- Alerts: 90 days history
- Dashboards: Version controlled

## Integration Points

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
- name: Deployment Annotation
  run: |
    curl -X POST http://grafana:3000/api/annotations \
      -H "Authorization: Bearer $GRAFANA_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "dashboardId": 1,
        "tags": ["deployment", "v${{ github.run_number }}"],
        "text": "Deployed version ${{ github.sha }}"
      }'
```

### Health Checks

```python
@router.get("/health/metrics")
async def health_metrics():
    """Expose custom health metrics."""
    return {
        "db_healthy": await check_database(),
        "redis_healthy": await check_redis(),
        "ai_service_healthy": await check_ai_service(),
        "booking_providers_healthy": await check_booking_providers()
    }
```

## Maintenance

### Daily Tasks

- Review overnight alerts
- Check dashboard anomalies
- Verify backup completion
- Monitor error rates

### Weekly Tasks

- Review SLO compliance
- Tune alert thresholds
- Update runbooks
- Capacity planning review

### Monthly Tasks

- Dashboard cleanup
- Metric cardinality review
- Cost optimization
- Security audit

## Emergency Procedures

### Service Degradation

1. Check overview dashboard
2. Identify affected services
3. Review recent deployments
4. Check infrastructure metrics
5. Implement fixes or rollback

### Complete Outage

1. Verify monitoring stack is operational
2. Check infrastructure status
3. Review error logs
4. Coordinate with on-call team
5. Implement disaster recovery

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Monitoring Best Practices](https://sre.google/sre-book/monitoring-distributed-systems/)