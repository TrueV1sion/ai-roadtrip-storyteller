variable "aws_region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "The deployment environment (e.g., prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "backend_cpu" {
  description = "CPU units for the backend task"
  type        = string
  default     = "1024"
}

variable "backend_memory" {
  description = "Memory for the backend task"
  type        = string
  default     = "2048"
}

variable "backend_instance_count" {
  description = "Number of backend instances to run"
  type        = number
  default     = 2
}

variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "roadtrip"
}

variable "db_username" {
  description = "Username for the database"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Password for the database"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "Instance class for the RDS database"
  type        = string
  default     = "db.t3.small"
}

variable "redis_node_type" {
  description = "Node type for Redis cache"
  type        = string
  default     = "cache.t3.small"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to deploy in"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]
}

# Additional secret variables
variable "jwt_secret" {
  description = "Secret key used for JWT token signing"
  type        = string
  sensitive   = true
}

variable "maps_api_key" {
  description = "Google Maps API Key"
  type        = string
  sensitive   = true
}

variable "spotify_client_id" {
  description = "Spotify API Client ID"
  type        = string
  sensitive   = true
}

variable "spotify_client_secret" {
  description = "Spotify API Client Secret"
  type        = string
  sensitive   = true
} 