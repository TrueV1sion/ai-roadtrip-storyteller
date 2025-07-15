# Security Monitoring and Alerting Configuration
# Provides comprehensive monitoring for DDoS attacks and security events

# Create log sink for security events
resource "google_logging_project_sink" "security_events" {
  name                   = "roadtrip-security-events-${var.environment}"
  project                = var.project_id
  destination            = "storage.googleapis.com/${google_storage_bucket.security_logs.name}"
  unique_writer_identity = true

  # Filter for security-related logs
  filter = <<-EOT
    resource.type="http_load_balancer" OR
    resource.type="cloud_armor_policy" OR
    resource.type="cloud_run_revision"
    AND (
      jsonPayload.enforcedSecurityPolicy.name != "" OR
      httpRequest.status >= 400 OR
      labels."serviceName" = "roadtrip-backend" OR
      jsonPayload.@type = "type.googleapis.com/google.cloud.loadbalancing.type.LoadBalancerLogEntry"
    )
  EOT

  bigquery_options {
    use_partitioned_tables = true
  }
}

# Storage bucket for security logs
resource "google_storage_bucket" "security_logs" {
  name                        = "${var.project_id}-security-logs-${var.environment}"
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  
  retention_policy {
    retention_period = 2592000  # 30 days
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }
}

# BigQuery dataset for security analytics
resource "google_bigquery_dataset" "security_analytics" {
  dataset_id                  = "roadtrip_security_analytics_${var.environment}"
  project                     = var.project_id
  location                    = var.region
  default_table_expiration_ms = 7776000000  # 90 days

  labels = {
    environment = var.environment
    purpose     = "security-analytics"
  }
}

# Notification channel for security alerts
resource "google_monitoring_notification_channel" "security_email" {
  display_name = "Security Team Email"
  type         = "email"
  project      = var.project_id
  
  labels = {
    email_address = var.security_email
  }
}

resource "google_monitoring_notification_channel" "security_pagerduty" {
  count        = var.pagerduty_integration_key != "" ? 1 : 0
  display_name = "Security PagerDuty"
  type         = "pagerduty"
  project      = var.project_id
  
  labels = {
    servicekey = var.pagerduty_integration_key
  }
}

# Alert Policies

# 1. DDoS Attack Detection
resource "google_monitoring_alert_policy" "ddos_detection" {
  display_name = "DDoS Attack Detection - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "High request rate detected"
    condition_threshold {
      filter          = "resource.type = \"http_load_balancer\" AND metric.type = \"loadbalancing.googleapis.com/https/request_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10000  # Adjust based on normal traffic
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  conditions {
    display_name = "Cloud Armor rule triggered"
    condition_threshold {
      filter          = "resource.type = \"cloud_armor_policy\" AND metric.type = \"networksecurity.googleapis.com/l7_ddos/detected_attack_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = concat(
    [google_monitoring_notification_channel.security_email.id],
    var.pagerduty_integration_key != "" ? [google_monitoring_notification_channel.security_pagerduty[0].id] : []
  )

  alert_strategy {
    auto_close = "1800s"
    
    notification_rate_limit {
      period = "300s"
    }
  }

  documentation {
    content = <<-EOT
      ## DDoS Attack Detected
      
      A potential DDoS attack has been detected on the ${var.environment} environment.
      
      ### Immediate Actions:
      1. Check the Cloud Armor dashboard for attack details
      2. Review the security policy logs
      3. Enable emergency lockdown rule if necessary
      4. Contact security team lead
      
      ### Dashboard Links:
      - [Cloud Armor Dashboard](https://console.cloud.google.com/net-security/securitypolicies/details/${google_compute_security_policy.roadtrip_policy.name})
      - [Load Balancer Monitoring](https://console.cloud.google.com/net-services/loadbalancing/details/http/${google_compute_url_map.roadtrip_url_map.name})
    EOT
    mime_type = "text/markdown"
  }
}

# 2. SQL Injection Attack Alert
resource "google_monitoring_alert_policy" "sql_injection" {
  display_name = "SQL Injection Attack Detected - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "SQL injection rule triggered"
    condition_monitoring_query_language {
      duration = "60s"
      query    = <<-EOT
        fetch http_lb_rule
        | metric 'loadbalancing.googleapis.com/https/request_count'
        | filter resource.backend_name == '${google_compute_backend_service.roadtrip_backend.name}'
        | filter metric.response_code_class == '403'
        | filter metric.cache_result == 'owasp-crs-v030301-id942110-sqli'
        | group_by 5m, [sum(value.request_count)]
        | condition sum(value.request_count) > 5
      EOT
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.id]

  alert_strategy {
    auto_close = "3600s"
  }
}

# 3. Rate Limit Violations
resource "google_monitoring_alert_policy" "rate_limit_violations" {
  display_name = "High Rate Limit Violations - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Rate limit exceeded"
    condition_threshold {
      filter = <<-EOT
        resource.type = "http_load_balancer" AND
        metric.type = "loadbalancing.googleapis.com/https/request_count" AND
        metric.response_code == "429"
      EOT
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.id]
}

# 4. Suspicious Geographic Activity
resource "google_monitoring_alert_policy" "geo_anomaly" {
  display_name = "Suspicious Geographic Activity - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Requests from blocked countries"
    condition_monitoring_query_language {
      duration = "300s"
      query    = <<-EOT
        fetch http_lb_rule
        | metric 'loadbalancing.googleapis.com/https/request_count'
        | filter resource.backend_name == '${google_compute_backend_service.roadtrip_backend.name}'
        | filter metric.client_country in ['XX', 'YY']  # Blocked countries
        | group_by 5m, [sum(value.request_count)]
        | condition sum(value.request_count) > 10
      EOT
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.id]
}

# 5. Backend Service Health
resource "google_monitoring_alert_policy" "backend_health" {
  display_name = "Backend Service Unhealthy - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Backend unhealthy"
    condition_threshold {
      filter          = "resource.type = \"https_lb_rule\" AND metric.type = \"loadbalancing.googleapis.com/https/backend_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5000  # 5 seconds
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MAX"
      }
    }
  }

  notification_channels = var.notification_channels
}

# Security Dashboard
resource "google_monitoring_dashboard" "security_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Road Trip Security Dashboard - ${var.environment}"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Rate by Country"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"http_load_balancer\" metric.type=\"loadbalancing.googleapis.com/https/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.client_country"]
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
          widget = {
            title = "Security Policy Actions"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_armor_policy\" metric.type=\"networksecurity.googleapis.com/l7_rule_hit_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.action", "metric.rule_id"]
                    }
                  }
                }
              }]
            }
          }
        },
        {
          width  = 4
          height = 4
          xPos   = 0
          yPos   = 4
          widget = {
            title = "Rate Limit Violations"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"http_load_balancer\" metric.type=\"loadbalancing.googleapis.com/https/request_count\" metric.response_code=\"429\""
                  aggregation = {
                    alignmentPeriod    = "300s"
                    perSeriesAligner   = "ALIGN_SUM"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_BAR"
              }
            }
          }
        },
        {
          width  = 4
          height = 4
          xPos   = 4
          yPos   = 4
          widget = {
            title = "Blocked Requests"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"http_load_balancer\" metric.type=\"loadbalancing.googleapis.com/https/request_count\" metric.response_code_class=\"4xx\""
                  aggregation = {
                    alignmentPeriod    = "300s"
                    perSeriesAligner   = "ALIGN_SUM"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_LINE"
              }
            }
          }
        },
        {
          width  = 4
          height = 4
          xPos   = 8
          yPos   = 4
          widget = {
            title = "Attack Score"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_armor_policy\" metric.type=\"networksecurity.googleapis.com/l7_ddos/detection_confidence\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MAX"
                  }
                }
              }
              thresholds = [
                {
                  value = 0.5
                  color = "YELLOW"
                },
                {
                  value = 0.8
                  color = "RED"
                }
              ]
            }
          }
        }
      ]
    }
  })
}

# Outputs
output "security_dashboard_url" {
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.security_dashboard.id}"
  description = "URL to security monitoring dashboard"
}

output "security_logs_bucket" {
  value       = google_storage_bucket.security_logs.name
  description = "Security logs storage bucket"
}