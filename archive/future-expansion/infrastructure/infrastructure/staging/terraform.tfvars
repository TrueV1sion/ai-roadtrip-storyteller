# Staging Environment Configuration
# This file contains staging-specific values for Terraform variables

project_id = "roadtrip-460720"
region     = "us-central1"
zone       = "us-central1-a"
environment = "staging"

# Staging-specific resource configurations
db_tier = "db-f1-micro"              # Smaller instance for staging
db_disk_size = 100                   # 100GB for staging vs 500GB for production
db_availability_type = "ZONAL"       # Single zone for cost savings
db_backup_retention_days = 7         # 7 days for staging vs 30 for production

# Redis configuration
redis_tier = "BASIC"                 # Basic tier for staging
redis_memory_size_gb = 1             # 1GB for staging vs 5GB for production

# Cloud Run configuration
cloud_run_min_instances = 1          # Minimum 1 instance
cloud_run_max_instances = 20         # Max 20 for staging vs 100 for production
cloud_run_cpu = "1"                  # 1 CPU for staging
cloud_run_memory = "1Gi"             # 1GB memory for staging

# Monitoring configuration
enable_monitoring = true
enable_alerting = false              # Disable alerting for staging

# Security configuration
enable_cloud_armor = true            # Keep security enabled in staging
enable_ssl = true                    # SSL enabled for staging

# Networking
vpc_cidr = "10.1.0.0/16"            # Different CIDR for staging
subnet_cidr = "10.1.0.0/24"         # Staging subnet

# Tags
tags = {
  environment = "staging"
  project     = "roadtrip"
  managed_by  = "terraform"
  purpose     = "staging_validation"
}