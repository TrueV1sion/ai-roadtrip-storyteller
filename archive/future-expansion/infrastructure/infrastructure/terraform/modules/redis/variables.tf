# Variables for Redis module

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

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_0"
}

variable "memory_size" {
  description = "Memory size in GB"
  type        = number
  default     = 4
}

variable "ha_enabled" {
  description = "Enable high availability"
  type        = bool
  default     = true
}

variable "persistence_enabled" {
  description = "Enable persistence"
  type        = bool
  default     = true
}