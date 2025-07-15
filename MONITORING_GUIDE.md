# Monitoring & Observability Guide

## 📊 Complete Observability Stack

### Monitoring Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│   Prometheus    │────▶│    Grafana      │
│    Metrics      │     │  (Time Series)  │     │  (Dashboards)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
┌─────────────────┐     ┌───────▼─────────┐     ┌─────────────────┐
│   Application   │────▶│   Loki          │────▶│  Alert Manager  │
│     Logs        │     │ (Log Aggregator)│     │ (Notifications) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
┌─────────────────┐     ┌───────▼─────────┐
│  Distributed    │────▶│   Jaeger        │
│    Traces       │     │ (Trace Analysis)│
└─────────────────┘     └─────────────────┘
```

### Key Metrics (Golden Signals)

#### 1. Latency
- API Response Time (p50, p95, p99)
- Database Query Time
- Cache Hit Rate
- AI Processing Time

#### 2. Traffic
- Requests per second
- Active users
- API calls by endpoint
- Geographic distribution

#### 3. Errors
- 4xx/5xx rates
- Failed authentications
- API errors by type
- Mobile app crashes

#### 4. Saturation
- CPU utilization
- Memory usage
- Database connections
- Queue depth

### Dashboards

#### 1. Executive Dashboard
- Business KPIs
- User engagement
- Revenue metrics
- System health score

#### 2. API Performance
- Endpoint latencies
- Error rates
- Traffic patterns
- SLA compliance

#### 3. Infrastructure
- Resource utilization
- Scaling events
- Cost metrics
- Capacity planning

#### 4. Security
- Failed auth attempts
- Suspicious activities
- WAF blocks
- Threat detection

### Alert Configuration

#### Critical Alerts (P0)
```yaml
- alert: APIDown
  expr: up{job="backend-api"} == 0
  for: 1m
  severity: critical
  action: page

- alert: DatabaseDown
  expr: pg_up == 0
  for: 1m
  severity: critical
  action: page

- alert: HighErrorRate
  expr: error_rate > 0.05
  for: 5m
  severity: critical
  action: page
```

#### Warning Alerts (P1)
```yaml
- alert: HighLatency
  expr: http_request_duration_seconds{quantile="0.95"} > 1
  for: 10m
  severity: warning
  action: slack

- alert: LowCacheHitRate
  expr: cache_hit_rate < 0.8
  for: 15m
  severity: warning
  action: email
```

### Logging Standards

#### Log Levels
- **ERROR**: System errors requiring attention
- **WARN**: Potential issues
- **INFO**: Normal operations
- **DEBUG**: Detailed debugging (dev only)

#### Log Format
```json
{
  "timestamp": "2025-07-14T10:30:00Z",
  "level": "INFO",
  "service": "backend-api",
  "trace_id": "abc123",
  "user_id": "user456",
  "message": "API request processed",
  "metadata": {
    "endpoint": "/api/v1/stories/generate",
    "duration_ms": 145,
    "status_code": 200
  }
}
```

### Tracing

#### Trace Sampling
- Production: 1% sampling
- Errors: 100% sampling
- Slow requests: 100% sampling
- Development: 100% sampling

#### Key Traces
- API request lifecycle
- Database query execution
- AI model inference
- External API calls

### SLIs, SLOs, and SLAs

#### Service Level Indicators (SLIs)
- API availability
- Request latency
- Error rate
- Data freshness

#### Service Level Objectives (SLOs)
- Availability: 99.9% (43.2 min/month)
- Latency: 95% < 200ms
- Error Rate: < 0.1%
- AI Response: 95% < 2s

#### Service Level Agreements (SLAs)
- Uptime: 99.9% guaranteed
- Support: 24/7 for P0/P1
- Credits: Pro-rated for downtime

### Monitoring Checklist

#### Daily
- [ ] Check error rates
- [ ] Review overnight alerts
- [ ] Verify backup completion
- [ ] Check resource utilization

#### Weekly
- [ ] Review performance trends
- [ ] Analyze error patterns
- [ ] Update runbooks
- [ ] Capacity planning review

#### Monthly
- [ ] SLA compliance report
- [ ] Cost optimization review
- [ ] Security metrics review
- [ ] Incident post-mortems

### Runbooks

#### High CPU Usage
1. Check Grafana CPU dashboard
2. Identify resource-intensive queries
3. Scale horizontally if needed
4. Optimize code if pattern found

#### Database Slow Queries
1. Check slow query log
2. Run EXPLAIN on queries
3. Add indexes if needed
4. Consider query optimization

#### API Errors Spike
1. Check error logs in Loki
2. Identify error pattern
3. Check recent deployments
4. Rollback if necessary

### Access Information

#### Grafana
- URL: https://monitoring.roadtrip.app
- Default Dashboard: /d/roadtrip-overview

#### Prometheus
- URL: https://prometheus.roadtrip.app
- Retention: 15 days

#### Loki
- URL: https://loki.roadtrip.app
- Retention: 30 days

#### Jaeger
- URL: https://jaeger.roadtrip.app
- Retention: 7 days
