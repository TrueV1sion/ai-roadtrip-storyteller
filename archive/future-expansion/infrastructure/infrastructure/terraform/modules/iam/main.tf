# IAM Module for Road Trip Infrastructure

# Service account for the application
resource "google_service_account" "app_sa" {
  account_id   = "roadtrip-app-${var.environment}"
  display_name = "Road Trip Application Service Account"
  description  = "Service account for Road Trip application workloads"
}

# Service account for CI/CD
resource "google_service_account" "cicd_sa" {
  account_id   = "roadtrip-cicd-${var.environment}"
  display_name = "Road Trip CI/CD Service Account"
  description  = "Service account for CI/CD operations"
}

# Service account for monitoring
resource "google_service_account" "monitoring_sa" {
  account_id   = "roadtrip-monitoring-${var.environment}"
  display_name = "Road Trip Monitoring Service Account"
  description  = "Service account for monitoring and alerting"
}

# IAM roles for application service account
resource "google_project_iam_member" "app_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/redis.editor",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/aiplatform.user",
    "roles/cloudbuild.builds.viewer"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# IAM roles for CI/CD service account
resource "google_project_iam_member" "cicd_roles" {
  for_each = toset([
    "roles/container.developer",
    "roles/storage.admin",
    "roles/cloudbuild.builds.editor",
    "roles/artifactregistry.writer",
    "roles/run.admin",
    "roles/iam.serviceAccountUser"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd_sa.email}"
}

# IAM roles for monitoring service account
resource "google_project_iam_member" "monitoring_roles" {
  for_each = toset([
    "roles/monitoring.viewer",
    "roles/logging.viewer",
    "roles/cloudtrace.user",
    "roles/compute.viewer"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.monitoring_sa.email}"
}

# Workload Identity binding for application
resource "google_service_account_iam_binding" "app_workload_identity" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/roadtrip-app]",
    "serviceAccount:${var.project_id}.svc.id.goog[production/roadtrip-app]"
  ]
}

# Create custom role for minimal permissions
resource "google_project_iam_custom_role" "roadtrip_minimal" {
  role_id     = "roadtrip_minimal_${var.environment}"
  title       = "Road Trip Minimal Permissions"
  description = "Minimal permissions required for Road Trip application"
  permissions = [
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    "redis.instances.get",
    "redis.instances.getData",
    "redis.instances.setData",
    "storage.buckets.get",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "secretmanager.versions.access",
    "logging.logEntries.create",
    "monitoring.timeSeries.create",
    "cloudtrace.traces.patch"
  ]
}

# Keys for external services (if needed)
resource "google_service_account_key" "cicd_key" {
  service_account_id = google_service_account.cicd_sa.name
  private_key_type   = "TYPE_GOOGLE_CREDENTIALS_FILE"
}

# Outputs
output "app_service_account_email" {
  value = google_service_account.app_sa.email
}

output "cicd_service_account_email" {
  value = google_service_account.cicd_sa.email
}

output "monitoring_service_account_email" {
  value = google_service_account.monitoring_sa.email
}

output "cicd_service_account_key" {
  value     = base64decode(google_service_account_key.cicd_key.private_key)
  sensitive = true
}