#!/bin/bash
set -e

PROJECT_ID="roadtrip-460720"

echo "=== Fixing Terraform Deployment Issues ==="

# 1. Import existing subnet
echo "1. Importing existing subnet..."
terraform import google_compute_subnetwork.subnet projects/$PROJECT_ID/regions/us-central1/subnetworks/roadtrip-subnet-production || true

# 2. Import existing private IP allocation
echo "2. Importing existing private IP allocation..."
terraform import google_compute_global_address.private_ip_alloc projects/$PROJECT_ID/global/addresses/roadtrip-private-ip-production || true

# 3. Import existing db password secret
echo "3. Importing existing db password secret..."
terraform import google_secret_manager_secret.db_password projects/$PROJECT_ID/secrets/roadtrip-db-password || true

# 4. Import existing VPC connector
echo "4. Importing existing VPC connector..."
terraform import google_vpc_access_connector.connector projects/$PROJECT_ID/regions/us-central1/connectors/roadtrip-connector || true

# 5. Fix the IAM role issue
echo "5. Fixing IAM role in main.tf..."
sed -i 's/"roles\/cloudtexttospeech.client"/"roles\/texttospeech.client"/g' main.tf

# 6. Fix monitoring dashboard
echo "6. Creating fixed monitoring dashboard configuration..."
cat > monitoring_dashboard_fix.tf << 'EOF'
# Fixed monitoring dashboard configuration
resource "google_monitoring_dashboard" "roadtrip" {
  dashboard_json = jsonencode({
    displayName = "Road Trip Storyteller Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          xPos   = 0
          yPos   = 0
          widget = {
            title = "Cloud Run Request Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"roadtrip-backend\" metric.type=\"run.googleapis.com/request_count\""
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
          xPos   = 6
          yPos   = 0
          widget = {
            title = "Cloud SQL CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloudsql_database\" metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
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
EOF

# 7. Remove the broken monitoring dashboard from main.tf
echo "7. Removing broken monitoring dashboard from main.tf..."
sed -i '/# Monitoring dashboard/,/^output "cloud_run_url" {/d' main.tf

echo "All fixes applied. Now run 'terraform plan' to verify."