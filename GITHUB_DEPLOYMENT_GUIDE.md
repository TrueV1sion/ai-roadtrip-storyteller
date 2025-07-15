# GitHub Actions Deployment Guide

## 🚀 Your GitHub Actions Setup

You already have a complete CI/CD pipeline configured! The `.github/workflows/deploy.yml` workflow will automatically deploy to staging or production.

## 📋 How to Deploy to Staging

### Option 1: Push to Staging Branch (Automatic)
```bash
# Create and push to staging branch
git checkout -b staging
git add .
git commit -m "Deploy to staging environment 🚀"
git push origin staging
```

### Option 2: Manual Trigger (Workflow Dispatch)
1. Go to your GitHub repository
2. Click on **Actions** tab
3. Select **"Deploy to Google Cloud Run"** workflow
4. Click **"Run workflow"**
5. Select **"staging"** from the dropdown
6. Click **"Run workflow"**

### Option 3: Push to Existing Staging Branch
```bash
# If staging branch already exists
git checkout staging
git merge main  # or your feature branch
git push origin staging
```

## 🔧 Prerequisites

### GitHub Secrets Required
Make sure these secrets are set in your repository:
- `GCP_SA_KEY` - Google Cloud Service Account JSON key

To add secrets:
1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add the required secret

## 📊 What Happens When You Deploy

1. **GitHub Actions triggers** on push to staging branch
2. **CI Pipeline runs**:
   - Linting (Python & TypeScript)
   - Security scanning
   - Unit tests with 85% coverage requirement
   - Docker image build
3. **CD Pipeline runs**:
   - Authenticates to Google Cloud
   - Builds and pushes Docker image
   - Deploys to Cloud Run
   - Runs health checks

## 🎯 Quick Deployment Commands

```bash
# 1. Ensure you're on the latest code
git pull origin main

# 2. Create or switch to staging branch
git checkout -b staging  # or git checkout staging

# 3. Stage all changes
git add .

# 4. Commit with a descriptive message
git commit -m "feat: Deploy AI Road Trip Storyteller to staging

- All integration tests passing (100%)
- Security hardening complete
- Six Sigma deployment documentation
- Ready for staging validation"

# 5. Push to trigger deployment
git push origin staging
```

## 🔍 Monitor Deployment

### In GitHub:
1. Go to **Actions** tab
2. Watch the workflow progress in real-time
3. Click on the workflow run for detailed logs

### After Deployment:
- Service URL will be shown in the workflow logs
- Health check: `https://roadtrip-backend-staging-<hash>-uc.a.run.app/health`
- API Docs: `https://roadtrip-backend-staging-<hash>-uc.a.run.app/docs`

## ⚠️ Important Notes

1. **Service Account**: The workflow uses a service account key stored in GitHub Secrets
2. **Environment Variables**: Set automatically based on branch (staging branch → staging env)
3. **Docker Build**: Happens in GitHub Actions runners (no local Docker needed)
4. **Automatic Deployment**: Every push to staging branch triggers deployment

## 🆘 Troubleshooting

### If deployment fails:
1. Check Actions tab for error logs
2. Verify `GCP_SA_KEY` secret is set correctly
3. Ensure service account has required permissions:
   - Cloud Run Admin
   - Storage Admin
   - Container Registry Service Agent

### Common Issues:
- **Authentication failed**: Update GCP_SA_KEY secret
- **Build failed**: Check Dockerfile and dependencies
- **Tests failed**: Fix failing tests before pushing
- **Permission denied**: Check IAM roles for service account

## 📝 Current Status

Your repository is configured with:
- ✅ CI/CD pipeline (`.github/workflows/deploy.yml`)
- ✅ Automatic deployment on push to staging
- ✅ Manual deployment option
- ✅ Security scanning
- ✅ Test coverage requirements
- ⏳ Awaiting push to staging branch

## 🎉 Ready to Deploy!

Simply run:
```bash
git checkout -b staging && git push origin staging
```

This will trigger the automated deployment to your staging environment!