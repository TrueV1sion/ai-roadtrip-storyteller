# Production Terraform Variables
# AI Road Trip Storyteller Deployment

project_id = "roadtrip-460720"
region     = "us-central1"
environment = "production"

# Domain Configuration
domain_name = "ai-roadtrip.app"

# Billing Account (needs to be updated with actual billing account)
billing_account = "BILLINGACCOUNT"

# Database Configuration
db_tier = "db-n1-highmem-2"
db_availability_type = "REGIONAL"

# Application Configuration
app_name = "ai-roadtrip-storyteller"

# Monitoring
enable_monitoring = true
notification_email = "alerts@ai-roadtrip.app"