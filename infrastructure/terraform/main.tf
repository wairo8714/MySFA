terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "mysfa-terraform-state"
    key     = "terraform.tfstate"
    region  = "ap-northeast-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# ネットワーク & セキュリティ設定
# ============================================
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_security_group" "ecs_tasks" {
  id = "sg-04652f374cab72e64"
}

data "aws_security_group" "alb" {
  name   = "mysfa-alb-sg-8cb59333"
  vpc_id = data.aws_vpc.default.id
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
    Name = "${var.project_name}-cert"
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
  name        = "${var.project_name}-tg-v2"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled   = true
    path      = "/health/"
    matcher   = "200"
    interval  = 30
    timeout   = 10
  }
}

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [data.aws_security_group.alb.id]
  subnets            = data.aws_subnets.public.ids
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

# ============================================
# S3 / ECR / IAM / ECS
# ============================================
resource "aws_s3_bucket" "mysfa_bucket" {
  bucket = var.s3_bucket_name
}

resource "aws_s3_bucket_ownership_controls" "mysfa_bucket_ownership" {
  bucket = aws_s3_bucket.mysfa_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "mysfa_bucket_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.mysfa_bucket_ownership]
  bucket     = aws_s3_bucket.mysfa_bucket.id
  acl        = "private"
}

resource "aws_s3_bucket_policy" "mysfa_bucket_static_read" {
  bucket = aws_s3_bucket.mysfa_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowPublicReadForStaticAndMedia",
        Effect    = "Allow",
        Principal = "*",
        Action    = ["s3:GetObject"],
        Resource = [
          "${aws_s3_bucket.mysfa_bucket.arn}/static/*",
          "${aws_s3_bucket.mysfa_bucket.arn}/media/*"
        ]
      }
    ]
  })
}

resource "aws_s3_bucket_versioning" "mysfa_bucket_versioning" {
  bucket = aws_s3_bucket.mysfa_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_ecr_repository" "mysfa" {
  name = "mysfa_ver2"
}

# ============================================
# IAM ロールとポリシー（ECS Exec 用含む）
# ============================================
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = { Service = "ecs-tasks.amazonaws.com" },
      Effect = "Allow"
    }]
  })
}

# ECS 実行用ポリシー
resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Exec 用の SSM ポリシー
resource "aws_iam_policy" "ecs_exec_ssm_policy" {
  name        = "${var.project_name}-ecs-exec-ssm-policy"
  description = "Allow ECS Exec to use SSM Session Manager"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ssm:StartSession",
          "ssm:DescribeSessions",
          "ssm:GetConnectionStatus",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_exec_ssm" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_exec_ssm_policy.arn
}

# ============================================
# ECS クラスター
# ============================================
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

# ============================================
# ECS タスク定義
# ============================================
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name      = "web"
    image     = "${aws_ecr_repository.mysfa.repository_url}:latest"
    essential = true
    portMappings = [
      { containerPort = 8000, hostPort = 8000 }
    ]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "DEBUG", value = "False" },
      { name = "FORCE_HTTPS", value = "True" },
      { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
      { name = "MYSQL_HOST", value = var.mysql_host },
      { name = "MYSQL_DATABASE", value = var.mysql_database },
      { name = "MYSQL_USER", value = var.mysql_user },
      { name = "MYSQL_PASSWORD", value = var.mysql_password },
      { name = "SECRET_KEY", value = var.secret_key },
      { name = "USE_S3", value = "True" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "AWS_STORAGE_BUCKET_NAME", value = var.s3_bucket_name }
    ]

    logConfiguration = {
      logDriver = "awslogs",
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}-task",
        "awslogs-region"        = var.aws_region,
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# ============================================
# ECS サービス（ECS Exec 有効）
# ============================================
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
    assign_public_ip = true
    security_groups  = [data.aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = "web"
    container_port   = 8000
  }

  enable_execute_command = true

  depends_on = [aws_lb_listener.https]
}
