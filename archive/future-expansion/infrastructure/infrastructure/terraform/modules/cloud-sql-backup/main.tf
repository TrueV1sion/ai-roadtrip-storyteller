resource "google_sql_database_instance" "main" {
  name             = var.instance_name
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.instance_tier
    availability_type = var.availability_type
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    disk_autoresize   = true

    # Backup configuration - TASK-005
    backup_configuration {
      enabled                        = true
      start_time                     = var.backup_start_time
      point_in_time_recovery_enabled = var.enable_point_in_time_recovery
      transaction_log_retention_days = var.transaction_log_retention_days
      
      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    # Additional backup settings
    database_flags {
      name  = "log_bin_trust_function_creators"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = var.private_network_id
      require_ssl     = true

      authorized_networks {
        name  = "allow-internal"
        value = "10.0.0.0/8"
      }
    }

    # Maintenance window for backups
    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM
      update_track = "stable"
    }

    # Insights for monitoring
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = var.deletion_protection
}

# Automated backup verification
resource "google_cloud_scheduler_job" "backup_verification" {
  name        = "${var.instance_name}-backup-verification"
  description = "Verify daily backups are successful"
  schedule    = "0 6 * * *"  # Daily at 6 AM
  project     = var.project_id
  region      = var.region

  pubsub_target {
    topic_name = google_pubsub_topic.backup_notifications.id
    data = base64encode(jsonencode({
      action = "verify_backup"
      instance = google_sql_database_instance.main.name
    }))
  }
}

# Backup notifications
resource "google_pubsub_topic" "backup_notifications" {
  name    = "${var.instance_name}-backup-notifications"
  project = var.project_id
}

# Backup monitoring alert
resource "google_monitoring_alert_policy" "backup_failure" {
  display_name = "${var.instance_name} Backup Failure Alert"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Backup failed"
    
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/backup/count\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.main.name}\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      
      aggregations {
        alignment_period   = "86400s"  # 24 hours
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    notification_rate_limit {
      period = "3600s"  # 1 hour
    }
  }
}

# Export backups to GCS for long-term storage
resource "google_storage_bucket" "backup_bucket" {
  name          = "${var.project_id}-sql-backups"
  location      = var.region
  storage_class = "NEARLINE"
  project       = var.project_id

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = var.kms_key_id
  }
}

# Service account for backup operations
resource "google_service_account" "backup_account" {
  account_id   = "${var.instance_name}-backup-sa"
  display_name = "SQL Backup Service Account"
  project      = var.project_id
}

# Grant necessary permissions
resource "google_project_iam_member" "backup_permissions" {
  for_each = toset([
    "roles/cloudsql.admin",
    "roles/storage.admin",
    "roles/pubsub.publisher"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backup_account.email}"
}

# Output important values
output "instance_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "backup_bucket_name" {
  value = google_storage_bucket.backup_bucket.name
}

output "backup_service_account" {
  value = google_service_account.backup_account.email
}