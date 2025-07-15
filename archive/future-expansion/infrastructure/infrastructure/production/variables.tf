variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development"
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "ai-roadtrip-storyteller"
}

variable "billing_account" {
  description = "The billing account ID"
  type        = string
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidrs" {
  description = "CIDR blocks for subnets"
  type = object({
    public   = string
    private  = string
    database = string
  })
  default = {
    public   = "10.0.1.0/24"
    private  = "10.0.2.0/24"
    database = "10.0.3.0/24"
  }
}

# Cloud SQL
variable "db_instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
}

variable "db_tier" {
  description = "Machine tier for Cloud SQL instance"
  type        = string
  default     = "db-n1-standard-4"
}

variable "db_disk_size" {
  description = "Disk size in GB for Cloud SQL instance"
  type        = number
  default     = 100
}

variable "db_disk_type" {
  description = "Disk type for Cloud SQL instance"
  type        = string
  default     = "PD_SSD"
}

variable "db_backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "db_backup_start_time" {
  description = "Start time for automated backups (HH:MM format)"
  type        = string
  default     = "03:00"
}

variable "db_high_availability" {
  description = "Enable high availability (regional) for Cloud SQL"
  type        = bool
  default     = true
}

variable "db_database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "roadtrip"
}

variable "db_user" {
  description = "Database user name"
  type        = string
  default     = "roadtrip_app"
}

# Redis
variable "redis_instance_name" {
  description = "Name of the Redis instance"
  type        = string
}

variable "redis_tier" {
  description = "Service tier for Redis instance"
  type        = string
  default     = "STANDARD_HA"
}

variable "redis_memory_size" {
  description = "Memory size in GB for Redis instance"
  type        = number
  default     = 5
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.0"
}

# Cloud Storage
variable "storage_bucket_name" {
  description = "Name of the storage bucket"
  type        = string
}

variable "storage_location" {
  description = "Location for the storage bucket"
  type        = string
  default     = "US"
}

variable "storage_class" {
  description = "Storage class for the bucket"
  type        = string
  default     = "STANDARD"
}

# Cloud Run
variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run instances"
  type        = string
  default     = "4"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run instances"
  type        = string
  default     = "8Gi"
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 3
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 100
}

variable "cloud_run_concurrency" {
  description = "Maximum concurrent requests per Cloud Run instance"
  type        = number
  default     = 1000
}

# GKE (optional)
variable "gke_cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = ""
}

variable "gke_node_count" {
  description = "Initial number of nodes in GKE cluster"
  type        = number
  default     = 3
}

variable "gke_min_nodes" {
  description = "Minimum number of nodes in GKE cluster"
  type        = number
  default     = 3
}

variable "gke_max_nodes" {
  description = "Maximum number of nodes in GKE cluster"
  type        = number
  default     = 10
}

variable "gke_machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "n2-standard-4"
}

variable "gke_disk_size" {
  description = "Disk size in GB for GKE nodes"
  type        = number
  default     = 100
}

# Security
variable "enable_private_ip" {
  description = "Enable private IP for resources"
  type        = bool
  default     = true
}

variable "authorized_networks" {
  description = "Authorized networks for Cloud SQL"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

# Monitoring
variable "enable_monitoring" {
  description = "Enable monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

# Backup
variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "backup_location" {
  description = "Location for backups"
  type        = string
  default     = "us"
}

# Load Balancer
variable "enable_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = true
}

variable "ssl_certificates" {
  description = "SSL certificates for load balancer"
  type        = list(string)
  default     = []
}

# API Management
variable "api_gateway_name" {
  description = "Name of the API Gateway"
  type        = string
  default     = ""
}

variable "api_rate_limits" {
  description = "API rate limits by tier"
  type = object({
    anonymous     = number
    authenticated = number
    premium       = number
  })
  default = {
    anonymous     = 100
    authenticated = 1000
    premium       = 5000
  }
}

# Alerting
variable "notification_channels" {
  description = "Notification channels for alerts"
  type        = list(string)
  default     = []
}

# Cost Controls
variable "billing_budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 5000
}

variable "billing_alert_thresholds" {
  description = "Budget alert thresholds (as percentages)"
  type        = list(number)
  default     = [0.5, 0.8, 0.9, 1.0]
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Application = "ai-roadtrip-storyteller"
    ManagedBy   = "terraform"
  }
}