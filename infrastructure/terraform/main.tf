terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # ★ Terraform の状態ファイルは、既存の S3 バケット & DynamoDB ロックテーブルを利用
  backend "s3" {
    bucket         = "mysfa-terraform-state" # すでにコンソールで作成済み
    key            = "terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "mysfa-terraform-lock" # すでにコンソールで作成済み（名前は実際のテーブル名に合わせて要調整）
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# VPC モジュール呼び出し（既存のまま利用）
# ============================================
module "vpc" {
  source = "./modules/vpc"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
}

# ============================================
# S3（static / media 用）モジュール呼び出し
# ============================================
module "s3_app" {
  source = "./modules/s3_app"

  project_name = var.project_name
  environment  = var.environment

  # 例: mysfa-deploy-files
  bucket_name = var.s3_bucket_name

  # CORS 用に使用（https://mysfa.net, https://www.mysfa.net を許可）
  domain_name = var.domain_name
}

# ============================================
# セキュリティグループ
# （デフォルトVPCの既存SGではなく、自作VPC用に新規作成）
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
# ECR / ECS（このあと順次モジュール化予定）
# ============================================

module "ecr_app" {
  source = "./modules/ecr_app"

  project_name = var.project_name
  environment  = var.environment

  # 例: mysfa-app など
  repository_name = "${var.project_name}-app"

  # 必要なら変える
  image_tag_mutability    = "IMMUTABLE"
  scan_on_push            = true
  lifecycle_policy_enabled = true
  lifecycle_keep_last      = 10
}

# ============================================
# IAM
# ============================================

module "ecs_iam" {
  source = "./modules/ecs_iam"

  project_name = var.project_name
  environment  = var.environment

  app_bucket_arn  = module.s3_app.bucket_arn
  app_bucket_name = module.s3_app.bucket_name

  # ロググループ名は、このあと作る CloudWatch Logs モジュールと合わせる想定
  cloudwatch_log_group_name = "/ecs/${var.project_name}-${var.environment}"
}

# ============================================
# ECS（このあと順次モジュール化予定）
# ============================================

# ============================================
# ECS サービスの例（別ファイルに切り出し予定）
# ============================================
# resource "aws_ecs_service" "main" {
#   ...
# }
