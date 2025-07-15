# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "roadtrip-vpc"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Public Subnets
resource "aws_subnet" "public_subnets" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "roadtrip-public-subnet-${count.index + 1}"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Private Subnets
resource "aws_subnet" "private_subnets" {
  count                   = length(var.private_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "roadtrip-private-subnet-${count.index + 1}"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "roadtrip-igw"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# NAT Gateway for private subnets
resource "aws_eip" "nat_ip" {
  vpc = true

  tags = {
    Name        = "roadtrip-nat-eip"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_ip.id
  subnet_id     = aws_subnet.public_subnets[0].id

  tags = {
    Name        = "roadtrip-nat"
    Environment = var.environment
    Project     = "RoadTrip"
  }

  depends_on = [aws_internet_gateway.igw]
}

# Route tables and associations
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = "roadtrip-public-rt"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }

  tags = {
    Name        = "roadtrip-private-rt"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_route_table_association" "public_rt_assoc" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "private_rt_assoc" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private_subnets[count.index].id
  route_table_id = aws_route_table.private_rt.id
}

# DB Subnet Group
resource "aws_db_subnet_group" "postgres" {
  name        = "roadtrip-db-subnet-group"
  description = "Database subnet group for RoadTrip"
  subnet_ids  = aws_subnet.private_subnets.*.id

  tags = {
    Name        = "roadtrip-db-subnet-group"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "redis" {
  name        = "roadtrip-elasticache-subnet-group"
  description = "ElastiCache subnet group for RoadTrip"
  subnet_ids  = aws_subnet.private_subnets.*.id
}

# Security Groups
resource "aws_security_group" "lb_sg" {
  name        = "roadtrip-lb-sg"
  description = "Security group for load balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "roadtrip-lb-sg"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_security_group" "backend_sg" {
  name        = "roadtrip-backend-sg"
  description = "Security group for backend service"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.lb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "roadtrip-backend-sg"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_security_group" "postgres_sg" {
  name        = "roadtrip-postgres-sg"
  description = "Security group for PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "roadtrip-postgres-sg"
    Environment = var.environment
    Project     = "RoadTrip"
  }
}

resource "aws_security_group" "redis_sg" {
  name        = "roadtrip-redis-sg"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "roadtrip-redis-sg"
    Environment = var.environment
    Project     = "RoadTrip"
  }
} 