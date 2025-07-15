# Storage Module for Road Trip Infrastructure

# Static assets bucket
resource "google_storage_bucket" "static_assets" {
  name                        = "${var.project_id}-static-assets"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }
}

# User uploads bucket
resource "google_storage_bucket" "user_uploads" {
  name                        = "${var.project_id}-user-uploads"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  versioning {
    enabled = true
  }
}

# Backup bucket
resource "google_storage_bucket" "backups" {
  name                        = "${var.project_id}-backups"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
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

# Logs bucket
resource "google_storage_bucket" "logs" {
  name                        = "${var.project_id}-logs"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Terraform state bucket (if not already exists)
resource "google_storage_bucket" "terraform_state" {
  name                        = "${var.project_id}-terraform-state"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

# IAM bindings for service accounts
resource "google_storage_bucket_iam_member" "static_assets_viewer" {
  bucket = google_storage_bucket.static_assets.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Outputs
output "static_assets_bucket" {
  value = google_storage_bucket.static_assets.name
}

output "user_uploads_bucket" {
  value = google_storage_bucket.user_uploads.name
}

output "backups_bucket" {
  value = google_storage_bucket.backups.name
}

output "logs_bucket" {
  value = google_storage_bucket.logs.name
}

output "static_assets_url" {
  value = "https://storage.googleapis.com/${google_storage_bucket.static_assets.name}"
}