# Security and Load Balancer Variables

# Domain Configuration
variable "domain_name" {
  description = "Base domain name for the application"
  type        = string
  default     = "roadtripai.com"
}

variable "subdomain" {
  description = "Subdomain for API endpoints"
  type        = string
  default     = "api"
}

variable "ssl_domains" {
  description = "List of domains for SSL certificate"
  type        = list(string)
  default     = ["api.roadtripai.com", "www.roadtripai.com"]
}

variable "allowed_domains" {
  description = "Allowed domains for reCAPTCHA"
  type        = list(string)
  default     = ["roadtripai.com", "www.roadtripai.com"]
}

variable "api_hosts" {
  description = "API host names"
  type        = list(string)
  default     = ["api.roadtripai.com"]
}

variable "cors_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default = [
    "https://roadtripai.com",
    "https://www.roadtripai.com",
    "http://localhost:3000",  # Development
    "http://localhost:8081",  # Mobile development
    "exp://",                 # Expo development
  ]
}

# DNS Configuration
variable "create_dns_records" {
  description = "Whether to create DNS records"
  type        = bool
  default     = false
}

variable "dns_zone_name" {
  description = "Cloud DNS zone name"
  type        = string
  default     = ""
}

# Security Configuration
variable "security_email" {
  description = "Email address for security alerts"
  type        = string
  default     = "security@roadtripai.com"
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key for critical alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "notification_channels" {
  description = "List of notification channel IDs for general alerts"
  type        = list(string)
  default     = []
}

# Rate Limiting Configuration
variable "global_rate_limit" {
  description = "Global rate limit per minute"
  type        = number
  default     = 1000
}

variable "api_rate_limit" {
  description = "API endpoint rate limit per minute"
  type        = number
  default     = 100
}

variable "expensive_endpoint_rate_limit" {
  description = "Rate limit for expensive endpoints per minute"
  type        = number
  default     = 20
}

# Geographic Restrictions
variable "blocked_countries" {
  description = "List of country codes to block"
  type        = list(string)
  default     = []  # Add country codes as needed
}

variable "allowed_countries" {
  description = "List of country codes to allow (empty means all)"
  type        = list(string)
  default     = []
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "Number of days to retain security logs"
  type        = number
  default     = 90
}

variable "alert_cooldown_period" {
  description = "Cooldown period for alerts in seconds"
  type        = number
  default     = 1800
}

# Performance Configuration
variable "backend_timeout_seconds" {
  description = "Backend service timeout in seconds"
  type        = number
  default     = 30
}

variable "max_backend_utilization" {
  description = "Maximum backend utilization percentage"
  type        = number
  default     = 0.8
}

variable "cdn_default_ttl" {
  description = "Default CDN TTL in seconds"
  type        = number
  default     = 3600
}

variable "cdn_max_ttl" {
  description = "Maximum CDN TTL in seconds"
  type        = number
  default     = 86400
}

# Circuit Breaker Configuration
variable "circuit_breaker_max_requests" {
  description = "Maximum requests for circuit breaker"
  type        = number
  default     = 1000
}

variable "circuit_breaker_max_connections" {
  description = "Maximum connections for circuit breaker"
  type        = number
  default     = 1000
}

variable "circuit_breaker_max_retries" {
  description = "Maximum retries for circuit breaker"
  type        = number
  default     = 3
}

# Health Check Configuration
variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 10
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
}

variable "health_check_threshold" {
  description = "Number of consecutive checks for healthy/unhealthy state"
  type        = number
  default     = 2
}

# Attack Detection Thresholds
variable "ddos_request_threshold" {
  description = "Request count threshold for DDoS detection"
  type        = number
  default     = 10000
}

variable "sql_injection_threshold" {
  description = "SQL injection attempt threshold for alerting"
  type        = number
  default     = 5
}

variable "rate_limit_violation_threshold" {
  description = "Rate limit violation threshold for alerting"
  type        = number
  default     = 100
}

variable "backend_latency_threshold_ms" {
  description = "Backend latency threshold in milliseconds"
  type        = number
  default     = 2000
}