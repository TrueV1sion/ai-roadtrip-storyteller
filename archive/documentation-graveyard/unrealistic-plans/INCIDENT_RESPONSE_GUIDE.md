# AI Road Trip Storyteller - Incident Response Guide

## Quick Reference

**Incident Hotline**: +1-555-0123  
**Slack Channel**: #incidents  
**Status Page**: https://status.roadtripstoryteller.com  
**War Room Link**: https://meet.google.com/roadtrip-incident  

## Incident Classification

### Severity Levels

| Level | Impact | Response Time | Examples |
|-------|--------|---------------|----------|
| **SEV-1** | Complete outage or data loss | 15 min | API down, database failure, security breach |
| **SEV-2** | Major feature unavailable | 30 min | Booking system down, AI errors >50% |
| **SEV-3** | Partial degradation | 2 hours | Slow responses, minor features broken |
| **SEV-4** | Minimal impact | Next day | UI bugs, non-critical errors |

### Incident Types

1. **Availability**: Service downtime
2. **Performance**: Response time degradation
3. **Functionality**: Feature failures
4. **Security**: Breaches or vulnerabilities
5. **Data**: Corruption or loss

## Response Procedures

### 1. Detection & Alert (0-5 minutes)

#### Automated Detection
- Prometheus alerts → PagerDuty
- Cloud Monitoring → Slack
- Error budgets → Email

#### Manual Detection
- Customer reports
- Internal testing
- Partner notifications

#### Initial Actions
```bash
# Acknowledge alert
pd-cli incident acknowledge INCIDENT_ID

# Create Slack channel
/incident create "Brief description"

# Start timer
echo "Incident started at $(date)" > incident.log
```

### 2. Assessment (5-15 minutes)

#### Information Gathering
```bash
# Check service health
curl -s https://api.roadtripstoryteller.com/health | jq .

# Recent errors
gcloud logging read "severity>=ERROR" \
  --limit=100 \
  --format=json \
  --freshness=10m

# Current traffic
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --interval-end-time=now \
  --interval-duration=600s
```

#### Impact Analysis
- [ ] Number of users affected
- [ ] Features impacted
- [ ] Geographic scope
- [ ] Business impact (revenue, bookings)
- [ ] Data integrity risk

### 3. Communication (Ongoing)

#### Internal Communication

**Initial Alert** (within 5 min):
```
@here INCIDENT DECLARED
Severity: SEV-[1-4]
Issue: [Brief description]
Impact: [User impact]
Lead: [Your name]
Channel: #inc-[timestamp]
```

**Updates** (every 30 min):
```
UPDATE [Time]
Status: [Investigating/Mitigating/Monitoring]
Progress: [What's been done]
Next: [Next steps]
ETA: [If known]
```

#### External Communication

**Status Page Update** (within 15 min):
1. Go to https://status.roadtripstoryteller.com/admin
2. Create incident with clear title
3. Set affected components
4. Post initial update

**Customer Email** (if SEV-1 > 1 hour):
- Use template in `/templates/incident_customer_email.html`
- Get approval from VP Engineering
- Send via customer-comms@

### 4. Mitigation (15+ minutes)

#### Quick Wins

**1. Rollback Recent Changes**
```bash
# Check recent deployments
gcloud run revisions list \
  --service=roadtrip-api \
  --region=us-central1 \
  --limit=5

# Rollback
gcloud run services update-traffic roadtrip-api \
  --to-revisions=STABLE_REVISION=100 \
  --region=us-central1
```

**2. Scale Resources**
```bash
# Increase instances
gcloud run services update roadtrip-api \
  --max-instances=200 \
  --region=us-central1

# Increase database connections
gcloud sql instances patch roadtrip-db \
  --database-flags=max_connections=500
```

**3. Enable Circuit Breakers**
```bash
# Disable problematic features
gcloud run services update roadtrip-api \
  --update-env-vars="FEATURES_DISABLED=voice,booking"
```

**4. Clear Cache**
```bash
# Redis flush
redis-cli -h REDIS_IP FLUSHALL

# CDN purge
gcloud compute url-maps invalidate-cdn-cache roadtrip-url-map \
  --path="/*"
```

#### Specific Playbooks

**Database Issues**
```sql
-- Check connections
SELECT count(*) FROM pg_stat_activity;

-- Kill long queries
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'active' 
  AND now() - pg_stat_activity.query_start > interval '5 minutes';

-- Emergency connection pool
ALTER SYSTEM SET max_connections = 1000;
SELECT pg_reload_conf();
```

**API Overload**
```bash
# Enable rate limiting
gcloud compute security-policies rules update 2000 \
  --security-policy=roadtrip-waf-policy \
  --rate-limit-threshold-count=10 \
  --rate-limit-threshold-interval-sec=60

# Add caching headers
gcloud run services update roadtrip-api \
  --update-env-vars="CACHE_CONTROL_MAX_AGE=300"
```

**AI Service Failures**
```python
# Enable fallback mode in app
VERTEX_AI_FALLBACK_MODE = True
USE_CACHED_RESPONSES_ONLY = True
```

### 5. Resolution Verification

#### Synthetic Monitoring
```bash
# Run synthetic tests
./scripts/synthetic_tests.sh --comprehensive

# Check specific endpoints
for endpoint in health story/generate voice/personalities; do
  curl -w "%{http_code} %{time_total}s\n" \
    https://api.roadtripstoryteller.com/api/$endpoint
done
```

#### Real User Monitoring
```sql
-- Check error rates (last 5 min)
SELECT 
  date_trunc('minute', created_at) as minute,
  COUNT(CASE WHEN status_code >= 500 THEN 1 END) as errors,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(CASE WHEN status_code >= 500 THEN 1 END) / COUNT(*), 2) as error_rate
FROM api_logs
WHERE created_at > NOW() - INTERVAL '5 minutes'
GROUP BY 1
ORDER BY 1 DESC;
```

### 6. Incident Closure

#### Verification Checklist
- [ ] All alerts cleared
- [ ] Error rates normal (< 0.1%)
- [ ] Response times normal (p95 < 2s)
- [ ] All features functional
- [ ] No customer complaints (last 30 min)

#### Closure Actions
1. Update status page - mark resolved
2. Send final Slack update
3. Stop incident timer
4. Schedule post-mortem
5. Create JIRA tickets for action items

## Incident Commander Responsibilities

### During Incident
1. **Coordinate** - Direct team efforts
2. **Communicate** - Keep stakeholders informed
3. **Decide** - Make quick decisions
4. **Delegate** - Assign specific tasks
5. **Document** - Keep incident log

### Delegation Examples
- **Tech Lead**: Debug and implement fixes
- **SRE**: Monitor metrics and logs
- **Support**: Handle customer inquiries
- **Comms**: Update status page and stakeholders

### Decision Framework
1. **User Impact First** - Prioritize user-facing issues
2. **Stop Bleeding** - Mitigate before root cause
3. **Fail Safe** - Degrade gracefully
4. **Communicate Early** - Over-communicate

## Post-Mortem Process

### Timeline (Post-Incident)
- **Day 0**: Incident occurs
- **Day 1**: Create post-mortem doc
- **Day 2-3**: Gather data
- **Day 5**: Post-mortem meeting
- **Day 7**: Action items assigned
- **Day 14**: Follow-up on actions

### Post-Mortem Template

```markdown
# Incident Post-Mortem: [Title]

**Date**: [YYYY-MM-DD]
**Duration**: [X hours Y minutes]
**Severity**: SEV-[1-4]
**Author**: [Name]

## Summary
[2-3 sentence summary]

## Impact
- Users affected: [number/%]
- Features impacted: [list]
- Revenue impact: $[amount]
- SLA: [Met/Breached]

## Timeline
- HH:MM - Alert triggered
- HH:MM - Team responded
- HH:MM - Root cause identified
- HH:MM - Mitigation applied
- HH:MM - Incident resolved

## Root Cause
[Technical explanation]

## Contributing Factors
1. [Factor 1]
2. [Factor 2]

## What Went Well
- [Positive 1]
- [Positive 2]

## What Could Be Improved
- [Improvement 1]
- [Improvement 2]

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| [Action 1] | [Name] | [Date] |
| [Action 2] | [Name] | [Date] |

## Lessons Learned
[Key takeaways]
```

## Common Scenarios

### Scenario: API Returns 5XX Errors

**Symptoms**: High 500 error rate, alerts firing
**Common Causes**: Database overload, memory issues, deployment bug

**Response**:
```bash
# 1. Check recent deployments
gcloud run revisions list --service=roadtrip-api --limit=3

# 2. Check database
gcloud sql instances describe roadtrip-db | grep state

# 3. Check memory
gcloud run services describe roadtrip-api --format="get(spec.template.spec.containers[0].resources)"

# 4. Rollback if needed
gcloud run services update-traffic roadtrip-api --to-revisions=LAST_KNOWN_GOOD=100
```

### Scenario: Database Connection Exhausted

**Symptoms**: "too many connections" errors
**Common Causes**: Connection leak, traffic spike

**Response**:
```sql
-- 1. Check current connections
SELECT count(*), state, application_name 
FROM pg_stat_activity 
GROUP BY state, application_name;

-- 2. Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < current_timestamp - INTERVAL '10 minutes';

-- 3. Increase limit (emergency)
ALTER SYSTEM SET max_connections = 800;
SELECT pg_reload_conf();
```

### Scenario: AI Service Quota Exceeded

**Symptoms**: 429 errors from Vertex AI
**Common Causes**: Traffic spike, inefficient prompts

**Response**:
```bash
# 1. Check quota usage
gcloud compute project-info describe --format="flattened(quotas[].usage)"

# 2. Enable caching mode
gcloud run services update roadtrip-api \
  --update-env-vars="AI_CACHE_ONLY_MODE=true"

# 3. Request quota increase
gcloud compute project-info add-metadata \
  --metadata google-compute-default-service-account-email=EMAIL
```

### Scenario: Security Breach Suspected

**Symptoms**: Unusual activity, data access patterns
**Common Causes**: Compromised credentials, vulnerability

**Response**:
```bash
# 1. IMMEDIATE: Disable suspicious accounts
gcloud iam service-accounts disable suspicious@project.iam.gserviceaccount.com

# 2. Check access logs
gcloud logging read 'protoPayload.authenticationInfo.principalEmail!=""' \
  --limit=1000 \
  --format=json

# 3. Rotate all secrets
./scripts/emergency_secret_rotation.sh

# 4. Enable enhanced logging
gcloud run services update roadtrip-api \
  --update-env-vars="SECURITY_AUDIT_MODE=true"
```

## Tools and Resources

### Monitoring Dashboards
- **Grafana**: https://monitoring.roadtripstoryteller.com
  - System Overview
  - API Performance  
  - Database Health
  - AI Usage

### Debugging Tools
```bash
# Live logs
gcloud logging tail "resource.type=cloud_run_revision"

# Database query analysis
psql -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10"

# Traffic replay
vegeta attack -duration=30s -rate=100 -targets=targets.txt | vegeta report

# Trace analysis
gcloud trace traces list --limit=10
```

### Emergency Contacts
- **Google Cloud Support**: 1-855-817-1444
- **Security Team**: security@company.com
- **Legal**: legal@company.com
- **PR**: pr@company.com

## Training and Drills

### Monthly Incident Drills
- **GameDay**: Planned failures
- **Chaos Engineering**: Random failures
- **Tabletop Exercises**: Scenario planning

### Required Training
1. Incident Commander Training (quarterly)
2. Post-Mortem Writing (annually)
3. Communication Skills (annually)
4. Technical Deep Dives (monthly)

---

**Remember**: Stay calm, communicate clearly, and focus on user impact. We're all on the same team working toward resolution.