# AI Road Trip Storyteller - IAM Permissions Guide

## Quick Start

**To grant all required permissions, run ONE of these commands:**

### Windows PowerShell (Recommended):
```powershell
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\scripts
.\grant_iam_permissions.ps1
```

### Windows Command Prompt:
```cmd
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\scripts
grant_iam_permissions.bat
```

### Linux/Mac:
```bash
cd scripts
pwsh grant_iam_permissions.ps1
```

## Required IAM Roles

The service account `roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com` needs these 12 roles:

| Role | Purpose | Service |
|------|---------|---------|
| `roles/aiplatform.user` | Use Vertex AI Gemini 2.0 for story generation | Core AI |
| `roles/storage.objectAdmin` | Store TTS audio files and user content | Storage |
| `roles/secretmanager.secretAccessor` | Access API keys and credentials | Security |
| `roles/cloudsql.client` | Connect to PostgreSQL database | Database |
| `roles/redis.editor` | Cache AI responses to reduce costs | Cache |
| `roles/texttospeech.client` | Generate voice audio (20+ personalities) | Voice |
| `roles/speech.client` | Transcribe user voice commands | Voice |
| `roles/compute.networkUser` | Access VPC network | Network |
| `roles/vpcaccess.user` | Use VPC connector for Redis | Network |
| `roles/logging.logWriter` | Write application logs | Monitoring |
| `roles/monitoring.metricWriter` | Write custom metrics | Monitoring |
| `roles/cloudtrace.agent` | Performance tracing | Monitoring |

## Manual Grant via Console

If the script fails, grant permissions manually:

1. Go to: https://console.cloud.google.com/iam-admin/iam?project=roadtrip-460720
2. Find: `roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com`
3. Click: Edit (pencil icon)
4. Add all 12 roles listed above
5. Save

## Validation

To validate permissions are correctly set:

```powershell
.\scripts\grant_iam_permissions.ps1 -ValidateOnly
```

## Troubleshooting

### "Permission denied" errors
- Ensure you're authenticated: `gcloud auth login`
- Verify you have Project Owner or IAM Admin role
- Check project ID: `gcloud config get-value project`

### "Role not supported" errors
- Some roles may have different names in your region
- Use the Console UI to find the correct role name

### Service account not found
- Verify the service account exists in IAM
- Check for typos in the service account email

## Required APIs

These APIs must be enabled (the script doesn't handle this):

```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  texttospeech.googleapis.com \
  speech.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  compute.googleapis.com \
  vpcaccess.googleapis.com
```

## Contact

For permission issues, contact: peckinsights@gmail.com (Project Owner)