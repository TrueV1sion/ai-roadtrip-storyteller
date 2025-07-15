# AI Road Trip Storyteller - Agent Protocol v2.0

## REAL WORLD DEPLOYMENT STANDARDS

This is NOT a simulation. Every line of code has real-world impact on production systems, costs money, and affects users.

### Core Principles

1. **NO INTERACTIVE PROMPTS - EVER**
   - Scripts must run in CI/CD pipelines
   - No `read`, `input()`, `Read-Host`, or `pause` commands
   - Use environment variables or command-line arguments

2. **FAIL FAST, FAIL LOUD**
   - Exit immediately on errors: `set -e` in bash
   - Return proper exit codes: 0 for success, non-zero for failure
   - Log errors clearly with context

3. **IDEMPOTENCY IS MANDATORY**
   - Running a script twice must produce the same result
   - Check if resources exist before creating
   - Never assume clean state

4. **SECURITY FIRST**
   - NEVER hardcode credentials
   - NEVER store secrets in plain text
   - NEVER pass secrets via command line
   - Use secret managers or environment variables

5. **ONE SCRIPT, ONE PURPOSE**
   - No duplicate functionality
   - Clear naming that describes what it does
   - Document at the top what it does and when to use it

### Script Standards

```bash
#!/bin/bash
# Script: deploy.sh
# Purpose: Deploy application to Google Cloud Run
# Usage: ./deploy.sh [environment] [project-id]
# CI/CD: Compatible - no interactive prompts

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Validate environment
if [[ -z "${CI:-}" ]]; then
    echo "WARNING: Not running in CI environment"
fi

# All config from environment or args
PROJECT_ID="${1:-${GCP_PROJECT_ID}}"
ENVIRONMENT="${2:-${DEPLOY_ENV:-staging}}"

# Validate required vars
if [[ -z "$PROJECT_ID" ]]; then
    echo "ERROR: PROJECT_ID not set" >&2
    exit 1
fi

# Actual work here...
```

### Testing Requirements

1. **Every script must be tested in CI/CD**
   - GitHub Actions workflow must exist
   - Must run without human intervention
   - Must handle errors gracefully

2. **Cross-platform compatibility**
   - Test on Linux (CI/CD standard)
   - Document platform requirements
   - Use POSIX-compliant shell features

### Code Review Checklist

Before ANY script is merged:

- [ ] Zero interactive prompts
- [ ] Proper error handling with exit codes
- [ ] All config from environment/args
- [ ] Idempotent operations
- [ ] Security review (no hardcoded secrets)
- [ ] CI/CD workflow exists and passes
- [ ] Documentation is clear
- [ ] No duplicate functionality

### Deployment Script Requirements

1. **Environment Detection**
   ```bash
   # Detect CI/CD environment
   if [[ -n "${GITHUB_ACTIONS:-}" ]] || [[ -n "${CI:-}" ]]; then
       INTERACTIVE=false
   else
       INTERACTIVE=true
   fi
   ```

2. **Non-Interactive Mode**
   ```bash
   # Force non-interactive for automation
   export DEBIAN_FRONTEND=noninteractive
   gcloud config set core/disable_prompts true
   ```

3. **Proper Logging**
   ```bash
   log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }
   log "INFO: Starting deployment to $ENVIRONMENT"
   ```

### Consequences for Non-Compliance

Scripts that violate these standards will be:
1. Rejected in code review
2. Reverted if merged
3. Rewritten by competent engineers

### Migration Plan

1. **Immediate**: Fix all production deployment scripts
2. **Week 1**: Remove all interactive prompts
3. **Week 2**: Consolidate duplicate scripts
4. **Week 3**: Add CI/CD tests for all scripts

This is not optional. This is the minimum bar for production-grade code.