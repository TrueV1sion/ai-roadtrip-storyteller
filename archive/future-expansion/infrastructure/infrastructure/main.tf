terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket = "roadtrip-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "roadtrip_cluster" {
  name = "roadtrip-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# ECS Task Definition for the backend API
resource "aws_ecs_task_definition" "backend_task" {
  family                   = "roadtrip-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "roadtrip-backend"
      image     = "${aws_ecr_repository.backend_repo.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      
      # Non-sensitive environment variables
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "REDIS_HOST", value = aws_elasticache_cluster.redis.cache_nodes.0.address }
      ]
      
      # Sensitive environment variables from AWS Secrets Manager
      secrets = [
        { 
          name = "DATABASE_URL", 
          valueFrom = aws_secretsmanager_secret_version.database_url.arn 
        },
        {
          name = "SECRET_KEY",
          valueFrom = aws_secretsmanager_secret_version.jwt_secret.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

# ECS Service for the backend
resource "aws_ecs_service" "backend_service" {
  name            = "roadtrip-backend-service"
  cluster         = aws_ecs_cluster.roadtrip_cluster.id
  task_definition = aws_ecs_task_definition.backend_task.arn
  desired_count   = var.backend_instance_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_subnets.*.id
    security_groups  = [aws_security_group.backend_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend_tg.arn
    container_name   = "roadtrip-backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.backend_listener]

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# RDS PostgreSQL instance
resource "aws_db_instance" "postgres" {
  identifier             = "roadtrip-postgres"
  engine                 = "postgres"
  engine_version         = "13.7"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_type           = "gp2"
  name                   = var.db_name
  username               = var.db_username
  password               = var.db_password
  parameter_group_name   = "default.postgres13"
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  multi_az               = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "roadtrip-postgres-final-snapshot"
  deletion_protection    = true
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres_sg.id]

  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Redis ElastiCache for caching
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "roadtrip-redis"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis6.x"
  engine_version       = "6.2"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis_sg.id]
  
  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Application Load Balancer
resource "aws_lb" "backend_lb" {
  name               = "roadtrip-backend-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = aws_subnet.public_subnets.*.id

  enable_deletion_protection = true

  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "backend_logs" {
  name              = "/ecs/roadtrip-backend"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Auto-scaling configuration
resource "aws_appautoscaling_target" "backend_target" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.roadtrip_cluster.name}/${aws_ecs_service.backend_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 1
  max_capacity       = 10
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "backend-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend_target.resource_id
  scalable_dimension = aws_appautoscaling_target.backend_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

# S3 Bucket for backups
resource "aws_s3_bucket" "backup_bucket" {
  bucket = "roadtrip-backups-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backup_lifecycle" {
  bucket = aws_s3_bucket.backup_bucket.id

  rule {
    id     = "backup_retention"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
} 