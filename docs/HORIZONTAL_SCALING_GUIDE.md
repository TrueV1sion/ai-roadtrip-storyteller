# Horizontal Scaling Production Guide

## Overview

This guide covers the production-grade horizontal scaling implementation for the AI Road Trip Storyteller API. The system supports 4-20 pods with automatic scaling based on load.

## Architecture

### Components

1. **Gunicorn WSGI Server**
   - 4 async workers per pod (UvicornWorker)
   - Handles 3000+ RPS per pod
   - Graceful shutdown with 30s timeout
   - Worker lifecycle management

2. **Health Check System V2**
   - Liveness probe: `/health/v2/live`
   - Readiness probe: `/health/v2/ready`
   - Comprehensive status: `/health/v2/status`
   - Worker metrics: `/health/v2/metrics/worker`

3. **Kubernetes Orchestration**
   - Horizontal Pod Autoscaler (HPA)
   - Pod Disruption Budget (PDB)
   - Rolling updates with zero downtime
   - Session affinity for cache efficiency

## Configuration

### Gunicorn Settings

```python
# gunicorn_config.py key settings
workers = (2 * CPU_COUNT) + 1  # Optimal for I/O bound
worker_class = 'uvicorn.workers.UvicornWorker'
max_requests = 10000  # Prevent memory leaks
graceful_timeout = 30  # Allow requests to complete
preload_app = True  # Faster worker spawning
```

### Environment Variables

```bash
# Required
PORT=8080
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Optional tuning
GUNICORN_WORKERS=4  # Override worker count
LOG_LEVEL=info
ENVIRONMENT=production
```

### Kubernetes Resources

```yaml
# Resource allocation per pod
resources:
  requests:
    cpu: "1"      # Minimum 1 CPU
    memory: "2Gi"  # Minimum 2GB
  limits:
    cpu: "2"      # Maximum 2 CPU
    memory: "4Gi"  # Maximum 4GB
```

## Deployment

### Initial Deployment

```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/roadtrip-api:v1.0.0 .
docker push gcr.io/PROJECT_ID/roadtrip-api:v1.0.0

# Deploy to Kubernetes
kubectl apply -f deploy/k8s/roadtrip-deployment.yaml

# Verify deployment
kubectl get pods -l app=roadtrip-api
kubectl get hpa roadtrip-api-hpa
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/roadtrip-api \
  roadtrip-api=gcr.io/PROJECT_ID/roadtrip-api:v1.0.1

# Monitor rollout
kubectl rollout status deployment/roadtrip-api

# Rollback if needed
kubectl rollout undo deployment/roadtrip-api
```

### Manual Scaling

```bash
# Scale to specific replica count
kubectl scale deployment/roadtrip-api --replicas=8

# Temporary scale for high load
kubectl patch hpa roadtrip-api-hpa \
  -p '{"spec":{"minReplicas":8}}'
```

## Monitoring

### Key Metrics

1. **Request Rate**
   - Target: <3000 RPS per pod
   - Alert: >2500 RPS sustained

2. **Response Time**
   - Target: P99 <200ms
   - Alert: P99 >500ms

3. **CPU Usage**
   - Target: 60-80%
   - Scale up: >70% for 1 min
   - Scale down: <30% for 5 min

4. **Memory Usage**
   - Target: <3GB per pod
   - Alert: >3.5GB

5. **Worker Health**
   - All workers healthy
   - Active requests <100 per worker

### Prometheus Queries

```promql
# Request rate per pod
rate(http_requests_total[1m])

# P99 latency
histogram_quantile(0.99, 
  rate(http_request_duration_seconds_bucket[5m])
)

# Worker health status
worker_health_status{component="worker"}

# Active requests per worker
worker_active_requests
```

### Grafana Dashboard

Import dashboard ID: `roadtrip-scaling-v1`

Key panels:
- Request rate by pod
- Response time percentiles
- CPU/Memory by pod
- Worker health matrix
- Scaling events timeline

## Troubleshooting

### Common Issues

#### 1. Pods Not Ready

```bash
# Check pod status
kubectl describe pod <pod-name>

# Check readiness probe
kubectl logs <pod-name> | grep "ready"

# Common causes:
# - Database connection failed
# - Redis not accessible
# - Migrations pending
```

#### 2. High Memory Usage

```bash
# Check for memory leaks
kubectl top pods -l app=roadtrip-api

# Force worker restart
kubectl exec <pod-name> -- kill -HUP 1

# Reduce max_requests in gunicorn_config.py
```

#### 3. Uneven Load Distribution

```bash
# Check service endpoints
kubectl get endpoints roadtrip-api

# Verify session affinity
kubectl describe service roadtrip-api

# Test load distribution
for i in {1..100}; do
  curl -s http://roadtrip-api/health/v2/worker | \
    jq -r .worker_id
done | sort | uniq -c
```

#### 4. Scaling Not Working

```bash
# Check HPA status
kubectl describe hpa roadtrip-api-hpa

# Check metrics server
kubectl top nodes
kubectl top pods

# Manual test scaling
kubectl run -i --tty load-generator --rm \
  --image=busybox --restart=Never -- \
  /bin/sh -c "while sleep 0.01; do \
    wget -q -O- http://roadtrip-api/health; done"
```

## Performance Tuning

### Worker Optimization

```python
# For CPU-bound workloads
worker_class = 'sync'  # Use sync workers
threads = 4  # Multiple threads per worker

# For I/O-bound workloads (default)
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
```

### Database Connections

```python
# Scale pool with workers
pool_size = 20  # Per worker
max_overflow = 40  # Burst capacity
pool_pre_ping = True  # Verify connections
```

### Cache Optimization

```python
# Redis connection pool
max_connections = 100  # Total across workers
connection_pool_kwargs = {
    'max_connections': 100,
    'retry_on_timeout': True
}
```

## Load Testing

### Using Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class RoadtripUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health/v2/status")
    
    @task(10)
    def generate_story(self):
        self.client.post("/api/v1/stories/generate", json={
            "location": "San Francisco",
            "style": "adventure"
        })
```

```bash
# Run load test
locust -f locustfile.py \
  --host https://api.roadtrip.app \
  --users 1000 \
  --spawn-rate 10
```

### Expected Performance

| Pods | RPS Capacity | P99 Latency | Cost/Month |
|------|-------------|-------------|------------|
| 4    | 12,000      | <200ms      | $200       |
| 8    | 24,000      | <200ms      | $400       |
| 16   | 48,000      | <250ms      | $800       |
| 20   | 60,000      | <300ms      | $1000      |

## Best Practices

### 1. Graceful Shutdown

Always ensure graceful shutdown:
```python
# In your app
import signal

def handle_sigterm(*args):
    # Finish active requests
    # Close connections
    # Exit cleanly
    
signal.signal(signal.SIGTERM, handle_sigterm)
```

### 2. Health Checks

Implement comprehensive health checks:
```python
# Don't just return 200 OK
# Actually verify dependencies
async def health_check():
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_external_apis()
    )
    return all(checks)
```

### 3. Request ID Tracking

Track requests across workers:
```python
# Add to all log entries
logger.info("Processing request", extra={
    "request_id": request.headers.get("X-Request-ID"),
    "worker_id": os.getpid()
})
```

### 4. Circuit Breakers

Protect against cascading failures:
```python
from circuit_breaker import CircuitBreaker

@CircuitBreaker(failure_threshold=5, recovery_timeout=30)
async def external_api_call():
    # Call external service
    pass
```

## Maintenance

### Regular Tasks

- **Daily**: Check error rates and response times
- **Weekly**: Review scaling patterns and adjust HPA
- **Monthly**: Analyze cost vs performance
- **Quarterly**: Load test and capacity planning

### Monitoring Checklist

- [ ] All pods healthy
- [ ] Response time within SLA
- [ ] No memory leaks
- [ ] Database connections stable
- [ ] Cache hit rate >80%
- [ ] No stuck requests
- [ ] Scaling events normal

## Emergency Procedures

### High Load Event

1. **Immediate**: Scale to maximum pods
   ```bash
   kubectl scale deployment/roadtrip-api --replicas=20
   ```

2. **Enable rate limiting** (if not active)
   ```bash
   kubectl set env deployment/roadtrip-api \
     RATE_LIMIT_ENABLED=true
   ```

3. **Add more nodes** if needed
   ```bash
   gcloud container clusters resize roadtrip-cluster \
     --num-nodes=10
   ```

### Complete Outage

1. Check pod status and logs
2. Verify database connectivity
3. Check for poison pill requests
4. Roll back if recent deployment
5. Scale to single pod for debugging

## Contact

- **On-Call**: #roadtrip-oncall
- **Escalation**: platform-team@company.com
- **Runbooks**: wiki/roadtrip-runbooks