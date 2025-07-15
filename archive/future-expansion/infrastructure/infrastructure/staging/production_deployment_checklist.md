# Production Deployment Checklist

## Pre-Deployment Validation

### ✅ Staging Environment Validation
- [ ] All staging validation tests passed (staging_validation_suite.py)
- [ ] Staging has been running stable for at least 48 hours
- [ ] No critical errors in staging logs
- [ ] Performance metrics meet SLAs in staging

### ✅ Configuration Comparison
- [ ] Run staging_production_comparison.py
- [ ] All critical differences resolved
- [ ] Environment-specific configurations verified
- [ ] Secrets properly separated between environments

### ✅ Testing Completion
- [ ] Unit tests: 85%+ coverage
- [ ] Integration tests: All passing
- [ ] E2E tests: Core flows validated
- [ ] Load tests: 1000+ concurrent users handled
- [ ] Security scan: No critical vulnerabilities

### ✅ Documentation
- [ ] API documentation up to date
- [ ] Deployment guide reviewed
- [ ] Runbooks prepared
- [ ] Rollback procedures documented

## Deployment Preparation

### ✅ Infrastructure Readiness
- [ ] Production Terraform state backed up
- [ ] Database backup taken
- [ ] Current production metrics baseline captured
- [ ] Monitoring dashboards ready

### ✅ Team Readiness
- [ ] Deployment team identified
- [ ] On-call engineer assigned
- [ ] Communication plan in place
- [ ] Stakeholders notified

### ✅ Risk Mitigation
- [ ] Rollback script tested
- [ ] Database migration rollback prepared
- [ ] Feature flags configured
- [ ] Traffic splitting plan ready

## Deployment Steps

### 1. Pre-Deployment (T-1 hour)
- [ ] Final staging validation
- [ ] Freeze code changes
- [ ] Notify team of deployment start
- [ ] Verify all team members ready

### 2. Database Migration (T-30 min)
- [ ] Backup production database
- [ ] Run migration in transaction
- [ ] Verify migration success
- [ ] Test rollback procedure

### 3. Infrastructure Update (T-15 min)
- [ ] Apply Terraform changes
- [ ] Verify infrastructure updates
- [ ] Check service connectivity
- [ ] Validate SSL certificates

### 4. Application Deployment (T-0)
- [ ] Build production image
- [ ] Push to container registry
- [ ] Deploy with blue-green strategy
- [ ] Monitor deployment progress

### 5. Traffic Migration
- [ ] Route 5% traffic to new version
- [ ] Monitor error rates and latency
- [ ] Gradually increase traffic (25%, 50%, 100%)
- [ ] Full cutover when stable

## Post-Deployment Validation

### ✅ Immediate Checks (T+15 min)
- [ ] Health endpoints responding
- [ ] No spike in error rates
- [ ] Performance within SLAs
- [ ] All integrations functional

### ✅ Extended Monitoring (T+1 hour)
- [ ] User reports monitored
- [ ] Business metrics tracking
- [ ] Resource utilization normal
- [ ] No memory leaks detected

### ✅ Full Validation (T+4 hours)
- [ ] Run production smoke tests
- [ ] Verify all features working
- [ ] Check backup systems
- [ ] Validate monitoring alerts

## Rollback Criteria

Initiate rollback if ANY of the following occur:
- [ ] Error rate > 5% for 5 minutes
- [ ] Response time > 2x baseline
- [ ] Critical functionality broken
- [ ] Database corruption detected
- [ ] Security breach identified

## Rollback Procedure

1. **Immediate Actions**
   ```bash
   # Switch traffic back to previous version
   gcloud run services update-traffic roadtrip-backend \
     --to-revisions=PREVIOUS=100 \
     --region=us-central1
   ```

2. **Database Rollback** (if needed)
   ```bash
   # Restore from backup
   gcloud sql backups restore <BACKUP_ID> \
     --backup-instance=roadtrip-db-production
   ```

3. **Notify stakeholders**
   - Send rollback notification
   - Document issues encountered
   - Schedule post-mortem

## Success Criteria

Deployment is successful when:
- [ ] All validation tests pass
- [ ] Error rate < 0.1%
- [ ] Response time p95 < 1.5s
- [ ] No critical issues for 4 hours
- [ ] Stakeholder approval received

## Communication Plan

### Channels
- **Slack**: #deployment-status
- **Email**: deployment@roadtrip.app
- **War Room**: Google Meet link

### Updates Schedule
- T-1 hour: Deployment starting notification
- T+0: Deployment in progress
- T+30 min: Initial validation complete
- T+1 hour: Extended monitoring update
- T+4 hours: Final success/rollback decision

## Emergency Contacts

- **DevOps Lead**: +1-XXX-XXX-XXXX
- **Engineering Manager**: +1-XXX-XXX-XXXX
- **Database Admin**: +1-XXX-XXX-XXXX
- **Security Team**: security@roadtrip.app
- **Google Cloud Support**: [Support Case Link]

## Post-Deployment Tasks

### ✅ Within 24 hours
- [ ] Update status page
- [ ] Send success notification
- [ ] Archive deployment artifacts
- [ ] Update documentation

### ✅ Within 1 week
- [ ] Conduct post-mortem (if issues)
- [ ] Update runbooks with learnings
- [ ] Plan improvements
- [ ] Celebrate success! 🎉

---

**Remember**: 
- Stay calm under pressure
- Communicate frequently
- Don't hesitate to rollback
- Document everything
- Learn from each deployment