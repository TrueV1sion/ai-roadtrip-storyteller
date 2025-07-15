# Load Balancer Module for Road Trip Infrastructure

# Reserve static IP
resource "google_compute_global_address" "default" {
  name = "${var.environment}-roadtrip-ip"
}

# SSL Certificate
resource "google_compute_managed_ssl_certificate" "default" {
  name = "${var.environment}-roadtrip-cert"

  managed {
    domains = [var.domain, "www.${var.domain}"]
  }
}

# Health check
resource "google_compute_health_check" "default" {
  name                = "${var.environment}-roadtrip-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  http_health_check {
    request_path = "/health"
    port         = 8080
  }
}

# Backend service
resource "google_compute_backend_service" "default" {
  name                  = "${var.environment}-roadtrip-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  health_checks         = [google_compute_health_check.default.id]
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group           = google_compute_instance_group.default.id
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    client_ttl                   = 7200
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
    signed_url_cache_max_age_sec = 7200

    negative_caching_policy {
      code = 404
      ttl  = 120
    }
  }

  security_policy = google_compute_security_policy.default.id

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# URL map
resource "google_compute_url_map" "default" {
  name            = "${var.environment}-roadtrip-url-map"
  default_service = google_compute_backend_service.default.id

  host_rule {
    hosts        = [var.domain, "www.${var.domain}"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.default.id

    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.default.id
    }

    path_rule {
      paths   = ["/static/*"]
      service = google_compute_backend_bucket.static.id
    }
  }
}

# Backend bucket for static assets
resource "google_compute_backend_bucket" "static" {
  name        = "${var.environment}-roadtrip-static-backend"
  bucket_name = var.static_bucket_name
  enable_cdn  = true

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    client_ttl                   = 7200
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
  }
}

# HTTP(S) proxy
resource "google_compute_target_https_proxy" "default" {
  name             = "${var.environment}-roadtrip-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
  ssl_policy       = google_compute_ssl_policy.default.id
}

# SSL policy
resource "google_compute_ssl_policy" "default" {
  name            = "${var.environment}-roadtrip-ssl-policy"
  profile         = "MODERN"
  min_tls_version = "TLS_1_2"
}

# Forwarding rule
resource "google_compute_global_forwarding_rule" "default" {
  name       = "${var.environment}-roadtrip-forwarding-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "${var.environment}-roadtrip-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "${var.environment}-roadtrip-http-redirect-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  name       = "${var.environment}-roadtrip-http-redirect-rule"
  target     = google_compute_target_http_proxy.http_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.default.address
}

# Security policy
resource "google_compute_security_policy" "default" {
  name = "${var.environment}-roadtrip-security-policy"

  # Rate limiting rule
  rule {
    action   = "throttle"
    priority = "1000"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"

      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }

      ban_duration_sec = 600
    }
  }

  # Allow rule
  rule {
    action   = "allow"
    priority = "2147483647"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    description = "Default allow rule"
  }

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
}

# Instance group (placeholder - will be managed by GKE)
resource "google_compute_instance_group" "default" {
  name = "${var.environment}-roadtrip-ig"
  zone = "${var.region}-a"

  named_port {
    name = "http"
    port = 8080
  }
}

# Cloud Armor security policies
resource "google_compute_security_policy" "owasp" {
  name = "${var.environment}-roadtrip-owasp-policy"

  # OWASP Top 10 protection
  rule {
    action   = "deny(403)"
    priority = "1001"

    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }

    description = "Deny XSS attacks"
  }

  rule {
    action   = "deny(403)"
    priority = "1002"

    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }

    description = "Deny SQL injection attacks"
  }

  rule {
    action   = "deny(403)"
    priority = "1003"

    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-stable')"
      }
    }

    description = "Deny local file inclusion attacks"
  }

  rule {
    action   = "deny(403)"
    priority = "1004"

    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rfi-stable')"
      }
    }

    description = "Deny remote file inclusion attacks"
  }

  rule {
    action   = "deny(403)"
    priority = "1005"

    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rce-stable')"
      }
    }

    description = "Deny remote code execution attacks"
  }

  # Default allow
  rule {
    action   = "allow"
    priority = "2147483647"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    description = "Default allow rule"
  }
}

# Outputs
output "load_balancer_ip" {
  value = google_compute_global_address.default.address
}

output "ssl_certificate_id" {
  value = google_compute_managed_ssl_certificate.default.id
}

output "backend_service_id" {
  value = google_compute_backend_service.default.id
}