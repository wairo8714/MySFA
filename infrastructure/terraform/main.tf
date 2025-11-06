terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "mysfa-terraform-state"  # tfstate保存用のS3バケット（手動作成が必要）
    key    = "terraform.tfstate"
    region = "ap-northeast-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# 最新のAmazon Linux 2 AMIを動的取得
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 既存のキーペアを参照
data "aws_key_pair" "main" {
  key_name = "${var.project_name}-keypair"
}

# デフォルトVPCを取得
data "aws_vpc" "default" {
  default = true
}

# デフォルトVPCのパブリックサブネットを取得（ALB用に最低2つ必要）
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

# 既存のセキュリティグループを参照（EC2用）
data "aws_security_group" "ec2" {
  name   = "mysfa-ec2-sg-8cb59333"
  vpc_id = data.aws_vpc.default.id
}

# 既存のセキュリティグループを参照（ALB用）
data "aws_security_group" "alb" {
  name   = "mysfa-alb-sg-8cb59333"
  vpc_id = data.aws_vpc.default.id
}

# EC2インスタンス（セキュア構成）
resource "aws_instance" "main" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = data.aws_key_pair.main.key_name  # 既存のキーペアを参照
  vpc_security_group_ids = [data.aws_security_group.ec2.id]
  subnet_id              = data.aws_subnets.public.ids[0]

  # user_dataは削除（Nginx設定はdeploy.ymlで転送されるため不要）
  # Docker/Docker Composeは既存インスタンスに手動でインストール済み、または別途インストールが必要

  tags = {
    Name = "${var.project_name}-server"
  }
}

# ECSタスク用セキュリティグループのルール（ALBからのHTTPアクセスを許可）
resource "aws_security_group_rule" "ecs_from_alb" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.alb.id
  security_group_id        = data.aws_security_group.ec2.id
  description              = "HTTP access from ALB to ECS tasks on port 8000"
}

# ACM証明書（DNS検証）
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

# Route 53 Hosted Zone
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# ACM証明書のDNS検証レコード
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

# ACM証明書の検証
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  timeouts {
    create = "5m"
  }
}

# ターゲットグループ
resource "aws_lb_target_group" "main" {
  name     = "${var.project_name}-tg-v2"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    path                = "/health/"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = {
    Name = "${var.project_name}-tg-v2"
  }
}

# ターゲットグループへのEC2インスタンス登録
# 注意: ECSサービスを使用する場合、このリソースは不要です。
# ECSサービスが自動的にターゲットグループにタスクを登録します。

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [data.aws_security_group.alb.id]
  subnets            = data.aws_subnets.public.ids

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# ALB HTTPリスナー（HTTPSへリダイレクト）
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
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

# ALB HTTPSリスナー
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

# Route 53 A Record（ALBのDNS名を指す）
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

# S3バケット（静的・メディア用）
resource "aws_s3_bucket" "mysfa_bucket" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "${var.project_name}-bucket"
    Environment = "production"
  }
}

# S3バケットの所有権制御（ACLを有効にするため）
resource "aws_s3_bucket_ownership_controls" "mysfa_bucket_ownership" {
  bucket = aws_s3_bucket.mysfa_bucket.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# S3バケットACL
resource "aws_s3_bucket_acl" "mysfa_bucket_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.mysfa_bucket_ownership]
  
  bucket = aws_s3_bucket.mysfa_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "mysfa_bucket_versioning" {
  bucket = aws_s3_bucket.mysfa_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3バケットのPublic Access Block設定
resource "aws_s3_bucket_public_access_block" "mysfa_bucket_pab" {
  bucket = aws_s3_bucket.mysfa_bucket.id

  block_public_acls       = true
  block_public_policy     = false  # ポリシーを許可するためfalse
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "mysfa_bucket_policy" {
  depends_on = [aws_s3_bucket_public_access_block.mysfa_bucket_pab]
  
  bucket = aws_s3_bucket.mysfa_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowDjangoAccess"
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.mysfa_bucket.arn}/*"
      }
    ]
  })
}

# ECRリポジトリを作成
resource "aws_ecr_repository" "mysfa" {
  name                 = "mysfa_ver2"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-ecr"
    Environment = "production"
  }
}

# 古いDockerイメージを自動削除するライフサイクルポリシー
resource "aws_ecr_lifecycle_policy" "mysfa_policy" {
  repository = aws_ecr_repository.mysfa.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECRリポジトリURLを出力
output "ecr_repository_url" {
  value       = aws_ecr_repository.mysfa.repository_url
  description = "ECR repository URL for Docker image pushes"
}

# ===============================
# ECS クラスタ
# ===============================
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-ecs-cluster"
  }
}

# ===============================
# ECS タスク定義
# ===============================
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode              = "awsvpc"
  requires_compatibilities  = ["FARGATE"]
  cpu                       = "512"
  memory                    = "1024"
  execution_role_arn        = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn             = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "${aws_ecr_repository.mysfa.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-task"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ===============================
# ECS サービス
# ===============================
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = data.aws_subnets.public.ids
    assign_public_ip = true
    security_groups = [data.aws_security_group.ec2.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = "web"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]
}

# ===============================
# ECS タスク実行ロール
# ===============================
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# CloudWatch Logs ロググループ
resource "aws_cloudwatch_log_group" "ecs_task" {
  name              = "/ecs/${var.project_name}-task"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}
