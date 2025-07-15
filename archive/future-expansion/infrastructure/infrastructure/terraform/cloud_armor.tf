# Cloud Armor Security Policy for DDoS Protection and WAF
# This configuration provides enterprise-grade protection for the AI Road Trip Storyteller

# Enable required APIs for Cloud Armor
resource "google_project_service" "armor_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "networksecurity.googleapis.com",
    "recaptchaenterprise.googleapis.com",
  ])
  
  project = var.project_id
  service = each.key
  
  disable_on_destroy = false
}

# Create reCAPTCHA Enterprise key for bot protection
resource "google_recaptcha_enterprise_key" "roadtrip_key" {
  display_name = "roadtrip-recaptcha-key"
  project      = var.project_id

  web_settings {
    integration_type              = "SCORE"
    allow_all_domains            = false
    allowed_domains              = var.allowed_domains
    challenge_security_preference = "BALANCE"
  }

  labels = {
    environment = var.environment
    purpose     = "bot-protection"
  }
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "roadtrip_policy" {
  name        = "roadtrip-security-policy-${var.environment}"
  description = "Comprehensive security policy for AI Road Trip Storyteller"
  project     = var.project_id

  # Adaptive Protection (Auto-tuning for DDoS)
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable          = true
      rule_visibility = "STANDARD"
    }
  }

  # Default rule - Allow traffic
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule"
  }

  # Rule 1: Block known malicious IPs
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "origin.ip in ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']"
      }
    }
    description = "Block private IP ranges"
  }

  # Rule 2: Country-based blocking (optional - customize based on requirements)
  rule {
    action   = "deny(403)"
    priority = 2000
    match {
      expr {
        expression = "origin.region_code in ['XX', 'YY']"  # Replace with actual country codes if needed
      }
    }
    description = "Geographic restrictions"
  }

  # Rule 3: Rate limiting for API endpoints
  rule {
    action = "rate_based_ban"
    priority = 3000
    match {
      expr {
        expression = "request.path.matches('/api/.*')"
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 600  # 10 minute ban
    }
    description = "API endpoint rate limiting"
  }

  # Rule 4: Enhanced rate limiting for expensive endpoints
  rule {
    action = "rate_based_ban"
    priority = 3100
    match {
      expr {
        expression = "request.path.matches('/api/story/generate|/api/voice/.*|/api/booking/.*')"
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 20
        interval_sec = 60
      }
      ban_duration_sec = 1800  # 30 minute ban
    }
    description = "Rate limiting for expensive operations"
  }

  # Rule 5: SQL Injection Protection
  rule {
    action   = "deny(403)"
    priority = 4000
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('sqli-v33-stable',
            ['owasp-crs-v030301-id942110-sqli',
             'owasp-crs-v030301-id942120-sqli',
             'owasp-crs-v030301-id942130-sqli',
             'owasp-crs-v030301-id942140-sqli',
             'owasp-crs-v030301-id942150-sqli',
             'owasp-crs-v030301-id942160-sqli',
             'owasp-crs-v030301-id942170-sqli',
             'owasp-crs-v030301-id942180-sqli',
             'owasp-crs-v030301-id942190-sqli',
             'owasp-crs-v030301-id942200-sqli'])
        EOT
      }
    }
    description = "SQL injection protection"
  }

  # Rule 6: XSS Protection
  rule {
    action   = "deny(403)"
    priority = 4100
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('xss-v33-stable',
            ['owasp-crs-v030301-id941110-xss',
             'owasp-crs-v030301-id941120-xss',
             'owasp-crs-v030301-id941130-xss',
             'owasp-crs-v030301-id941140-xss',
             'owasp-crs-v030301-id941150-xss',
             'owasp-crs-v030301-id941160-xss',
             'owasp-crs-v030301-id941170-xss',
             'owasp-crs-v030301-id941180-xss'])
        EOT
      }
    }
    description = "Cross-site scripting protection"
  }

  # Rule 7: Local File Inclusion Protection
  rule {
    action   = "deny(403)"
    priority = 4200
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('lfi-v33-stable',
            ['owasp-crs-v030301-id930100-lfi',
             'owasp-crs-v030301-id930110-lfi',
             'owasp-crs-v030301-id930120-lfi',
             'owasp-crs-v030301-id930130-lfi'])
        EOT
      }
    }
    description = "Local file inclusion protection"
  }

  # Rule 8: Remote Code Execution Protection
  rule {
    action   = "deny(403)"
    priority = 4300
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('rce-v33-stable',
            ['owasp-crs-v030301-id932100-rce',
             'owasp-crs-v030301-id932105-rce',
             'owasp-crs-v030301-id932110-rce',
             'owasp-crs-v030301-id932115-rce'])
        EOT
      }
    }
    description = "Remote code execution protection"
  }

  # Rule 9: Protocol Attack Protection
  rule {
    action   = "deny(403)"
    priority = 4400
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('protocolattack-v33-stable',
            ['owasp-crs-v030301-id921110-protocolattack',
             'owasp-crs-v030301-id921120-protocolattack',
             'owasp-crs-v030301-id921130-protocolattack',
             'owasp-crs-v030301-id921140-protocolattack',
             'owasp-crs-v030301-id921150-protocolattack',
             'owasp-crs-v030301-id921160-protocolattack'])
        EOT
      }
    }
    description = "Protocol attack protection"
  }

  # Rule 10: Scanner Detection
  rule {
    action   = "deny(403)"
    priority = 4500
    match {
      expr {
        expression = <<-EOT
          evaluatePreconfiguredExpr('scannerdetection-v33-stable',
            ['owasp-crs-v030301-id913100-scannerdetection',
             'owasp-crs-v030301-id913110-scannerdetection',
             'owasp-crs-v030301-id913120-scannerdetection'])
        EOT
      }
    }
    description = "Scanner and bot detection"
  }

  # Rule 11: Request Method Validation
  rule {
    action   = "deny(403)"
    priority = 4600
    match {
      expr {
        expression = "!(request.method in ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])"
      }
    }
    description = "Block non-standard HTTP methods"
  }

  # Rule 12: Request Size Limits
  rule {
    action   = "deny(413)"
    priority = 4700
    match {
      expr {
        expression = "int(request.headers['content-length']) > 10485760"  # 10MB limit
      }
    }
    description = "Request size limit"
  }

  # Rule 13: Bot Protection with reCAPTCHA
  rule {
    action   = "redirect"
    priority = 5000
    match {
      expr {
        expression = <<-EOT
          request.path.matches('/api/auth/.*') && 
          !token.recaptcha_session.score > 0.5
        EOT
      }
    }
    redirect_options {
      type = "GOOGLE_RECAPTCHA"
    }
    description = "reCAPTCHA challenge for suspicious auth requests"
  }

  # Rule 14: Mobile App Traffic Optimization
  rule {
    action   = "allow"
    priority = 6000
    match {
      expr {
        expression = <<-EOT
          request.headers['user-agent'].contains('RoadTripApp/') && 
          request.headers['x-app-version'] != ''
        EOT
      }
    }
    description = "Prioritize legitimate mobile app traffic"
  }

  # Rule 15: API Key Validation for High-Value Endpoints
  rule {
    action   = "deny(401)"
    priority = 7000
    match {
      expr {
        expression = <<-EOT
          request.path.matches('/api/booking/.*|/api/voice/synthesis') && 
          !request.headers['x-api-key'].matches('[a-zA-Z0-9]{32,}')
        EOT
      }
    }
    description = "API key requirement for premium features"
  }

  # Rule 16: Threat Intelligence Integration
  rule {
    action   = "deny(403)"
    priority = 8000
    match {
      expr {
        expression = "evaluateThreatIntelligence('iplist-known-malicious')"
      }
    }
    description = "Block IPs from threat intelligence feeds"
  }

  # Rule 17: Session Fixation Protection
  rule {
    action   = "deny(403)"
    priority = 8100
    match {
      expr {
        expression = <<-EOT
          request.query.contains('session_id') || 
          request.query.contains('PHPSESSID') || 
          request.query.contains('jsessionid')
        EOT
      }
    }
    description = "Prevent session fixation attacks"
  }

  # Rule 18: Emergency Lockdown Rule (Disabled by default)
  rule {
    action   = "deny(503)"
    priority = 100
    match {
      expr {
        expression = "origin.ip in ['0.0.0.0/0']"
      }
    }
    description = "Emergency lockdown - Enable during active attacks"
    preview     = true  # This makes the rule inactive by default
  }
}

# Cloud Armor Edge Security Policy for additional protection
resource "google_compute_security_policy" "roadtrip_edge_policy" {
  name        = "roadtrip-edge-policy-${var.environment}"
  description = "Edge security policy for enhanced protection"
  type        = "CLOUD_ARMOR_EDGE"
  project     = var.project_id

  # Rule 1: User-Agent filtering
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = <<-EOT
          request.headers['user-agent'].matches('.*([Bb]ot|[Cc]rawler|[Ss]pider|[Ss]craper).*') &&
          !request.headers['user-agent'].matches('.*(Googlebot|Bingbot).*')
        EOT
      }
    }
    description = "Block unwanted bots and crawlers"
  }

  # Rule 2: Referer validation
  rule {
    action   = "allow"
    priority = 2000
    match {
      expr {
        expression = <<-EOT
          request.headers['referer'] == '' || 
          request.headers['referer'].matches('https://(.*\.)?${var.domain_name}/.*')
        EOT
      }
    }
    description = "Validate referer headers"
  }

  # Default allow rule
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule"
  }
}

# Outputs for use in load balancer configuration
output "security_policy_id" {
  value       = google_compute_security_policy.roadtrip_policy.id
  description = "Cloud Armor security policy ID"
}

output "edge_security_policy_id" {
  value       = google_compute_security_policy.roadtrip_edge_policy.id
  description = "Cloud Armor edge security policy ID"
}

output "recaptcha_key" {
  value       = google_recaptcha_enterprise_key.roadtrip_key.name
  description = "reCAPTCHA Enterprise key name"
}