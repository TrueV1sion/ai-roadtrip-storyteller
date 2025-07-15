# Service Down Runbook

## Alert: LowAvailability

### Description
Backend service is not responding to health checks.

### Impact
- Complete service outage
- All users affected
- Revenue loss

### Investigation Steps
1. Check service logs
2. Verify infrastructure health
3. Check recent changes
4. Review monitoring dashboards

### Remediation
1. Restart service
2. Check database connectivity
3. Verify environment variables
4. Scale horizontally if needed

### Prevention
- Implement health checks
- Set up auto-recovery
- Use multiple availability zones
