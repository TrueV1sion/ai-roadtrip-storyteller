# Variables for Cloud SQL module

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "network_id" {
  description = "VPC network ID"
  type        = string
}

variable "database_version" {
  description = "Database version"
  type        = string
  default     = "POSTGRES_15"
}

variable "tier" {
  description = "Machine tier for the database"
  type        = string
  default     = "db-n1-standard-2"
}

variable "replica_tier" {
  description = "Machine tier for the read replica"
  type        = string
  default     = ""
}

variable "availability_type" {
  description = "Availability type (ZONAL or REGIONAL)"
  type        = string
  default     = "REGIONAL"
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 100
}

variable "disk_autoresize" {
  description = "Enable disk autoresize"
  type        = bool
  default     = true
}

variable "disk_autoresize_limit" {
  description = "Disk autoresize limit in GB"
  type        = number
  default     = 500
}

variable "backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Start time for backups"
  type        = string
  default     = "03:00"
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "replica_region" {
  description = "Region for read replica (optional)"
  type        = string
  default     = ""
}