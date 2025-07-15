terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  # Temporarily using local backend - migrate to GCS later
  # backend "gcs" {
  #   bucket = "roadtrip-terraform-state"
  #   prefix = "production"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Local variables
locals {
  app_name_normalized = replace(var.app_name, "-", "_")
  common_labels = merge(var.common_tags, {
    terraform_managed = "true"
    environment      = var.environment
  })
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "storage.googleapis.com",
    "cloudrun.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "certificatemanager.googleapis.com",
    "networksecurity.googleapis.com",
    "beyondcorp.googleapis.com",
  ])
  
  service            = each.key
  disable_on_destroy = false
}

# VPC Network
module "vpc" {
  source = "../terraform/modules/vpc"
  
  project_id = var.project_id
  region     = var.region
  
  depends_on = [google_project_service.apis]
}

# Cloud SQL Instance
module "cloud_sql" {
  source = "../terraform/modules/cloud-sql"
  
  project_id           = var.project_id
  region              = var.region
  network_id          = module.vpc.network_id
  database_version    = "POSTGRES_15"
  tier                = var.db_tier
  disk_size           = var.db_disk_size
  backup_enabled      = var.db_backup_enabled
  backup_start_time   = var.db_backup_start_time
  availability_type   = var.db_high_availability ? "REGIONAL" : "ZONAL"
  
  depends_on = [
    google_project_service.apis,
    module.vpc
  ]
}

# Redis Instance
module "redis" {
  source = "../terraform/modules/redis"
  
  project_id      = var.project_id
  region         = var.region
  network_id     = module.vpc.network_id
  redis_version  = "REDIS_${replace(var.redis_version, ".", "_")}"
  memory_size    = var.redis_memory_size
  ha_enabled     = var.redis_tier == "STANDARD_HA"
  
  depends_on = [
    google_project_service.apis,
    module.vpc
  ]
}

# Cloud Storage Bucket
module "storage" {
  source = "../terraform/modules/storage"
  
  project_id    = var.project_id
  region       = var.region
  environment  = var.environment
  
  depends_on = [google_project_service.apis]
}

# Secret Manager Secrets
module "secrets" {
  source = "../terraform/modules/secrets"
  
  project_id = var.project_id
  region    = var.region
  
  # Note: Secrets will need to be created manually or provided through CI/CD
  secrets = {}
  
  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${var.app_name}-${var.environment}-run"
  display_name = "Cloud Run Service Account"
  description  = "Service account for Cloud Run application"
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/redis.editor",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "app" {
  name     = "${var.app_name}-${var.environment}"
  location = var.region
  
  template {
    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }
    
    max_instance_request_concurrency = var.cloud_run_concurrency
    
    service_account = google_service_account.cloud_run.email
    
    containers {
      image = "gcr.io/${var.project_id}/${var.app_name}:latest"
      
      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
        cpu_idle = true
      }
      
      ports {
        container_port = 8000
      }
      
      env {
        name  = "DATABASE_URL"
        value = "postgresql://${module.cloud_sql.db_user}:${module.cloud_sql.db_password}@${module.cloud_sql.private_ip}:5432/${module.cloud_sql.database_name}"
      }
      
      env {
        name  = "REDIS_URL"
        value = module.redis.connection_string
      }
      
      env {
        name  = "GCS_BUCKET_NAME"
        value = module.storage.user_uploads_bucket
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      
      # Secrets from Secret Manager - to be configured after initial deployment
      # dynamic "env" {
      #   for_each = {
      #     JWT_SECRET_KEY         = "jwt_secret"
      #     GOOGLE_MAPS_API_KEY    = "google_maps_api_key"
      #     TICKETMASTER_API_KEY   = "ticketmaster_api_key"
      #     OPENWEATHERMAP_API_KEY = "openweathermap_api_key"
      #     RECREATION_GOV_API_KEY = "recreation_gov_api_key"
      #     SPOTIFY_CLIENT_ID      = "spotify_client_id"
      #     SPOTIFY_CLIENT_SECRET  = "spotify_client_secret"
      #   }
      #   content {
      #     name = env.key
      #     value_source {
      #       secret_key_ref {
      #         secret  = module.secrets.secret_ids[env.value]
      #         version = "latest"
      #       }
      #     }
      #   }
      # }
      
      # Health check
      liveness_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 30
        period_seconds        = 30
        timeout_seconds       = 10
        failure_threshold     = 3
      }
      
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 0
        period_seconds        = 10
        timeout_seconds       = 10
        failure_threshold     = 30
      }
    }
    
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = local.common_labels
  
  depends_on = [
    google_project_service.apis,
    module.cloud_sql,
    module.redis,
    module.secrets
  ]
}

# VPC Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "${var.app_name}-${var.environment}-connector"
  ip_cidr_range = "10.8.0.0/28"
  network       = module.vpc.network_name
  region        = var.region
  
  min_instances = 2
  max_instances = 10
  
  depends_on = [google_project_service.apis]
}

# Load Balancer with CDN
module "load_balancer" {
  source = "../terraform/modules/load-balancer"
  
  project_id      = var.project_id
  region         = var.region
  environment    = var.environment
  domain         = "${var.app_name}.com"  # Update with actual domain
  
  depends_on = [google_cloud_run_v2_service.app]
}

# Monitoring and Alerting
module "monitoring" {
  source = "../terraform/modules/monitoring"
  
  project_id   = var.project_id
  environment  = var.environment
  cluster_name = ""  # Using Cloud Run, not GKE
  domain       = "${var.app_name}.com"
  
  depends_on = [google_project_service.apis]
}

# Budget Alert
resource "google_billing_budget" "budget" {
  billing_account = var.billing_account
  display_name    = "${var.app_name}-${var.environment}-budget"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units        = tostring(var.billing_budget_amount)
    }
  }
  
  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.8
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
  
  all_updates_rule {
    monitoring_notification_channels = var.notification_channels
  }
}

# Outputs
output "cloud_run_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.app.uri
}

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = module.load_balancer.load_balancer_ip
}

output "database_connection_name" {
  description = "Connection name for Cloud SQL instance"
  value       = module.cloud_sql.connection_name
  sensitive   = true
}

output "redis_host" {
  description = "Redis instance host"
  value       = module.redis.host
  sensitive   = true
}

output "storage_bucket_url" {
  description = "URL of the storage bucket"
  value       = module.storage.static_assets_url
}