# Variables for Terraform configuration

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
}

variable "domain" {
  description = "Domain name for the application"
  type        = string
}

# GKE Variables
variable "gke_num_nodes" {
  description = "Number of nodes per zone in the GKE cluster"
  type        = number
  default     = 2
}

variable "gke_machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "n2-standard-4"
}

variable "gke_disk_size_gb" {
  description = "Disk size for GKE nodes in GB"
  type        = number
  default     = 100
}

variable "gke_min_node_count" {
  description = "Minimum node count for autoscaling"
  type        = number
  default     = 2
}

variable "gke_max_node_count" {
  description = "Maximum node count for autoscaling"
  type        = number
  default     = 10
}

# Database Variables
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-n1-standard-2"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 100
}

variable "db_disk_autoresize" {
  description = "Enable disk autoresize for Cloud SQL"
  type        = bool
  default     = true
}

variable "db_max_disk_size" {
  description = "Maximum disk size for Cloud SQL autoresize"
  type        = number
  default     = 500
}

variable "db_backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "db_backup_start_time" {
  description = "Start time for automated backups (HH:MM)"
  type        = string
  default     = "03:00"
}

# Redis Variables
variable "redis_memory_size" {
  description = "Redis memory size in GB"
  type        = number
  default     = 4
}

variable "redis_ha_enabled" {
  description = "Enable Redis high availability"
  type        = bool
  default     = true
}

# Monitoring Variables
variable "enable_monitoring" {
  description = "Enable monitoring and alerting"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

# Security Variables
variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges for API access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssl_policy" {
  description = "SSL policy for load balancer"
  type        = string
  default     = "MODERN"
}

# Application Variables
variable "app_replicas" {
  description = "Number of application replicas"
  type        = number
  default     = 3
}

variable "celery_workers" {
  description = "Number of Celery workers"
  type        = number
  default     = 2
}