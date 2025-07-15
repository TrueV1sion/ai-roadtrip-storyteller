# Redis (Memorystore) Module for Road Trip Infrastructure

resource "google_redis_instance" "cache" {
  name               = "${var.project_id}-redis"
  tier               = var.ha_enabled ? "STANDARD_HA" : "BASIC"
  memory_size_gb     = var.memory_size
  region             = var.region
  location_id        = var.ha_enabled ? null : "${var.region}-a"
  alternative_location_id = var.ha_enabled ? "${var.region}-b" : null

  redis_version     = var.redis_version
  display_name      = "Road Trip Redis Cache"
  reserved_ip_range = "10.3.0.0/29"

  authorized_network = var.network_id

  redis_configs = {
    "maxmemory-policy" = "allkeys-lru"
    "notify-keyspace-events" = "Ex"
  }

  persistence_config {
    persistence_mode = var.persistence_enabled ? "RDB" : "DISABLED"
    rdb_snapshot_period = var.persistence_enabled ? "ONE_HOUR" : null
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Generate auth string
resource "random_password" "redis_auth" {
  length  = 32
  special = true
}

# Outputs
output "host" {
  value = google_redis_instance.cache.host
}

output "port" {
  value = google_redis_instance.cache.port
}

output "auth_string" {
  value     = google_redis_instance.cache.auth_string != "" ? google_redis_instance.cache.auth_string : random_password.redis_auth.result
  sensitive = true
}

output "current_location_id" {
  value = google_redis_instance.cache.current_location_id
}

output "connection_string" {
  value     = "redis://:${google_redis_instance.cache.auth_string != "" ? google_redis_instance.cache.auth_string : random_password.redis_auth.result}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  sensitive = true
}