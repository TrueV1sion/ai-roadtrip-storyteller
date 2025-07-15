# Staging Environment Terraform Configuration
# This creates a complete staging environment that mirrors production

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "gcs" {
    bucket = "roadtrip-terraform-state"
    prefix = "terraform/staging"
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "zone" {
  description = "GCP Zone"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
}

variable "db_disk_size" {
  description = "Database disk size in GB"
  type        = number
}

variable "db_availability_type" {
  description = "Database availability type"
  type        = string
}

variable "db_backup_retention_days" {
  description = "Backup retention in days"
  type        = number
}

variable "redis_tier" {
  description = "Redis instance tier"
  type        = string
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
}

variable "cloud_run_min_instances" {
  description = "Minimum Cloud Run instances"
  type        = number
}

variable "cloud_run_max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU allocation"
  type        = string
}

variable "cloud_run_memory" {
  description = "Cloud Run memory allocation"
  type        = string
}

variable "enable_monitoring" {
  description = "Enable monitoring stack"
  type        = bool
}

variable "enable_alerting" {
  description = "Enable alerting"
  type        = bool
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor WAF"
  type        = bool
}

variable "enable_ssl" {
  description = "Enable SSL"
  type        = bool
}

variable "vpc_cidr" {
  description = "VPC CIDR range"
  type        = string
}

variable "subnet_cidr" {
  description = "Subnet CIDR range"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

# Providers
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Service Account for Staging
resource "google_service_account" "staging_sa" {
  account_id   = "roadtrip-staging-${random_id.suffix.hex}"
  display_name = "Road Trip Staging Service Account"
  description  = "Service account for staging environment"
}

# IAM roles for staging service account
resource "google_project_iam_member" "staging_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
    "roles/redis.editor",
    "roles/cloudtexttospeech.client",
    "roles/aiplatform.user",
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.staging_sa.email}"
}

# VPC for Staging
resource "google_compute_network" "staging_vpc" {
  name                    = "roadtrip-vpc-staging"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# Subnet for Staging
resource "google_compute_subnetwork" "staging_subnet" {
  name          = "roadtrip-subnet-staging"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.staging_vpc.id
  
  private_ip_google_access = true
}

# Allocate IP range for VPC peering
resource "google_compute_global_address" "staging_private_ip" {
  name          = "roadtrip-private-ip-staging"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = google_compute_network.staging_vpc.id
}

# Create VPC peering connection
resource "google_service_networking_connection" "staging_vpc_connection" {
  network                 = google_compute_network.staging_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.staging_private_ip.name]
}

# Cloud SQL PostgreSQL instance for Staging
resource "google_sql_database_instance" "staging_postgres" {
  name             = "roadtrip-db-staging-${random_id.suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  depends_on = [google_service_networking_connection.staging_vpc_connection]
  
  settings {
    tier              = var.db_tier
    availability_type = var.db_availability_type
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = false
      transaction_log_retention_days = 1
      
      backup_retention_settings {
        retained_backups = var.db_backup_retention_days
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.staging_vpc.id
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
    
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"  # Log queries taking more than 1s
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM
      update_track = "stable"
    }
  }
  
  deletion_protection = false  # Allow deletion for staging
}

# Database
resource "google_sql_database" "staging_database" {
  name     = "roadtrip_staging"
  instance = google_sql_database_instance.staging_postgres.name
}

# Database user
resource "random_password" "staging_db_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "staging_db_user" {
  name     = "roadtrip_staging"
  instance = google_sql_database_instance.staging_postgres.name
  password = random_password.staging_db_password.result
}

# Store staging database credentials in Secret Manager
resource "google_secret_manager_secret" "staging_db_password" {
  secret_id = "roadtrip-staging-db-password"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "staging_db_password" {
  secret = google_secret_manager_secret.staging_db_password.id
  secret_data = random_password.staging_db_password.result
}

resource "google_secret_manager_secret" "staging_db_url" {
  secret_id = "roadtrip-staging-db-url"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "staging_db_url" {
  secret = google_secret_manager_secret.staging_db_url.id
  secret_data = format(
    "postgresql://%s:%s@/%s?host=/cloudsql/%s",
    google_sql_user.staging_db_user.name,
    random_password.staging_db_password.result,
    google_sql_database.staging_database.name,
    google_sql_database_instance.staging_postgres.connection_name
  )
}

# Redis instance for Staging
resource "google_redis_instance" "staging_cache" {
  name               = "roadtrip-redis-staging"
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  redis_version      = "REDIS_7_0"
  display_name       = "Road Trip Staging Redis Cache"
  
  authorized_network = google_compute_network.staging_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  
  depends_on = [google_service_networking_connection.staging_vpc_connection]
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }
}

# Cloud Storage buckets for Staging
resource "google_storage_bucket" "staging_assets" {
  name          = "${var.project_id}-roadtrip-staging-assets"
  location      = var.region
  storage_class = "STANDARD"
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  lifecycle_rule {
    condition {
      age = 30  # Shorter retention for staging
    }
    action {
      type = "Delete"
    }
  }
  
  versioning {
    enabled = true
  }
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "staging_connector" {
  name          = "roadtrip-staging-connector"
  region        = var.region
  network       = google_compute_network.staging_vpc.name
  ip_cidr_range = "10.1.1.0/28"
  
  min_instances = 2
  max_instances = 3  # Lower max for staging
}

# Cloud Run service for Staging
resource "google_cloud_run_service" "staging_backend" {
  name     = "roadtrip-backend-staging"
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.staging_sa.email
      
      containers {
        image = "gcr.io/${var.project_id}/roadtrip-backend-staging:latest"
        
        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }
        
        env {
          name  = "ENVIRONMENT"
          value = "staging"
        }
        
        env {
          name  = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.staging_db_url.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.staging_cache.host}:${google_redis_instance.staging_cache.port}"
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"         = var.cloud_run_min_instances
        "autoscaling.knative.dev/maxScale"         = var.cloud_run_max_instances
        "run.googleapis.com/cloudsql-instances"    = google_sql_database_instance.staging_postgres.connection_name
        "run.googleapis.com/vpc-access-connector"  = google_vpc_access_connector.staging_connector.id
        "run.googleapis.com/vpc-access-egress"     = "private-ranges-only"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  autogenerate_revision_name = true
}

# Cloud Run IAM binding for public access
resource "google_cloud_run_service_iam_member" "staging_public_access" {
  service  = google_cloud_run_service.staging_backend.name
  location = google_cloud_run_service.staging_backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Armor security policy for staging
resource "google_compute_security_policy" "staging_armor" {
  count = var.enable_cloud_armor ? 1 : 0
  
  name        = "roadtrip-staging-armor"
  description = "Cloud Armor policy for staging environment"
  
  # Default rule
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
  
  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = 1000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action = "deny(429)"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 600
    }
  }
  
  # OWASP Top 10 rules
  dynamic "rule" {
    for_each = {
      "owasp-crs-v3-sqli" = 1001
      "owasp-crs-v3-xss"  = 1002
      "owasp-crs-v3-lfi"  = 1003
      "owasp-crs-v3-rce"  = 1004
    }
    
    content {
      action   = "deny(403)"
      priority = rule.value
      match {
        expr {
          expression = "evaluatePreconfiguredExpr('${rule.key}')"
        }
      }
    }
  }
}

# Monitoring Dashboard for Staging
resource "google_monitoring_dashboard" "staging_dashboard" {
  count = var.enable_monitoring ? 1 : 0
  
  dashboard_json = jsonencode({
    displayName = "Road Trip Staging Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Staging Cloud Run Request Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"roadtrip-backend-staging\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Staging Database CPU"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloudsql_database\" resource.labels.database_id=~\".*staging.*\" metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Staging Redis Memory Usage"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"redis_instance\" resource.labels.instance_id=\"roadtrip-redis-staging\" metric.type=\"redis.googleapis.com/stats/memory/usage\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Staging Error Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"roadtrip-backend-staging\" metric.type=\"run.googleapis.com/request_count\" metric.labels.response_code_class!=\"2xx\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })
}

# Outputs
output "staging_cloud_run_url" {
  value = google_cloud_run_service.staging_backend.status[0].url
  description = "Staging Cloud Run service URL"
}

output "staging_database_connection" {
  value = google_sql_database_instance.staging_postgres.connection_name
  description = "Staging database connection name"
}

output "staging_redis_host" {
  value = google_redis_instance.staging_cache.host
  description = "Staging Redis host"
}

output "staging_service_account" {
  value = google_service_account.staging_sa.email
  description = "Staging service account email"
}

output "staging_assets_bucket" {
  value = google_storage_bucket.staging_assets.url
  description = "Staging assets bucket URL"
}