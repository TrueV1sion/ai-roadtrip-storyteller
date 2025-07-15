# Global Load Balancer Configuration for Cloud Run with Cloud Armor
# Provides global distribution, SSL termination, and security integration

# Reserve a global static IP
resource "google_compute_global_address" "roadtrip_ip" {
  name         = "roadtrip-global-ip-${var.environment}"
  project      = var.project_id
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

# SSL Certificate (managed by Google)
resource "google_compute_managed_ssl_certificate" "roadtrip_cert" {
  name    = "roadtrip-ssl-cert-${var.environment}"
  project = var.project_id

  managed {
    domains = var.ssl_domains
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Health Check for backend
resource "google_compute_health_check" "roadtrip_health" {
  name                = "roadtrip-health-check-${var.environment}"
  project             = var.project_id
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  http_health_check {
    port               = 443
    request_path       = "/health"
    proxy_header       = "NONE"
    response           = ""
  }

  log_config {
    enable = true
  }
}

# Backend service configuration
resource "google_compute_backend_service" "roadtrip_backend" {
  name                            = "roadtrip-backend-service-${var.environment}"
  project                         = var.project_id
  protocol                        = "HTTPS"
  port_name                       = "https"
  timeout_sec                     = 30
  connection_draining_timeout_sec = 30

  # Cloud Armor security policy attachment
  security_policy = google_compute_security_policy.roadtrip_policy.id

  # Backend configuration for Cloud Run
  backend {
    group = google_compute_region_network_endpoint_group.roadtrip_neg.id
    
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }

  # Circuit breaker configuration
  circuit_breakers {
    max_requests_per_connection = 2
    max_connections             = 1000
    max_pending_requests        = 100
    max_requests                = 1000
    max_retries                 = 3
  }

  # Session affinity for consistent user experience
  session_affinity = "CLIENT_IP"
  
  # Connection persistence
  connection_tracking_policy {
    tracking_mode                                = "PER_SESSION"
    connection_persistence_on_unhealthy_backends = "NEVER_PERSIST"
  }

  health_checks = [google_compute_health_check.roadtrip_health.id]

  # CDN configuration for static content
  cdn_policy {
    cache_mode = "CACHE_ALL_STATIC"
    default_ttl = 3600
    max_ttl     = 86400
    
    negative_caching = true
    negative_caching_policy {
      code = 404
      ttl  = 120
    }

    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = false
    }
  }

  # Custom headers
  custom_request_headers = [
    "X-Cloud-Trace-Context: {client_trace_id}",
    "X-Forwarded-Proto: {protocol}",
  ]

  custom_response_headers = [
    "X-Content-Type-Options: nosniff",
    "X-Frame-Options: SAMEORIGIN",
    "X-XSS-Protection: 1; mode=block",
    "Referrer-Policy: strict-origin-when-cross-origin",
  ]

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  iap {
    enabled = false  # Enable if using Identity-Aware Proxy
  }
}

# Regional NEG for Cloud Run
resource "google_compute_region_network_endpoint_group" "roadtrip_neg" {
  name                  = "roadtrip-neg-${var.environment}"
  project               = var.project_id
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_service.backend.name
  }
}

# URL Map for routing
resource "google_compute_url_map" "roadtrip_url_map" {
  name            = "roadtrip-url-map-${var.environment}"
  project         = var.project_id
  default_service = google_compute_backend_service.roadtrip_backend.id

  # Host rules for different services
  host_rule {
    hosts        = var.api_hosts
    path_matcher = "api-paths"
  }

  # Path matching rules
  path_matcher {
    name            = "api-paths"
    default_service = google_compute_backend_service.roadtrip_backend.id

    # Route rules for different API endpoints
    route_rules {
      priority = 1
      match_rules {
        prefix_match = "/api/story"
      }
      route_action {
        weighted_backend_services {
          backend_service = google_compute_backend_service.roadtrip_backend.id
          weight          = 100
        }
        timeout {
          seconds = 60  # Longer timeout for story generation
        }
        retry_policy {
          num_retries = 2
          per_try_timeout {
            seconds = 30
          }
          retry_conditions = ["5xx", "deadline-exceeded", "connect-failure"]
        }
      }
    }

    route_rules {
      priority = 2
      match_rules {
        prefix_match = "/api/voice"
      }
      route_action {
        weighted_backend_services {
          backend_service = google_compute_backend_service.roadtrip_backend.id
          weight          = 100
        }
        timeout {
          seconds = 45  # Voice synthesis timeout
        }
      }
    }

    route_rules {
      priority = 3
      match_rules {
        prefix_match = "/api/booking"
      }
      route_action {
        weighted_backend_services {
          backend_service = google_compute_backend_service.roadtrip_backend.id
          weight          = 100
        }
        timeout {
          seconds = 30
        }
        cors_policy {
          allow_origins     = var.cors_origins
          allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
          allow_headers     = ["Authorization", "Content-Type", "X-API-Key"]
          expose_headers    = ["X-Request-ID", "X-RateLimit-Remaining"]
          max_age           = 3600
          allow_credentials = true
        }
      }
    }
  }

  # Default URL redirect for non-API traffic
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# Target HTTPS Proxy
resource "google_compute_target_https_proxy" "roadtrip_https_proxy" {
  name             = "roadtrip-https-proxy-${var.environment}"
  project          = var.project_id
  url_map          = google_compute_url_map.roadtrip_url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.roadtrip_cert.id]

  # Enable QUIC for better performance
  quic_override = "ENABLE"
}

# Global forwarding rule for HTTPS
resource "google_compute_global_forwarding_rule" "roadtrip_https" {
  name                  = "roadtrip-https-rule-${var.environment}"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.roadtrip_https_proxy.id
  ip_address            = google_compute_global_address.roadtrip_ip.id

  labels = {
    environment = var.environment
    service     = "roadtrip-api"
  }
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "roadtrip_http_redirect" {
  name    = "roadtrip-http-redirect-${var.environment}"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "roadtrip_http_proxy" {
  name    = "roadtrip-http-proxy-${var.environment}"
  project = var.project_id
  url_map = google_compute_url_map.roadtrip_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "roadtrip_http" {
  name                  = "roadtrip-http-rule-${var.environment}"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.roadtrip_http_proxy.id
  ip_address            = google_compute_global_address.roadtrip_ip.id

  labels = {
    environment = var.environment
    service     = "roadtrip-api"
  }
}

# CDN Backend Bucket for static assets
resource "google_compute_backend_bucket" "static_assets" {
  name        = "roadtrip-static-assets-${var.environment}"
  project     = var.project_id
  bucket_name = google_storage_bucket.assets.name
  enable_cdn  = true

  cdn_policy {
    cache_mode  = "CACHE_ALL_STATIC"
    default_ttl = 3600
    max_ttl     = 86400
    
    negative_caching = true
    negative_caching_policy {
      code = 404
      ttl  = 300
    }
  }
}

# DNS configuration
resource "google_dns_record_set" "roadtrip_a_record" {
  count        = var.create_dns_records ? 1 : 0
  name         = "${var.subdomain}.${var.domain_name}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_zone_name
  project      = var.project_id
  rrdatas      = [google_compute_global_address.roadtrip_ip.address]
}

# Monitoring Alert Policy for Load Balancer
resource "google_monitoring_alert_policy" "lb_high_latency" {
  display_name = "Load Balancer High Latency - ${var.environment}"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "High latency on load balancer"
    condition_threshold {
      filter          = "resource.type = \"https_lb_rule\" AND metric.type = \"loadbalancing.googleapis.com/https/backend_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000  # 2 seconds
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.url_map_name"]
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }
}

# Outputs
output "load_balancer_ip" {
  value       = google_compute_global_address.roadtrip_ip.address
  description = "Global load balancer IP address"
}

output "load_balancer_url" {
  value       = "https://${var.subdomain}.${var.domain_name}"
  description = "Load balancer URL"
}

output "backend_service_id" {
  value       = google_compute_backend_service.roadtrip_backend.id
  description = "Backend service ID"
}