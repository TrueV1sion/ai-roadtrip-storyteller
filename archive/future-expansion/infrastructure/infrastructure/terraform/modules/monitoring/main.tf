# Monitoring Module for Road Trip Infrastructure

# Notification channel for alerts
resource "google_monitoring_notification_channel" "email" {
  display_name = "Road Trip Alert Email"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# Slack notification channel (optional)
resource "google_monitoring_notification_channel" "slack" {
  count = var.slack_webhook_url != "" ? 1 : 0

  display_name = "Road Trip Alert Slack"
  type         = "slack"

  labels = {
    url = var.slack_webhook_url
  }
}

# Uptime check for the application
resource "google_monitoring_uptime_check_config" "https" {
  display_name = "${var.environment}-roadtrip-uptime"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"

    labels = {
      host       = var.domain
      project_id = var.project_id
    }
  }

  content_matchers {
    content = "ok"
    matcher = "CONTAINS_STRING"
  }
}

# Alert policies

# High CPU usage
resource "google_monitoring_alert_policy" "cpu_usage" {
  display_name = "${var.environment} Road Trip - High CPU Usage"
  combiner     = "OR"

  conditions {
    display_name = "CPU usage above 80%"

    condition_threshold {
      filter          = "metric.type=\"kubernetes.io/container/cpu/core_usage_time\" resource.type=\"k8s_container\" resource.label.\"cluster_name\"=\"${var.cluster_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.pod_name"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = "CPU usage is above 80% for more than 5 minutes. Check if the application needs scaling or if there's a performance issue."
  }
}

# High memory usage
resource "google_monitoring_alert_policy" "memory_usage" {
  display_name = "${var.environment} Road Trip - High Memory Usage"
  combiner     = "OR"

  conditions {
    display_name = "Memory usage above 85%"

    condition_threshold {
      filter          = "metric.type=\"kubernetes.io/container/memory/used_bytes\" resource.type=\"k8s_container\" resource.label.\"cluster_name\"=\"${var.cluster_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.pod_name"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = "Memory usage is above 85% for more than 5 minutes. Check for memory leaks or increase resources."
  }
}

# High error rate
resource "google_monitoring_alert_policy" "error_rate" {
  display_name = "${var.environment} Road Trip - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate above 5%"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/error_count\" resource.type=\"k8s_container\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = "Error rate is above 5%. Check application logs for errors."
  }
}

# Database connection issues
resource "google_monitoring_alert_policy" "database_connection" {
  display_name = "${var.environment} Road Trip - Database Connection Issues"
  combiner     = "OR"

  conditions {
    display_name = "Database connections failing"

    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\" resource.type=\"cloudsql_database\""
      duration        = "180s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MIN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "600s"
  }

  documentation {
    content = "Database connection count is very low. Check if the database is accessible."
  }
}

# Redis memory usage
resource "google_monitoring_alert_policy" "redis_memory" {
  display_name = "${var.environment} Road Trip - Redis High Memory Usage"
  combiner     = "OR"

  conditions {
    display_name = "Redis memory usage above 90%"

    condition_threshold {
      filter          = "metric.type=\"redis.googleapis.com/stats/memory/usage_ratio\" resource.type=\"redis_instance\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.9

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = "Redis memory usage is above 90%. Consider increasing memory size or optimizing cache usage."
  }
}

# Pod restart alert
resource "google_monitoring_alert_policy" "pod_restarts" {
  display_name = "${var.environment} Road Trip - Frequent Pod Restarts"
  combiner     = "OR"

  conditions {
    display_name = "Pod restarting frequently"

    condition_threshold {
      filter          = "metric.type=\"kubernetes.io/container/restart_count\" resource.type=\"k8s_container\" resource.label.\"cluster_name\"=\"${var.cluster_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["resource.label.pod_name"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
  
  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content = "Pod has restarted more than 5 times in 5 minutes. Check pod logs for crash reasons."
  }
}

# SLO for API latency
resource "google_monitoring_slo" "api_latency" {
  service      = google_monitoring_service.api_service.service_id
  display_name = "95% of requests under 200ms"
  
  goal                = 0.95
  rolling_period_days = 30

  request_based_sli {
    good_total_ratio {
      total_service_filter = "metric.type=\"serviceruntime.googleapis.com/api/request_count\""
      good_service_filter  = "metric.type=\"serviceruntime.googleapis.com/api/request_count\" AND metric.label.response_code_class=\"2xx\""
    }
  }
}

# Service for SLO
resource "google_monitoring_service" "api_service" {
  service_id   = "${var.environment}-roadtrip-api"
  display_name = "${var.environment} Road Trip API"

  basic_service {
    service_type = "CLUSTER_ISTIO"
    service_labels = {
      cluster_name = var.cluster_name
    }
  }
}

# Dashboard
resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "${var.environment} Road Trip Dashboard"
    gridLayout = {
      widgets = [
        {
          title = "API Request Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"loadbalancing.googleapis.com/https/request_count\" resource.type=\"https_lb_rule\""
                }
              }
            }]
          }
        },
        {
          title = "API Latency (p95)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"loadbalancing.googleapis.com/https/backend_latencies\" resource.type=\"https_lb_rule\""
                  aggregation = {
                    alignmentPeriod   = "60s"
                    perSeriesAligner  = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        },
        {
          title = "CPU Usage by Pod"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"kubernetes.io/container/cpu/core_usage_time\" resource.type=\"k8s_container\""
                }
              }
            }]
          }
        },
        {
          title = "Memory Usage by Pod"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"kubernetes.io/container/memory/used_bytes\" resource.type=\"k8s_container\""
                }
              }
            }]
          }
        },
        {
          title = "Database Connections"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\" resource.type=\"cloudsql_database\""
                }
              }
            }]
          }
        },
        {
          title = "Redis Memory Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"redis.googleapis.com/stats/memory/usage_ratio\" resource.type=\"redis_instance\""
                }
              }
            }]
          }
        }
      ]
    }
  })
}

# Outputs
output "dashboard_url" {
  value = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.main.id}?project=${var.project_id}"
}

output "notification_channel_id" {
  value = google_monitoring_notification_channel.email.id
}