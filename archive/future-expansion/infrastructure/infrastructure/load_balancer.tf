# Target Group for backend
resource "aws_lb_target_group" "backend_tg" {
  name        = "roadtrip-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = {
    Name        = "roadtrip-backend-tg"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# HTTP Listener
resource "aws_lb_listener" "backend_http" {
  load_balancer_arn = aws_lb.backend_lb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS Listener with SSL certificate
resource "aws_lb_listener" "backend_listener" {
  load_balancer_arn = aws_lb.backend_lb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.backend_cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend_tg.arn
  }

  depends_on = [aws_acm_certificate_validation.cert_validation]
}

# ACM Certificate for HTTPS
resource "aws_acm_certificate" "backend_cert" {
  domain_name       = "api.roadtrip.example.com"
  validation_method = "DNS"

  tags = {
    Name        = "roadtrip-backend-cert"
    Environment = var.environment
    Project     = "RoadTrip"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Certificate Validation
resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = aws_acm_certificate.backend_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Route53 Records for Certificate Validation
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.backend_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.roadtrip_zone.zone_id
}

# Route53 Zone
resource "aws_route53_zone" "roadtrip_zone" {
  name = "roadtrip.example.com"

  tags = {
    Name        = "roadtrip-zone"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# API Route53 Record
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.roadtrip_zone.zone_id
  name    = "api.roadtrip.example.com"
  type    = "A"

  alias {
    name                   = aws_lb.backend_lb.dns_name
    zone_id                = aws_lb.backend_lb.zone_id
    evaluate_target_health = true
  }
} 