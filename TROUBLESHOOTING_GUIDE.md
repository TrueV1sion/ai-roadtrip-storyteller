# Troubleshooting Guide

## 🔧 Production Troubleshooting Runbook

### Quick Diagnostics

#### System Health Check
```bash
# Check all services
./scripts/health-check.sh production

# Check specific service
curl https://api.roadtrip.app/health
curl https://api.roadtrip.app/api/v1/knowledge-graph/health

# Check database
psql $DATABASE_URL -c "SELECT version();"

# Check Redis
redis-cli -h $REDIS_HOST ping
```

### Common Issues & Solutions

#### 1. API Returns 500 Errors

**Symptoms**: Consistent 500 errors, high error rate in monitoring

**Diagnosis**:
```bash
# Check logs
gcloud logging read "resource.labels.service_name=roadtrip-backend severity>=ERROR" --limit=50

# Check database connection
gcloud sql operations list --instance=roadtrip-db

# Check memory usage
gcloud run services describe roadtrip-backend --region=us-central1
```

**Solutions**:
1. Database connection pool exhausted → Increase pool size
2. Memory limit reached → Scale up instances
3. Unhandled exception → Deploy hotfix
4. External API down → Enable circuit breaker

#### 2. Slow API Response Times

**Symptoms**: P95 latency > 1 second, user complaints

**Diagnosis**:
```bash
# Check slow queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check cache hit rate
redis-cli -h $REDIS_HOST INFO stats | grep hit_rate

# Check CPU usage
gcloud monitoring read "compute.googleapis.com/instance/cpu/utilization"
```

**Solutions**:
1. Slow DB queries → Add indexes
2. Low cache hit rate → Adjust TTL
3. High CPU → Scale horizontally
4. N+1 queries → Implement eager loading

#### 3. Authentication Failures

**Symptoms**: Users can't log in, 401 errors

**Diagnosis**:
```bash
# Check JWT keys
gcloud secrets versions list jwt-private-key

# Verify Redis is running (sessions)
redis-cli -h $REDIS_HOST DBSIZE

# Check auth logs
gcloud logging read "jsonPayload.endpoint=/api/v1/auth/login"
```

**Solutions**:
1. JWT key mismatch → Verify key rotation
2. Redis down → Restart Redis
3. Clock skew → Sync time
4. Rate limiting → Check IP limits

#### 4. Mobile App Can't Connect

**Symptoms**: App shows connection error, API unreachable

**Diagnosis**:
```bash
# Check CORS configuration
curl -H "Origin: https://app.roadtrip.app" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS https://api.roadtrip.app/api/v1/health

# Check SSL certificate
openssl s_client -connect api.roadtrip.app:443 -servername api.roadtrip.app
```

**Solutions**:
1. CORS misconfigured → Update allowed origins
2. SSL expired → Renew certificate
3. DNS issues → Check DNS records
4. Firewall blocking → Update rules

#### 5. Voice Features Not Working

**Symptoms**: Voice recognition fails, no audio output

**Diagnosis**:
```bash
# Check Google Cloud Speech API
gcloud services list --enabled | grep speech

# Check API quotas
gcloud alpha services quota list --service=speech.googleapis.com

# Check voice service logs
gcloud logging read "resource.labels.service_name=roadtrip-backend jsonPayload.service=voice"
```

**Solutions**:
1. API quota exceeded → Request increase
2. Invalid credentials → Update API key
3. Audio format issue → Check encoding
4. Network timeout → Increase timeout

#### 6. Database Connection Issues

**Symptoms**: Intermittent connection errors, timeouts

**Diagnosis**:
```bash
# Check connection count
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check for locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE granted='f';"

# Check Cloud SQL status
gcloud sql instances describe roadtrip-db
```

**Solutions**:
1. Connection limit → Increase max_connections
2. Long queries → Kill blocking queries
3. Network issues → Check VPC peering
4. Failover occurred → Verify replica promotion

### Performance Optimization

#### Database Optimization
```sql
-- Find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1
ORDER BY n_distinct DESC;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Check table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
```

#### Redis Optimization
```bash
# Check memory usage
redis-cli -h $REDIS_HOST INFO memory

# Find large keys
redis-cli -h $REDIS_HOST --bigkeys

# Check slow commands
redis-cli -h $REDIS_HOST SLOWLOG GET 10
```

### Emergency Procedures

#### Complete Service Down
1. **Immediate**: Switch to maintenance page
2. **Diagnose**: Check all health endpoints
3. **Communicate**: Update status page
4. **Fix**: Apply emergency patch
5. **Verify**: Run full test suite
6. **Post-mortem**: Document incident

#### Data Corruption
1. **Stop writes**: Enable read-only mode
2. **Backup**: Create immediate backup
3. **Identify**: Find corruption extent
4. **Restore**: From last good backup
5. **Verify**: Data integrity checks
6. **Prevent**: Add validation

#### Security Breach
1. **Isolate**: Disconnect affected systems
2. **Assess**: Determine breach scope
3. **Contain**: Patch vulnerability
4. **Notify**: Legal and users if needed
5. **Recover**: Restore from clean state
6. **Audit**: Full security review

### Monitoring Commands

#### Real-time Metrics
```bash
# Watch API requests
gcloud logging tail "resource.labels.service_name=roadtrip-backend" --format="value(jsonPayload)"

# Monitor CPU/Memory
watch gcloud run services describe roadtrip-backend --region=us-central1 --format="value(status.conditions)"

# Database connections
watch 'psql $DATABASE_URL -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"'
```

### Support Escalation

#### Level 1 (On-Call Engineer)
- Service restarts
- Scale adjustments
- Cache clearing
- Known issue fixes

#### Level 2 (Senior Engineer)
- Database issues
- Code deployment
- Architecture changes
- Performance tuning

#### Level 3 (CTO/Architect)
- Major outages
- Security incidents
- Data loss
- SLA breaches

### Post-Incident Checklist

- [ ] Service restored
- [ ] Root cause identified
- [ ] Fix deployed
- [ ] Monitoring added
- [ ] Documentation updated
- [ ] Team notified
- [ ] Customer communication
- [ ] Post-mortem scheduled
