# High Error Rate Runbook

## Alert: HighErrorRate

### Description
The error rate has exceeded 1% for more than 5 minutes.

### Impact
- Users experiencing failures
- Potential data loss
- Revenue impact

### Investigation Steps
1. Check error logs in Grafana
2. Identify error patterns
3. Check recent deployments
4. Review dependency health

### Remediation
1. If deployment-related, rollback
2. If dependency issue, check downstream services
3. If load-related, scale up
4. Apply hotfix if code issue

### Prevention
- Improve test coverage
- Implement canary deployments
- Add circuit breakers
