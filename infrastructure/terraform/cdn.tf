# CDN Configuration for AI Road Trip Storyteller

resource "google_compute_global_address" "cdn_ip" {
  name = "roadtrip-cdn-ip"
}

resource "google_compute_backend_bucket" "static_assets" {
  name        = "roadtrip-static-assets"
  bucket_name = google_storage_bucket.static_assets.name
  enable_cdn  = true
  
  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    client_ttl        = 3600
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
    
    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = false
    }
  }
}

resource "google_storage_bucket" "static_assets" {
  name          = "${var.project_id}-static-assets"
  location      = "US"
  force_destroy = false
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_compute_url_map" "cdn" {
  name            = "roadtrip-cdn-url-map"
  default_service = google_compute_backend_bucket.static_assets.id
  
  host_rule {
    hosts        = ["cdn.roadtrip.ai"]
    path_matcher = "assets"
  }
  
  path_matcher {
    name            = "assets"
    default_service = google_compute_backend_bucket.static_assets.id
    
    path_rule {
      paths   = ["/images/*"]
      service = google_compute_backend_bucket.static_assets.id
    }
    
    path_rule {
      paths   = ["/audio/*"]
      service = google_compute_backend_bucket.voice_assets.id
    }
  }
}

resource "google_compute_backend_bucket" "voice_assets" {
  name        = "roadtrip-voice-assets"
  bucket_name = google_storage_bucket.voice_assets.name
  enable_cdn  = true
  
  cdn_policy {
    cache_mode  = "CACHE_ALL_STATIC"
    client_ttl  = 7200
    default_ttl = 7200
    max_ttl     = 172800
  }
}

resource "google_storage_bucket" "voice_assets" {
  name          = "${var.project_id}-voice-assets"
  location      = "US"
  force_destroy = false
}

# CloudFlare integration for global CDN
resource "cloudflare_record" "cdn" {
  zone_id = var.cloudflare_zone_id
  name    = "cdn"
  value   = google_compute_global_address.cdn_ip.address
  type    = "A"
  ttl     = 1
  proxied = true
}

output "cdn_url" {
  value = "https://cdn.roadtrip.ai"
}
