# Variables for Load Balancer module

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain" {
  description = "Domain name for the application"
  type        = string
}

variable "static_bucket_name" {
  description = "Name of the static assets bucket"
  type        = string
  default     = ""
}