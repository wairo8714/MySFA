terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Terraform の状態ファイルは、既存の S3 バケット & DynamoDB ロックテーブルを利用
  backend "s3" {
    bucket         = "mysfa-terraform-state"
    key            = "terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "mysfa-terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# VPC
# ============================================
module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# ============================================
# S3
# ============================================
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment

  # 例: mysfa-deploy-files
  bucket_name = var.s3_bucket_name

  # CORS 用に使用（https://mysfa.net, https://www.mysfa.net を許可）
  domain_name = var.domain_name
}

# ============================================
# セキュリティグループ
# ============================================

# ALB用セキュリティグループ
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from Internet"
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
    Name        = "${var.project_name}-alb-sg"
    Environment = var.environment
  }
}

# ECSタスク用セキュリティグループ
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = module.vpc.vpc_id

  # ALB からのHTTP(80)のみ許可
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-tasks-sg"
    Environment = var.environment
  }
}

# ============================================
# ACM / Route53 / ALB
# ============================================

resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-cert"
    Environment = var.environment
  }
}

data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
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
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

resource "aws_lb_target_group" "main" {
  name_prefix = "tg-"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  lifecycle {
    create_before_destroy = true
  }

  health_check {
    enabled             = true
    path                = "/health/"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "${var.project_name}-tg"
    Environment = var.environment
  }
}

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnet_ids

  tags = {
    Name        = "${var.project_name}-alb"
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
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

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

resource "aws_route53_record" "main" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ============================================
# ECR
# ============================================

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment

  repository_name = "${var.project_name}-app"

  image_tag_mutability     = "MUTABLE"
  scan_on_push             = true
  lifecycle_policy_enabled = true
  lifecycle_keep_last      = 10
}

# ============================================
# IAM（ECS 用ロール）
# ============================================

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment

  app_bucket_arn  = module.s3.bucket_arn
  app_bucket_name = module.s3.bucket_name
 
  cloudwatch_log_group_name = "/ecs/${var.project_name}-${var.environment}"
}

# ============================================
# RDS (MySQL)
# ============================================

module "rds" {
  source = "./modules/rds"

  project_name = var.project_name
  environment  = var.environment

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

   allowed_security_group_ids = [aws_security_group.ecs_tasks.id]

  db_name  = var.mysql_database
  username = var.mysql_user
  password = var.mysql_password

  engine_version          = "8.0"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  backup_retention_period = 7
  multi_az                = false
  publicly_accessible     = false
  deletion_protection     = false
  apply_immediately       = true
}

# ============================================
# ECS（RDS 接続版・web コンテナのみ）
# ============================================

module "ecs" {
  source = "./modules/ecs"

  project_name = var.project_name
  environment  = var.environment

  cluster_name = "${var.project_name}-${var.environment}-cluster"

  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [aws_security_group.ecs_tasks.id]

  alb_target_group_arn = aws_lb_target_group.main.arn

  task_role_arn      = module.iam.task_role_arn
  execution_role_arn = module.iam.task_execution_role_arn

  container_image = "${module.ecr.repository_url}:latest"
  container_port  = 80

  task_cpu    = "256"
  task_memory = "512"

  desired_count = 1

  aws_region = var.aws_region

  # ===== Django env =====
  secret_key    = var.secret_key
  debug         = var.debug
  allowed_hosts = var.allowed_hosts

  mysql_host     = module.rds.db_endpoint
  mysql_port     = module.rds.db_port
  mysql_database = var.mysql_database
  mysql_user     = var.mysql_user
  mysql_password = var.mysql_password

  s3_bucket_name = module.s3.bucket_name
  use_s3         = true

  log_group_name        = "/ecs/${var.project_name}-${var.environment}"
  log_retention_in_days = 30
}
