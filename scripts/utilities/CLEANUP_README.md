# Codebase Cleanup Utilities

## Overview

These utilities help maintain a clean, production-ready codebase by removing unnecessary files, reorganizing structure, and verifying integrity.

## Scripts

### 1. `cleanup_workflow.sh` - Master Cleanup Workflow
The main entry point that orchestrates the entire cleanup process safely.

**Usage:**
```bash
./scripts/utilities/cleanup_workflow.sh
```

**What it does:**
1. Verifies current codebase integrity
2. Creates a backup git branch
3. Runs cleanup in dry-run mode first
4. Executes actual cleanup (with confirmation)
5. Verifies integrity after cleanup
6. Runs basic tests

### 2. `cleanup_codebase.py` - Cleanup Execution
The main cleanup script that removes unnecessary files and reorganizes structure.

**Usage:**
```bash
# Dry run mode (default)
python scripts/utilities/cleanup_codebase.py

# Live mode (actually modifies files)
python scripts/utilities/cleanup_codebase.py
# Then type 'n' when prompted for dry run
```

**What it removes:**
- Redundant planning documents (~20 files)
- Archive directory (historical files)
- Test files not in test suite
- Unused demo HTML files
- Temporary files (__pycache__, .pyc, etc.)
- Redundant deployment scripts
- Credentials directories (should use secret management)
- Duplicate main.py variants (moves to main_variants/)

### 3. `verify_codebase_integrity.py` - Integrity Verification
Verifies that all critical dependencies and imports work correctly.

**Usage:**
```bash
python scripts/utilities/verify_codebase_integrity.py
```

**What it checks:**
- Critical files exist
- Python imports resolve
- Docker builds reference valid files
- Database migrations are present
- Tests can be discovered
- API endpoints are properly structured
- Documentation links are valid

## Safety Features

1. **Backup Creation**: Always creates a backup before cleanup
2. **Dry Run Mode**: Shows what would be changed without modifying
3. **Git Branch**: Creates a backup branch before changes
4. **Confirmation Prompts**: Multiple confirmations before destructive actions
5. **Integrity Checks**: Verifies codebase before and after cleanup
6. **Detailed Logging**: Creates timestamped log of all changes

## What Gets Cleaned

### Files Removed (~150+ files)
- Planning documents (moved to git history)
- Archive directory (backed up first)
- Redundant test files in root
- Old demo files
- Temporary/cache files
- Duplicate deployment scripts
- Backup files (.save, .old)

### Structure Changes
- Alternative main.py files → `backend/app/main_variants/`
- Redundant PowerShell scripts removed
- __pycache__ directories cleaned

### Files Preserved
- All active code in backend/ and mobile/
- All tests in tests/
- Configuration files
- Documentation in docs/
- Infrastructure code
- Package files

## Recovery

If something goes wrong:

1. **Git Backup Branch**: The workflow creates a backup branch
   ```bash
   git checkout backup/pre-cleanup-YYYYMMDD-HHMMSS
   ```

2. **File Backup**: Important files are backed up to:
   ```
   cleanup_backup_YYYYMMDD_HHMMSS/
   ```

3. **Cleanup Log**: Detailed log of all changes:
   ```
   cleanup_log_YYYYMMDD_HHMMSS.txt
   ```

## Best Practices

1. **Always run dry-run first** to review changes
2. **Commit current work** before running cleanup
3. **Run full test suite** after cleanup
4. **Review git diff** before committing cleanup
5. **Test in staging** before deploying cleaned code

## Post-Cleanup Checklist

- [ ] Review git status and diff
- [ ] Run full test suite: `pytest`
- [ ] Build Docker images: `docker-compose build`
- [ ] Test local development: `docker-compose up`
- [ ] Update documentation if needed
- [ ] Commit with message: `chore: comprehensive codebase cleanup`
- [ ] Deploy to staging for verification
- [ ] Update team on structural changes

## Maintenance

Run cleanup periodically (monthly) to maintain codebase hygiene:
- Remove new temporary files
- Clean up completed feature branches
- Archive old documentation
- Update .gitignore as needed