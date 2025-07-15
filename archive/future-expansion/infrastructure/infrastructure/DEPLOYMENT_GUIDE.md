# Road Trip Production Deployment Guide

This guide provides step-by-step instructions for deploying the Road Trip application to Google Cloud Platform using Terraform and Kubernetes.

## Prerequisites

1. **Tools Required:**
   - Google Cloud SDK (`gcloud`)
   - Terraform (>= 1.0)
   - kubectl
   - Docker
   - Git

2. **GCP Requirements:**
   - Active GCP account with billing enabled
   - Project with owner or editor permissions
   - Domain name for the application

## Infrastructure Setup

### 1. Initial Setup

Run the setup script to prepare your environment:

```bash
cd infrastructure
./setup.sh
```

This script will:
- Verify prerequisites
- Enable required GCP APIs
- Create Terraform state bucket
- Create CI/CD service account
- Initialize Terraform

### 2. Configure Terraform Variables

Edit `terraform/terraform.tfvars` with your configuration:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
domain     = "roadtrip.yourdomain.com"
alert_email = "alerts@yourdomain.com"
```

### 3. Deploy Infrastructure

Review and apply Terraform configuration:

```bash
cd terraform
terraform plan
terraform apply
```

This creates:
- VPC and networking
- GKE cluster
- Cloud SQL (PostgreSQL)
- Cloud Memorystore (Redis)
- Cloud Storage buckets
- IAM roles and service accounts
- Secret Manager entries
- Load balancer
- Monitoring setup

### 4. Configure Secrets

Add your API keys to Google Secret Manager:

```bash
# Add secrets using gcloud
gcloud secrets create google-maps-api-key --data-file=- <<< "your-api-key"
gcloud secrets create openai-api-key --data-file=- <<< "your-api-key"
gcloud secrets create ticketmaster-api-key --data-file=- <<< "your-api-key"
# ... add other secrets
```

## Application Deployment

### 1. Build and Push Docker Image

```bash
# Authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push image
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-docker/roadtrip-api:latest .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-docker/roadtrip-api:latest
```

### 2. Deploy to Kubernetes

```bash
cd infrastructure
./deploy.sh --tag latest
```

The deploy script will:
- Create namespaces
- Deploy ConfigMaps and Secrets
- Deploy the application
- Set up autoscaling
- Configure ingress
- Deploy monitoring stack

### 3. Configure DNS

After deployment, get the load balancer IP:

```bash
kubectl get ingress roadtrip-ingress -n production
```

Update your DNS records:
- Create an A record pointing your domain to the load balancer IP
- Wait for DNS propagation (can take up to 48 hours)

### 4. Verify SSL Certificate

Google-managed SSL certificates are automatically provisioned. Check status:

```bash
kubectl describe managedcertificate roadtrip-managed-cert -n production
```

## CI/CD Setup

### 1. GitHub Secrets

Add the following secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_SA_KEY`: Contents of `cicd-key.json` (created by setup script)
- `SLACK_WEBHOOK`: Slack webhook URL for notifications
- `SONAR_TOKEN`: SonarCloud token (optional)

### 2. Deployment Workflow

The GitHub Actions workflow automatically:
- Runs tests on pull requests
- Builds and pushes Docker images
- Deploys to production on merge to main
- Runs smoke tests
- Sends notifications

## Monitoring

### 1. Access Monitoring Tools

**Prometheus:**
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Access at http://localhost:9090
```

**Grafana:**
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
# Access at http://localhost:3000
# Default credentials: admin/changeme-in-production
```

### 2. Configure Alerts

Alerts are configured in `prometheus-rules.yaml` and sent to:
- Email (configured in terraform.tfvars)
- Slack (if webhook configured)
- PagerDuty (optional)

### 3. View Dashboards

Pre-configured Grafana dashboards include:
- Application Overview
- API Performance
- Resource Usage
- Business Metrics

## Scaling

### 1. Horizontal Pod Autoscaling

HPA is configured to scale based on:
- CPU usage (70%)
- Memory usage (80%)
- Request rate

Adjust in `k8s/hpa.yaml` if needed.

### 2. Cluster Autoscaling

GKE cluster autoscaling is enabled with:
- Min nodes: 2 per zone
- Max nodes: 10 per zone

### 3. Database Scaling

For database scaling:
- Vertical: Change `db_tier` in Terraform
- Read replicas: Enabled for production

## Maintenance

### 1. Updates

Deploy application updates:

```bash
# Build and push new image
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-docker/roadtrip-api:v1.2.3 .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-docker/roadtrip-api:v1.2.3

# Deploy update
./deploy.sh --tag v1.2.3
```

### 2. Database Migrations

Migrations run automatically during deployment. For manual migrations:

```bash
kubectl exec -it deployment/roadtrip-api -n production -- alembic upgrade head
```

### 3. Backups

Automated backups are configured for:
- Cloud SQL: Daily backups, 30-day retention
- GCS buckets: Object versioning enabled

### 4. Log Analysis

View logs:

```bash
# Application logs
kubectl logs -n production -l app=roadtrip-api -f

# All namespace logs
kubectl logs -n production --all-containers=true -f

# GCP Console logs
gcloud logging read "resource.type=k8s_container AND resource.labels.namespace_name=production"
```

## Troubleshooting

### Common Issues

1. **Pods not starting:**
   ```bash
   kubectl describe pod <pod-name> -n production
   kubectl logs <pod-name> -n production
   ```

2. **Database connection issues:**
   - Check Cloud SQL proxy sidecar logs
   - Verify network connectivity
   - Check IAM permissions

3. **SSL certificate pending:**
   - Can take up to 30 minutes
   - Verify DNS is correctly configured
   - Check certificate status

4. **High latency:**
   - Check HPA metrics
   - Review Grafana dashboards
   - Scale up if needed

### Emergency Procedures

1. **Rollback deployment:**
   ```bash
   kubectl rollout undo deployment/roadtrip-api -n production
   ```

2. **Scale manually:**
   ```bash
   kubectl scale deployment/roadtrip-api -n production --replicas=10
   ```

3. **Emergency maintenance mode:**
   ```bash
   # Update ingress to show maintenance page
   kubectl apply -f k8s/maintenance-ingress.yaml
   ```

## Security Best Practices

1. **Regular Updates:**
   - Keep GKE cluster updated
   - Update base images monthly
   - Apply security patches promptly

2. **Access Control:**
   - Use least privilege IAM
   - Rotate service account keys
   - Enable audit logging

3. **Network Security:**
   - Use network policies
   - Enable Cloud Armor
   - Restrict ingress IPs

4. **Secrets Management:**
   - Use Google Secret Manager
   - Rotate secrets regularly
   - Never commit secrets to git

## Cost Optimization

1. **Use Spot Instances:**
   - Spot node pool configured for non-critical workloads
   - 60-80% cost savings

2. **Resource Requests:**
   - Set appropriate resource requests/limits
   - Use VPA recommendations

3. **Storage Lifecycle:**
   - Automated archival for old data
   - Cleanup policies configured

4. **Monitoring Costs:**
   - Review GCP billing dashboard
   - Set budget alerts
   - Use committed use discounts

## Support

For issues or questions:
1. Check application logs
2. Review monitoring dashboards
3. Consult error messages
4. Contact the development team

Remember to always test changes in a staging environment first!