# Terraform 設計案 - 修正版（VPC自作・RDS削除・最適化）

## 📋 概要

このドキュメントは、以下の要件に基づいてTerraformを刷新する設計案です。

### 要件

1. **VPCを自作** - デフォルトVPCではなく、カスタムVPCを作成
2. **Private/Publicサブネットの使い分け** - 適切なネットワーク設計
3. **RDSを使わない** - 費用削減のため、ECSタスク内でMySQLコンテナを実行
4. **無駄な設定を排除** - 必要最小限のリソースのみ
5. **IAMは既存を使用** - `mysfa-terraform`は既に作成済み（Terraformで管理しない）

### 対象リソース

1. **VPC** - カスタムVPC（パブリック/プライベートサブネット）
2. **ALB** - Application Load Balancer
3. **Route53** (mysfa.net) - DNS管理
4. **ECS: Fargate** (Nginx + Gunicorn + Django + MySQL) - コンテナ実行環境
5. **S3** - static/media保存用
6. **CloudWatch** - ログとモニタリング
7. **ECR** - Dockerイメージリポジトリ

---

## 🏗️ アーキテクチャ概要

```
Internet
    ↓
Route53 (mysfa.net)
    ↓
ALB (アプリケーション用)
    ↓
    ACM Certificate (SSL/TLS)
        ↓
    ALB Listener (HTTPS:443)
        ↓
    Target Group
        ↓
    ECS Service (Fargate) - Public Subnet
        ↓
    ECS Task Definition
        ├─ Container: web (Nginx + Gunicorn + Django)
        ├─ Container: db (MySQL)
        ├─ IAM Task Execution Role (ECR, CloudWatch Logs)
        ├─ IAM Task Role (S3)
        └─ Security Group
            ↓
    S3 Bucket (static/media) - 直接アクセス
```

---

## 📁 ファイル構成（最適化版）

```
infrastructure/terraform/
├── main.tf                    # メインリソース定義（統合）
├── variables.tf               # 変数定義
├── outputs.tf                 # 出力定義
├── terraform.tfvars            # 変数値（gitignore推奨）
└── backend.tf                 # バックエンド設定（オプション）
```

**注意**: シンプルにするため、ファイルを分離せず`main.tf`に統合

---

## 🔧 リソース詳細設計

### 1. VPC & ネットワーク

**目的**: カスタムVPCと適切なサブネット設計

```hcl
# main.tf

# ============================================
# VPC & ネットワーク
# ============================================

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# インターネットゲートウェイ
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# パブリックサブネット（ALB、ECSタスク用）
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    Type = "public"
  }
}

# プライベートサブネット（将来的な拡張用、現在は使用しない）
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
    Type = "private"
  }
}

# パブリックルートテーブル
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# パブリックサブネットとルートテーブルの関連付け
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# 利用可能なAZを取得
data "aws_availability_zones" "available" {
  state = "available"
}
```

---

### 2. セキュリティグループ

**目的**: 最小権限のセキュリティ設定

```hcl
# ============================================
# セキュリティグループ
# ============================================

# ALB用セキュリティグループ
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

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
    Name = "${var.project_name}-alb-sg"
  }
}

# ECSタスク用セキュリティグループ
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # MySQLコンテナへのアクセス（同一タスク内のコンテナ間通信は自動的に許可）
  # 外部からのアクセスは不要

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}
```

---

### 3. S3 バケット

**目的**: 静的ファイル・メディアファイル保存用

```hcl
# ============================================
# S3 バケット
# ============================================

# アプリケーション用S3バケット
resource "aws_s3_bucket" "app" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "${var.project_name}-static-storage"
    Environment = var.environment
  }
}

# バージョニング
resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id

  versioning_configuration {
    status = "Enabled"
  }
}

# パブリックアクセスブロック
resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets  = true
}

# バケットポリシー（ECSタスクからのアクセスのみ許可、必要に応じてパブリック読み取りも許可可能）
resource "aws_s3_bucket_policy" "app" {
  bucket = aws_s3_bucket.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowECSTaskAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.app.arn,
          "${aws_s3_bucket.app.arn}/*"
        ]
      },
      {
        Sid    = "AllowPublicReadAccess"
        Effect = "Allow"
        Principal = "*"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.app.arn}/*"
        Condition = {
          StringEquals = {
            "s3:ExistingObjectTag/public" = "true"
          }
        }
      }
    ]
  })
}

# CORS設定（必要に応じて）
resource "aws_s3_bucket_cors_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = [
      "https://${var.domain_name}",
      "https://www.${var.domain_name}"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
```

**注意**: Terraform状態ファイル用のS3バケットは既に存在するため、ここでは作成しない

---


### 5. ALB & Route53

**目的**: ロードバランシングとDNS管理

**注意**: お名前.comでドメインを取得した場合、Route53ホストゾーンを新規作成し、お名前.com側でネームサーバーをRoute53に変更する必要があります。詳細は「お名前.comでのネームサーバー設定手順」を参照してください。

```hcl
# ============================================
# ALB & Route53
# ============================================

# Route53 Hosted Zone（新規作成）
# お名前.comでドメインを取得した場合、このホストゾーンを作成後、
# お名前.com側でネームサーバーをRoute53に変更する必要があります
resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Name        = "${var.project_name}-hosted-zone"
    Environment = var.environment
  }
}

# ACM証明書（ALB用）
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
  zone_id         = aws_route53_zone.main.zone_id
}

# ACM証明書の検証
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# ターゲットグループ
resource "aws_lb_target_group" "main" {
  name     = "${var.project_name}-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health/"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30

  tags = {
    Name = "${var.project_name}-tg"
  }
}

# ALB HTTPリスナー（HTTPSへリダイレクト）
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

# ALB HTTPSリスナー
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

# Route53レコード（ALB用）
resource "aws_route53_record" "main" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
```

---

### 6. ECR

**目的**: Dockerイメージリポジトリ

```hcl
# ============================================
# ECR リポジトリ
# ============================================

resource "aws_ecr_repository" "app" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

# ライフサイクルポリシー
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

---

### 7. CloudWatch Logs

**目的**: ログ管理

```hcl
# ============================================
# CloudWatch Logs
# ============================================

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}-task"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}
```

---

### 8. IAM ロール

**目的**: ECSタスク実行用（IAMユーザーは既存を使用）

```hcl
# ============================================
# IAM ロール（IAMユーザーは既存を使用）
# ============================================

# タスク実行ロール（ECR、CloudWatch Logsへのアクセス）
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# タスクロール（アプリケーション用：S3へのアクセス）
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-role"
  }
}

# S3アクセス用ポリシー
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project_name}-ecs-task-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.app.arn,
          "${aws_s3_bucket.app.arn}/*"
        ]
      }
    ]
  })
}
```

---

### 9. ECS

**目的**: コンテナ実行環境（Nginx + Gunicorn + Django + MySQL）

```hcl
# ============================================
# ECS
# ============================================

# ECSクラスター
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# ECSタスク定義（web + dbコンテナ）
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    # Webコンテナ（Nginx + Gunicorn + Django）
    {
      name  = "web"
      image = "${aws_ecr_repository.app.repository_url}:latest"

      essential = true

      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "SECRET_KEY", value = var.secret_key },
        { name = "DEBUG", value = tostring(var.debug) },
        { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
        { name = "MYSQL_DATABASE", value = var.mysql_database },
        { name = "MYSQL_USER", value = var.mysql_user },
        { name = "MYSQL_PASSWORD", value = var.mysql_password },
        { name = "MYSQL_HOST", value = "localhost" },  # 同一タスク内のコンテナ
        { name = "MYSQL_PORT", value = "3306" },
        { name = "S3_BUCKET_NAME", value = aws_s3_bucket.app.id },
        { name = "AWS_STORAGE_BUCKET_NAME", value = aws_s3_bucket.app.id },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "FORCE_HTTPS", value = "true" },
        { name = "DOMAIN_NAME", value = var.domain_name },
        { name = "USE_S3", value = "true" }
      ]

      # S3アクセス用の環境変数（IAMロールを使用する場合は不要だが、互換性のため）
      # 実際のアクセスはIAMロールで行う

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:80/health/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs-web"
        }
      }

      dependsOn = [
        {
          containerName = "db"
          condition     = "HEALTHY"
        }
      ]
    },
    # MySQLコンテナ
    {
      name  = "db"
      image = "mysql:8.0"

      essential = true

      environment = [
        { name = "MYSQL_ROOT_PASSWORD", value = var.mysql_root_password },
        { name = "MYSQL_DATABASE", value = var.mysql_database },
        { name = "MYSQL_USER", value = var.mysql_user },
        { name = "MYSQL_PASSWORD", value = var.mysql_password }
      ]

      portMappings = [
        {
          containerPort = 3306
          hostPort      = 3306
          protocol      = "tcp"
        }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "mysqladmin ping -h localhost || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs-db"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-task"
  }
}

# ECSサービス
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
    security_groups  = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = "web"
    container_port   = 80
  }

  enable_execute_command = true

  depends_on = [
    aws_lb_listener.https
  ]

  tags = {
    Name = "${var.project_name}-service"
  }
}
```

**注意**: MySQLコンテナは同一タスク内で実行されるため、`MYSQL_HOST=localhost`で接続可能

---

## 📝 変数定義（最適化版）

```hcl
# variables.tf

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "mysfa"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

# VPC設定
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]  # 2つのAZ用
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]  # 将来的な拡張用
}

# ドメイン設定
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "mysfa.net"
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS"
  type        = string
  default     = "mysfa.net,www.mysfa.net"
}

# アプリケーション設定
variable "secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "debug" {
  description = "Django DEBUG mode"
  type        = bool
  default     = false
}

# MySQL設定
variable "mysql_database" {
  description = "MySQL database name"
  type        = string
}

variable "mysql_user" {
  description = "MySQL user"
  type        = string
}

variable "mysql_password" {
  description = "MySQL password"
  type        = string
  sensitive   = true
}

variable "mysql_root_password" {
  description = "MySQL root password"
  type        = string
  sensitive   = true
}

# S3設定
variable "s3_bucket_name" {
  description = "S3 bucket name for static and media files"
  type        = string
}

# ECR設定
variable "ecr_repository_name" {
  description = "ECR repository name"
  type        = string
  default     = "mysfa_ver2"
}

# ECS設定
variable "ecs_task_cpu" {
  description = "ECS task CPU units (256, 512, 1024, etc.)"
  type        = number
  default     = 1024  # web + dbコンテナ用に増やす
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 2048  # web + dbコンテナ用に増やす
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

# CloudWatch設定
variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 7
}

```

---

## 📤 出力定義

```hcl
# outputs.tf

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.main.arn
}

output "acm_certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = aws_acm_certificate.main.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.main.name
}

output "s3_bucket_name" {
  description = "S3 bucket name for app files"
  value       = aws_s3_bucket.app.id
}

output "application_url_https" {
  description = "HTTPS URL to access the application"
  value       = "https://${var.domain_name}"
}

output "route53_name_servers" {
  description = "Route53 name servers for domain configuration"
  value       = aws_route53_zone.main.name_servers
}

output "route53_zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.main.zone_id
}

```

---

## 🔄 主な変更点

### 削除したリソース

1. ❌ **RDS** - 費用削減のため削除
2. ❌ **CloudFront** - シンプル化のため削除（S3に直接アクセス）
3. ❌ **IAMユーザー作成** - 既存の`mysfa-terraform`を使用
4. ❌ **EC2インスタンス** - ECS Fargateのみ使用
5. ❌ **DynamoDB** - Terraform状態ロック用（既存のS3バケットを使用）
6. ❌ **NATゲートウェイ** - プライベートサブネットは将来的な拡張用（現在は未使用）

### 追加・変更したリソース

1. ✅ **カスタムVPC** - デフォルトVPCではなく自作
2. ✅ **パブリック/プライベートサブネット** - 適切なネットワーク設計
3. ✅ **インターネットゲートウェイ** - パブリックサブネット用
4. ✅ **ECSタスク定義にMySQLコンテナ追加** - 同一タスク内で実行

### 最適化した点

1. **ファイル統合** - `main.tf`に統合（シンプル化）
2. **不要な設定削除** - 使用しないリソースを削除
3. **セキュリティグループ最適化** - 最小権限の原則
4. **コスト最適化** - RDS削除、NATゲートウェイ不要

---

## ⚠️ 重要な注意事項

1. **MySQLコンテナ**: 同一タスク内で実行されるため、`MYSQL_HOST=localhost`で接続
2. **データ永続化**: ECS Fargateではボリュームマウントが制限されるため、データベースの永続化には注意が必要
3. **IAMユーザー**: 既存の`mysfa-terraform`を使用するため、Terraformで管理しない
4. **プライベートサブネット**: 現在は未使用だが、将来的な拡張用に作成
5. **S3アクセス**: CloudFrontを使わないため、S3バケットへの直接アクセス（必要に応じてパブリック読み取りを許可）
6. **Route53ホストゾーン**: お名前.comでドメインを取得した場合、Route53ホストゾーンを新規作成し、お名前.com側でネームサーバーをRoute53に変更する必要があります。ネームサーバーの変更が反映されるまで（数時間〜24時間）、DNSレコードは機能しません。

---

## 🚀 実装手順

1. **VPCとネットワークリソース**を先に作成
2. **セキュリティグループ**を作成
3. **S3バケット**を作成
4. **ECRリポジトリ**を作成
5. **Route53ホストゾーン**を作成
6. **お名前.comでネームサーバーをRoute53に変更**（重要）
7. **ALBとACM証明書**を設定
8. **IAMロール**を作成
9. **CloudWatch Logs**を作成
10. **ECSクラスター、タスク定義、サービス**を作成

---

## 📝 お名前.comでのネームサーバー設定手順

### 前提条件

- お名前.comでドメイン（`mysfa.net`）を取得済み
- Route53ホストゾーンをTerraformで作成済み

### ステップ1: Route53のネームサーバーを取得

TerraformでRoute53ホストゾーンを作成後、以下のコマンドでネームサーバーを取得：

```bash
# Terraformでホストゾーンを作成
terraform apply

# ネームサーバーを取得
terraform output route53_name_servers
```

出力例：
```
route53_name_servers = [
  "ns-1234.awsdns-56.com",
  "ns-5678.awsdns-12.net",
  "ns-9012.awsdns-34.org",
  "ns-3456.awsdns-78.co.uk"
]
```

または、AWSコンソールから：
1. Route53 → ホストゾーン → `mysfa.net` を選択
2. 「ネームサーバー」タブをクリック
3. 4つのネームサーバーをコピー

### ステップ2: お名前.comでネームサーバーを変更

1. **お名前.comにログイン**
   - https://www.onamae.com/ にアクセス
   - お名前.com IDとパスワードでログイン

2. **ドメイン管理画面に移動**
   - 「ドメイン」→「ドメイン一覧」をクリック
   - 対象ドメイン（`mysfa.net`）を選択

3. **ネームサーバーの設定**
   - 「ネームサーバーの設定」または「DNS設定」をクリック
   - 「ネームサーバーを変更する」を選択

4. **Route53のネームサーバーを入力**
   - ネームサーバー1: `ns-1234.awsdns-56.com`
   - ネームサーバー2: `ns-5678.awsdns-12.net`
   - ネームサーバー3: `ns-9012.awsdns-34.org`
   - ネームサーバー4: `ns-3456.awsdns-78.co.uk`
   - （上記は例です。実際の値は`terraform output`で取得してください）

5. **変更を保存**
   - 「設定する」または「保存」をクリック
   - 確認画面で「設定する」をクリック

### ステップ3: ネームサーバーの変更を確認

ネームサーバーの変更は、通常**数時間〜24時間**かかります。

確認方法：

```bash
# ネームサーバーの変更を確認
dig NS mysfa.net +short
```

または、オンラインツールを使用：
- https://mxtoolbox.com/DNSLookup.aspx
- ドメイン名を入力して「DNS Lookup」を実行
- 「NS Records」でRoute53のネームサーバーが表示されればOK

### ステップ4: DNSレコードの自動設定を確認

ネームサーバーの変更が反映されると、Terraformで作成した以下のレコードが自動的に有効になります：

- **DNS検証レコード**（ACM証明書用）
- **Aレコード**（ALBへのエイリアス）
- **www Aレコード**（www.mysfa.net用）

### 注意事項

⚠️ **重要**:
- ネームサーバーの変更が反映されるまで、DNSレコードは機能しません
- 反映までは、お名前.com側のDNS設定が有効です
- 反映後は、Route53側のDNS設定が有効になります

⚠️ **ACM証明書の検証**:
- DNS検証レコードはRoute53に自動で追加されますが、ネームサーバーの変更が反映されるまで検証は完了しません
- ネームサーバーの変更が反映された後、ACM証明書の検証が自動的に開始されます

---

## 📊 コスト見積もり（参考）

- **ECS Fargate**: 約$0.08/時間（1024 CPU, 2GB RAM - web + dbコンテナ）
- **ALB**: 約$0.0225/時間 + データ転送料
- **S3**: ストレージ + リクエスト料
- **Route53**: $0.50/ホストゾーン/月
- **VPC**: 無料（データ転送料のみ）

**RDSとCloudFront削除により大幅なコスト削減とシンプル化**

