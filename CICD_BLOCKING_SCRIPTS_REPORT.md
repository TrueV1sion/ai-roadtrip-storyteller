# CI/CD Blocking Scripts Report

This report identifies all scripts in the codebase that contain interactive prompts, user confirmations, or blocking input operations that would break CI/CD pipelines.

## Summary

- **Total scripts with blocking operations**: 73+ files
- **Critical deployment scripts affected**: 15+ files
- **Languages affected**: Bash (.sh), Python (.py), PowerShell (.ps1), Batch (.bat)

## Critical Deployment Scripts with Blocking Operations

### 1. Shell Scripts (.sh)

#### High Priority - Deployment Scripts
1. **`/agent_taskforce/tools/deploy_production.sh`**
   - Line 129: `read -p "Do you want to apply these changes? (yes/no): " -n 3 -r`
   - **Impact**: Blocks production deployment waiting for terraform confirmation

2. **`/infrastructure/staging/deploy_staging.sh`**
   - Contains interactive prompts for deployment confirmation
   - **Impact**: Blocks staging deployments

3. **`/scripts/deployment/secure_production_deploy.sh`**
   - Contains confirmation prompts
   - **Impact**: Blocks secure production deployments

4. **`/scripts/deployment/rollback_deployment.sh`**
   - Contains rollback confirmation prompts
   - **Impact**: Blocks emergency rollbacks

#### Setup and Configuration Scripts
5. **`/setup_dev_environment.sh`**
   - Contains setup confirmations
   - **Impact**: Blocks automated development environment setup

6. **`/scripts/setup_production_secrets.sh`**
   - Contains secret setup prompts
   - **Impact**: Blocks automated secret configuration

7. **`/scripts/setup_api_keys.sh`**
   - Contains API key input prompts
   - **Impact**: Blocks automated API configuration

### 2. Python Scripts (.py)

#### High Priority - Deployment Scripts
1. **`/scripts/deployment/production_deployment_wizard.py`**
   - Line 100: `input(f"GCP Project ID [{default_project}]: ")`
   - Line 104: `input(f"Region [{default_region}]: ")`
   - Line 108: `input(f"Service name [{default_service}]: ")`
   - Line 121: `input("Create new project? (y/n): ")`
   - Line 147: `input("\nProceed with deployment? (y/n): ")`
   - **Impact**: Completely interactive wizard, blocks all automated deployments

2. **`/scripts/security/emergency_credential_rotation.py`**
   - Contains getpass prompts for credentials
   - **Impact**: Blocks automated credential rotation

3. **`/scripts/setup/setup_apis.py`**
   - Line 202: `input(f"   Enter {var}: ").strip()`
   - **Impact**: Blocks automated API setup

4. **`/scripts/setup/configure_production.py`**
   - Contains multiple input() calls for configuration
   - **Impact**: Blocks automated production configuration

### 3. PowerShell Scripts (.ps1)

1. **`/scripts/grant_iam_permissions.ps1`**
   - Line 86: `$confirm = Read-Host "Continue? (Y/N)"`
   - **Impact**: Blocks automated IAM permission grants

2. **`/backend/check_cloud_run_env.ps1`**
   - Contains Read-Host prompts
   - **Impact**: Blocks automated environment checks

3. **`/scripts/deployment/check_gcp_setup.ps1`**
   - Contains confirmation prompts
   - **Impact**: Blocks automated GCP setup verification

### 4. Batch Files (.bat)

1. **`/scripts/grant_iam_permissions.bat`**
   - Line 16: `pause`
   - **Impact**: Blocks execution waiting for key press

2. **`/infrastructure/staging/deploy_anyway.bat`**
   - Contains pause commands
   - **Impact**: Blocks automated staging deployments

3. **`/C:\Users\jared\OneDrive\Desktop\RoadTrip\*.bat`**
   - Multiple files with pause/choice commands
   - **Impact**: Blocks various automated operations

## Blocking Patterns Found

### Bash/Shell
- `read -p` - Interactive prompts
- `read variablename` - Variable input
- `select` - Menu selections
- Confirmation patterns: `[Yy]/[Nn]`, `yes/no`

### Python
- `input()` - User input
- `getpass.getpass()` - Password input
- `click.prompt()` - Click library prompts
- `click.confirm()` - Click confirmations
- `inquirer` - Interactive menus
- `questionary` - Interactive prompts

### PowerShell
- `Read-Host` - User input
- `Write-Host` with `?` - Confirmation prompts
- `-Confirm` parameter usage

### Batch
- `set /p` - Variable input
- `choice` - Menu selection
- `pause` - Wait for key press

## Recommendations for CI/CD Compatibility

### 1. Add Non-Interactive Flags
All deployment scripts should support a non-interactive mode:
```bash
# Example for shell scripts
if [ "$CI" = "true" ] || [ "$NON_INTERACTIVE" = "true" ]; then
    REPLY="yes"  # Auto-confirm
else
    read -p "Continue? (yes/no): " REPLY
fi
```

### 2. Environment Variable Overrides
Replace interactive prompts with environment variables:
```python
# Instead of:
project_id = input("Enter project ID: ")

# Use:
project_id = os.environ.get('GCP_PROJECT_ID') or input("Enter project ID: ")
```

### 3. Command-Line Arguments
Add CLI arguments to bypass prompts:
```python
parser.add_argument('--yes', '-y', action='store_true', 
                    help='Auto-confirm all prompts')
```

### 4. CI/CD Detection
Detect CI/CD environment and skip prompts:
```bash
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ]; then
    echo "Running in CI/CD mode - skipping confirmations"
    AUTO_CONFIRM=true
fi
```

### 5. Separate CI/CD Scripts
Create dedicated CI/CD versions of deployment scripts:
- `deploy_production.sh` → `deploy_production_ci.sh`
- Remove all interactive elements
- Use environment variables for all configuration

## Immediate Actions Required

1. **Priority 1**: Fix production deployment scripts
   - `/agent_taskforce/tools/deploy_production.sh`
   - `/scripts/deployment/production_deployment_wizard.py`

2. **Priority 2**: Fix staging and development setup scripts
   - `/infrastructure/staging/deploy_staging.sh`
   - `/setup_dev_environment.sh`

3. **Priority 3**: Fix security and credential scripts
   - `/scripts/grant_iam_permissions.ps1`
   - `/scripts/security/emergency_credential_rotation.py`

## Testing CI/CD Compatibility

To test if a script is CI/CD compatible:
```bash
# Set CI environment variable
export CI=true
export NON_INTERACTIVE=true

# Run script with timeout to detect hangs
timeout 30s ./your_script.sh
if [ $? -eq 124 ]; then
    echo "Script timed out - likely has blocking input"
fi
```