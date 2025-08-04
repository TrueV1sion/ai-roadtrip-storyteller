# Root Directory File Convention

This document explains which files should remain in the project root and why.

## Files That MUST Stay in Root

### Core Project Files
- `README.md` - Project overview and quick start
- `LICENSE` - Legal license file
- `CLAUDE.md` - AI assistant instructions

### Python Project Files
- `requirements.txt` - Main dependencies
- `requirements-dev.txt` - Development dependencies
- `requirements-minimal.txt` - Minimal dependencies
- `requirements.prod.txt` - Production dependencies
- `pytest.ini` - PyTest configuration
- `alembic.ini` - Database migration config

### Environment Files (Active)
- `.env` - Local development environment (git-ignored)
- `.env.example` - Template for developers
- `.env.production` - Production environment (git-ignored)

### Development Tool Configs
- `.gitignore` - Git ignore patterns
- `.dockerignore` - Docker ignore patterns
- `.flake8` - Python linting config
- `.gcloudignore` - Google Cloud ignore patterns
- `.pre-commit-config.yaml` - Pre-commit hooks

## Files That Were Moved

### To `/docs/`
- All markdown documentation except README.md, LICENSE, CLAUDE.md
- DMAIC reports (including JSON files)
- Architecture documents
- Deployment guides

### To `/scripts/`
- All shell scripts (`.sh` files)
- All Python utility scripts
- DMAIC report generators

### To `/infrastructure/`
- `Dockerfile` and docker-compose files
- `cloudbuild.yaml`
- Kubernetes manifests
- Terraform files

### To `/config/env-templates/`
- `.env.template` - Template file
- `.env.email.backup` - Backup configuration

## Why This Structure?

1. **Root Clarity**: Only files that tools expect in root remain there
2. **Tool Compatibility**: Build tools, linters, and package managers expect certain files in root
3. **Developer Experience**: New developers immediately see only essential files
4. **Best Practices**: Follows Python/Node.js project conventions

## Quick Reference

When adding new files:
- Documentation → `/docs/`
- Scripts → `/scripts/`
- Configs (non-tool) → `/config/`
- Infrastructure → `/infrastructure/`
- Only tool configs that MUST be in root stay in root