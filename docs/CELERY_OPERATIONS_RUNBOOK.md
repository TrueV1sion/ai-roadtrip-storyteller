# Celery Operations Runbook

## Overview
This runbook provides operational procedures for managing the Celery async processing system with Six Sigma quality controls.

## System Architecture

### Components
- **Redis Broker**: Message queue for task distribution
- **Celery Workers**: Process async tasks
- **Beat Scheduler**: Handles periodic tasks
- **Monitoring Stack**: Prometheus + Grafana dashboards

### Queue Structure
```
Priority Queues (1-10, higher = more important):
- booking (10): Payment processing, reservations
- voice_synthesis (7): Real-time voice generation
- notifications (6): User notifications
- ai_generation (5): Story generation
- image_processing (4): Image optimization
- analytics (3): Batch analytics
```

## Startup Procedures

### 1. Start Redis
```bash
# Check Redis status
redis-cli ping

# Start if not running
docker-compose up -d redis
```

### 2. Start Celery Workers
```bash
# Start worker with all queues
celery -A backend.app.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --queues=booking,ai_generation,voice_synthesis,notifications,analytics,default \
  -n worker1@%h

# Start specialized high-priority worker
celery -A backend.app.core.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --queues=booking,voice_synthesis \
  -n priority_worker@%h \
  --max-tasks-per-child=100
```

### 3. Start Beat Scheduler
```bash
# Only one beat instance should run
celery -A backend.app.core.celery_app beat \
  --loglevel=info \
  --pidfile=/var/run/celery/beat.pid
```

### 4. Start Flower (Monitoring)
```bash
celery -A backend.app.core.celery_app flower \
  --port=5555 \
  --url_prefix=flower
```

## Monitoring

### Key Metrics (Six Sigma Targets)

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Job Completion Rate | >99.9% | <99.5% |
| Queue Latency | <100ms | >500ms |
| Task Duration (AI) | <30s | >60s |
| Task Duration (Booking) | <5s | >10s |
| Worker Memory | <2GB | >3GB |
| Queue Depth | <100 | >500 |

### Health Check Endpoints
```bash
# API health
curl http://localhost:8000/api/v1/jobs/queue/stats

# Worker status
celery -A backend.app.core.celery_app inspect active

# Queue depths
celery -A backend.app.core.celery_app inspect stats
```

### Monitoring Commands
```bash
# Real-time queue monitoring
watch -n 1 'redis-cli llen celery:booking'

# Task failure rate
celery -A backend.app.core.celery_app events --dump

# Worker performance
celery -A backend.app.core.celery_app inspect stats
```

## Common Operations

### Scaling Workers

#### Scale Up (High Load)
```bash
# Add more workers
for i in {2..5}; do
  celery -A backend.app.core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=ai_generation,default \
    -n worker$i@%h &
done
```

#### Scale Down (Low Load)
```bash
# Graceful shutdown
celery -A backend.app.core.celery_app control shutdown

# Or specific worker
celery -A backend.app.core.celery_app control shutdown worker2@hostname
```

### Queue Management

#### Clear Stuck Tasks
```bash
# Purge specific queue
celery -A backend.app.core.celery_app purge -Q ai_generation

# Cancel specific task
celery -A backend.app.core.celery_app control revoke <task_id>

# Cancel with termination
celery -A backend.app.core.celery_app control revoke <task_id> --terminate
```

#### Requeue Failed Tasks
```python
# Python script to requeue
from backend.app.core.celery_app import celery_app
from backend.app.tasks.ai_enhanced import generate_story_with_status

# Get failed tasks
failed_tasks = celery_app.backend.get_many([...])

# Resubmit
for task_data in failed_tasks:
    generate_story_with_status.apply_async(
        args=task_data['args'],
        kwargs=task_data['kwargs'],
        priority=5
    )
```

### Priority Management

#### Emergency Priority Override
```bash
# Pause low-priority queues
celery -A backend.app.core.celery_app control cancel_consumer analytics
celery -A backend.app.core.celery_app control cancel_consumer image_processing

# Resume after emergency
celery -A backend.app.core.celery_app control add_consumer analytics
celery -A backend.app.core.celery_app control add_consumer image_processing
```

## Troubleshooting

### High Queue Latency

1. **Check queue depths**
```bash
redis-cli
> LLEN celery:booking
> LLEN celery:ai_generation
```

2. **Check worker availability**
```bash
celery -A backend.app.core.celery_app inspect active_queues
```

3. **Scale workers if needed**
```bash
# Add dedicated workers for backed-up queue
celery -A backend.app.core.celery_app worker \
  --queues=<backed_up_queue> \
  --concurrency=8 \
  -n emergency_worker@%h
```

### Memory Issues

1. **Check worker memory**
```bash
celery -A backend.app.core.celery_app inspect memdump
```

2. **Restart workers with child limits**
```bash
celery -A backend.app.core.celery_app worker \
  --max-tasks-per-child=50 \
  --max-memory-per-child=300000  # 300MB
```

### Task Failures

1. **Check failure reasons**
```bash
# View recent failures
celery -A backend.app.core.celery_app events --dump | grep -A5 "task-failed"
```

2. **Common fixes**:
- Timeout errors: Increase task time limits
- Memory errors: Reduce concurrency or add memory
- Connection errors: Check external service health

### Redis Connection Issues

1. **Check Redis connectivity**
```bash
redis-cli ping
redis-cli info clients
```

2. **Check connection pool**
```bash
redis-cli client list | wc -l
```

3. **Reset connections if needed**
```bash
redis-cli client kill type normal
```

## Deployment Procedures

### Zero-Downtime Deployment

1. **Pre-deployment**
```bash
# Stop beat scheduler (prevent new periodic tasks)
pkill -f "celery beat"

# Signal workers to finish current tasks
celery -A backend.app.core.celery_app control shutdown --timeout=300
```

2. **Deploy new code**
```bash
# Update application code
git pull origin main
pip install -r requirements.txt
```

3. **Start new workers**
```bash
# Start workers with new code
./scripts/start_celery_workers.sh

# Verify workers are running new version
celery -A backend.app.core.celery_app inspect report
```

4. **Resume beat scheduler**
```bash
celery -A backend.app.core.celery_app beat --detach
```

### Rollback Procedure

1. **Stop current workers**
```bash
celery -A backend.app.core.celery_app control shutdown
```

2. **Revert code**
```bash
git checkout <previous_version>
pip install -r requirements.txt
```

3. **Restart workers**
```bash
./scripts/start_celery_workers.sh
```

## Maintenance Tasks

### Daily
- Check queue health dashboard
- Review error rates
- Monitor completion rates

### Weekly
- Analyze job patterns
- Review slow task logs
- Clean up old job results

### Monthly
- Performance optimization review
- Capacity planning
- Update monitoring thresholds

## Emergency Contacts

- **On-Call Engineer**: Check PagerDuty
- **Platform Team**: #platform-oncall
- **Redis Support**: redis-support@company.com

## Alert Response

### Critical Alert: Queue Depth > 1000
1. Check worker status
2. Scale workers immediately
3. Investigate root cause
4. Consider rate limiting

### Critical Alert: Completion Rate < 99%
1. Check failure logs
2. Identify failing task types
3. Apply targeted fixes
4. Monitor recovery

### Critical Alert: Worker Memory > 3GB
1. Check for memory leaks
2. Restart affected workers
3. Reduce concurrency if needed
4. Investigate task memory usage