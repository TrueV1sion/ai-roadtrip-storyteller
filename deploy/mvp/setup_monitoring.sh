#!/bin/bash
# Set up monitoring and alerting for MVP

set -e

# Configuration
PROJECT_ID="roadtrip-mvp-prod"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"
ALERT_EMAIL="${ALERT_EMAIL:-your-email@example.com}"

echo "📊 Setting up Monitoring for AI Road Trip MVP"
echo "============================================"
echo ""

# Step 1: Create notification channel
echo "Creating email notification channel..."
CHANNEL_ID=$(gcloud alpha monitoring channels create \
    --display-name="MVP Alerts Email" \
    --type=email \
    --channel-labels="email_address=${ALERT_EMAIL}" \
    --format="value(name)" 2>/dev/null || echo "")

if [ -z "$CHANNEL_ID" ]; then
    # Get existing channel
    CHANNEL_ID=$(gcloud alpha monitoring channels list \
        --filter="displayName='MVP Alerts Email'" \
        --format="value(name)" | head -1)
fi

echo "Notification channel: $CHANNEL_ID"

# Step 2: Create uptime check
echo ""
echo "Creating uptime check..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

gcloud monitoring uptime create roadtrip-mvp-health \
    --display-name="Road Trip MVP Health Check" \
    --resource-type="URL" \
    --hostname="${SERVICE_URL#https://}" \
    --path="/health" \
    --check-interval=300 \
    --timeout=10 || echo "Uptime check already exists"

# Step 3: Create alert policies
echo ""
echo "Creating alert policies..."

# High latency alert
cat > /tmp/latency_alert.yaml << EOF
displayName: "High Response Time - Road Trip MVP"
conditions:
  - displayName: "Response time > 3 seconds"
    conditionThreshold:
      filter: |
        metric.type="run.googleapis.com/request_latencies"
        AND resource.type="cloud_run_revision"
        AND resource.labels.service_name="${SERVICE_NAME}"
      comparison: COMPARISON_GT
      thresholdValue: 3000
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_PERCENTILE_95
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 86400s
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/latency_alert.yaml || echo "Latency alert exists"

# Error rate alert
cat > /tmp/error_alert.yaml << EOF
displayName: "High Error Rate - Road Trip MVP"
conditions:
  - displayName: "Error rate > 1%"
    conditionThreshold:
      filter: |
        metric.type="run.googleapis.com/request_count"
        AND resource.type="cloud_run_revision"
        AND resource.labels.service_name="${SERVICE_NAME}"
        AND metric.labels.response_code_class="5xx"
      comparison: COMPARISON_GT
      thresholdValue: 0.01
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 86400s
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/error_alert.yaml || echo "Error alert exists"

# Memory usage alert
cat > /tmp/memory_alert.yaml << EOF
displayName: "High Memory Usage - Road Trip MVP"
conditions:
  - displayName: "Memory usage > 80%"
    conditionThreshold:
      filter: |
        metric.type="run.googleapis.com/container/memory/utilizations"
        AND resource.type="cloud_run_revision"
        AND resource.labels.service_name="${SERVICE_NAME}"
      comparison: COMPARISON_GT
      thresholdValue: 0.8
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_MEAN
notificationChannels:
  - ${CHANNEL_ID}
alertStrategy:
  autoClose: 86400s
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/memory_alert.yaml || echo "Memory alert exists"

# Step 4: Create dashboard
echo ""
echo "Creating monitoring dashboard..."

cat > /tmp/dashboard.json << EOF
{
  "displayName": "AI Road Trip MVP Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Response Time (95th percentile)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Error Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND metric.labels.response_code_class=\"5xx\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Memory Usage",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/container/memory/utilizations\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

gcloud monitoring dashboards create --config-from-file=/tmp/dashboard.json || echo "Dashboard already exists"

# Clean up temp files
rm -f /tmp/*.yaml /tmp/*.json

echo ""
echo "✅ Monitoring setup complete!"
echo ""
echo "Resources created:"
echo "- Uptime check: Road Trip MVP Health Check"
echo "- Alert: High Response Time (>3s)"
echo "- Alert: High Error Rate (>1%)"
echo "- Alert: High Memory Usage (>80%)"
echo "- Dashboard: AI Road Trip MVP Dashboard"
echo ""
echo "View dashboard at:"
echo "https://console.cloud.google.com/monitoring/dashboards"
echo ""
echo "⚠️  Remember to update ALERT_EMAIL in the notification channel!"