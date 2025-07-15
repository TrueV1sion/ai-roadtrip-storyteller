# AWS Secrets Manager resources for sensitive application data

# Database URL secret
resource "aws_secretsmanager_secret" "database_url" {
  name        = "roadtrip/database_url"
  description = "Database connection URL for the RoadTrip application"
  
  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
  
  # Wait for RDS instance to be fully created before creating the secret
  depends_on = [aws_db_instance.postgres]
}

# JWT Secret Key
resource "aws_secretsmanager_secret" "jwt_secret" {
  name        = "roadtrip/jwt_secret"
  description = "JWT signing key for authentication"
  
  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

# Google Maps API Key
resource "aws_secretsmanager_secret" "maps_api_key" {
  name        = "roadtrip/maps_api_key"
  description = "Google Maps API Key"
  
  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_secretsmanager_secret_version" "maps_api_key" {
  secret_id     = aws_secretsmanager_secret.maps_api_key.id
  secret_string = var.maps_api_key
}

# Spotify API credentials
resource "aws_secretsmanager_secret" "spotify_credentials" {
  name        = "roadtrip/spotify_credentials"
  description = "Spotify API credentials"
  
  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_secretsmanager_secret_version" "spotify_credentials" {
  secret_id = aws_secretsmanager_secret.spotify_credentials.id
  secret_string = jsonencode({
    client_id     = var.spotify_client_id
    client_secret = var.spotify_client_secret
  })
}

# Grant ECS task execution role permission to read secrets
resource "aws_iam_policy" "secrets_access" {
  name        = "roadtrip-secrets-access-policy"
  description = "Allows the ECS task to access secrets in Secrets Manager"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
        ],
        Effect = "Allow",
        Resource = [
          aws_secretsmanager_secret.database_url.arn,
          aws_secretsmanager_secret.jwt_secret.arn,
          aws_secretsmanager_secret.maps_api_key.arn,
          aws_secretsmanager_secret.spotify_credentials.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_access_attachment" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}