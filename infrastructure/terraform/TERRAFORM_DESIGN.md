# Terraform 設計案 - 大幅刷新版

## 📋 概要

このドキュメントは、以下の構成でTerraformを大幅に刷新する設計案です。

### 対象リソース

1. **IAM** (mysfa-terraform) - Terraform実行用IAMユーザー
2. **ALB** - Application Load Balancer
3. **Route53** (mysfa.net) - DNS管理
4. **ECS: Fargate** (Nginx/gunicorn/django) - コンテナ実行環境
5. **S3** - static/imagesとmedia保存用、terraform.tfstate用
6. **CloudFront** - 静的ファイル配信の高速化
7. **RDS (MySQL)** - データベース
8. **CloudWatch** - ログとモニタリング
9. **CloudShell** - AWSマネージドサービス（Terraform管理外）

---

## 🏗️ アーキテクチャ概要

```
Internet
    ↓
Route53 (mysfa.net)
    ↓
CloudFront Distribution (静的ファイル用)
    ↓
    ├─ S3 Bucket (static/media)
    └─ ALB (アプリケーション用)
        ↓
    ACM Certificate (SSL/TLS)
        ↓
    ALB Listener (HTTPS:443)
        ↓
    Target Group
        ↓
    ECS Service (Fargate)
        ↓
    ECS Task Definition
        ├─ Container: Nginx + Gunicorn + Django
        ├─ IAM Task Execution Role (ECR, CloudWatch Logs)
        ├─ IAM Task Role (S3, RDS)
        └─ Security Group
            ↓
    RDS MySQL (データベース)
```

---

## 📁 ファイル構成

```
infrastructure/terraform/
├── main.tf                    # メインリソース定義
├── variables.tf               # 変数定義
├── outputs.tf                 # 出力定義
├── terraform.tfvars            # 変数値（gitignore推奨）
├── backend.tf                 # バックエンド設定（分離推奨）
├── iam.tf                     # IAMリソース（分離推奨）
├── network.tf                 # ネットワーク・セキュリティ（分離推奨）
├── compute.tf                 # ECS関連（分離推奨）
├── storage.tf                 # S3, ECR関連（分離推奨）
├── database.tf                # RDS関連（分離推奨）
├── cdn.tf                     # CloudFront関連（分離推奨）
└── monitoring.tf              # CloudWatch関連（分離推奨）
```

---

## 🔧 リソース詳細設計

### 1. IAM (mysfa-terraform)

**目的**: Terraform実行用のIAMユーザー

```hcl
# iam.tf

# Terraform実行用IAMユーザー
resource "aws_iam_user" "terraform" {
  name = "mysfa-terraform"
  path = "/"

  tags = {
    Name        = "mysfa-terraform"
    Environment = var.environment
    Purpose     = "Terraform execution"
  }
}

# アクセスキー（初回のみ手動作成、その後はTerraformで管理）
resource "aws_iam_access_key" "terraform" {
  user = aws_iam_user.terraform.name
}

# Terraform実行用ポリシー（必要な権限のみ）
resource "aws_iam_user_policy" "terraform" {
  name = "mysfa-terraform-policy"
  user = aws_iam_user.terraform.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:*",
          "ecs:*",
          "ecr:*",
          "s3:*",
          "rds:*",
          "iam:*",
          "route53:*",
          "acm:*",
          "cloudfront:*",
          "cloudwatch:*",
          "logs:*",
          "elasticloadbalancing:*",
          "application-autoscaling:*"
        ]
        Resource = "*"
      }
    ]
  })
}
```

**注意事項**:
- 初回作成時は、ルートアカウントまたは既存のIAMユーザーで実行
- アクセスキーは機密情報のため、`terraform.tfvars`には含めない
- 必要に応じて、より細かい権限に制限

---

### 2. S3 バケット

**目的**: 
- 静的ファイル・メディアファイル保存用
- Terraform状態ファイル保存用

```hcl
# storage.tf

# ============================================
# S3: アプリケーション用（static/media）
# ============================================
resource "aws_s3_bucket" "app" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "${var.project_name}-app-storage"
    Environment = var.environment
    Purpose     = "Static and media files"
  }
}

# バージョニング
resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id

  versioning_configuration {
    status = "Enabled"
  }
}

# パブリックアクセスブロック（CloudFront経由でアクセス）
resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets  = true
}

# バケットポリシー（CloudFrontからのアクセスのみ許可）
resource "aws_s3_bucket_policy" "app" {
  bucket = aws_s3_bucket.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.app.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.app.arn}/*"
      },
      {
        Sid    = "AllowECSWriteAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task.arn
        }
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.app.arn}/*"
      }
    ]
  })
}

# CORS設定
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

# ライフサイクルポリシー（オプション）
resource "aws_s3_bucket_lifecycle_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "delete_incomplete_multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================
# S3: Terraform状態ファイル用
# ============================================
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-terraform-state"

  tags = {
    Name        = "${var.project_name}-terraform-state"
    Environment = var.environment
    Purpose     = "Terraform state storage"
  }
}

# バージョニング（必須）
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 暗号化
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# パブリックアクセスブロック
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDBテーブル（状態ファイルのロック用）
resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "${var.project_name}-terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-terraform-state-lock"
    Environment = var.environment
  }
}
```

---

### 3. CloudFront

**目的**: 静的ファイル・メディアファイルの高速配信

```hcl
# cdn.tf

# Origin Access Identity（OAI）
resource "aws_cloudfront_origin_access_identity" "app" {
  comment = "OAI for ${var.project_name} S3 bucket"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "app" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.project_name}"
  default_root_object = "index.html"

  # S3 Origin
  origin {
    domain_name = aws_s3_bucket.app.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.app.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.app.cloudfront_access_identity_path
    }
  }

  # カスタムドメイン（オプション）
  aliases = [
    var.domain_name,
    "www.${var.domain_name}"
  ]

  # SSL証明書（ACM）
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.main.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # デフォルトキャッシュビヘイビア
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.app.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # 静的ファイル用キャッシュビヘイビア
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.app.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 86400
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }

  # メディアファイル用キャッシュビヘイビア
  ordered_cache_behavior {
    path_pattern     = "/media/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.app.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 3600
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # カスタムエラーレスポンス
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name        = "${var.project_name}-cloudfront"
    Environment = var.environment
  }
}

# Route53レコード（CloudFront用）
resource "aws_route53_record" "cloudfront" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "cdn.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.app.domain_name
    zone_id                = aws_cloudfront_distribution.app.hosted_zone_id
    evaluate_target_health = false
  }
}
```

**注意事項**:
- CloudFrontの証明書は`us-east-1`リージョンで作成する必要がある
- デプロイには15-20分かかる場合がある

---

### 4. RDS (MySQL)

**目的**: データベース

```hcl
# database.tf

# DBサブネットグループ
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = data.aws_subnets.private.ids

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# セキュリティグループ（RDS用）
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for RDS MySQL"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MySQL from ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# RDSインスタンス
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  engine         = "mysql"
  engine_version = "8.0"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage  = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.mysql_database
  username = var.mysql_user
  password = var.mysql_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  backup_retention_period = var.rds_backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  skip_final_snapshot       = var.rds_skip_final_snapshot
  final_snapshot_identifier = "${var.project_name}-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  enabled_cloudwatch_logs_exports = ["error", "general", "slow_query"]

  performance_insights_enabled = var.rds_performance_insights_enabled

  tags = {
    Name        = "${var.project_name}-db"
    Environment = var.environment
  }
}
```

---

### 5. ECS (Fargate)

**目的**: コンテナ実行環境（Nginx + Gunicorn + Django）

```hcl
# compute.tf

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

# ============================================
# IAM ロール
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

# タスクロール（アプリケーション用：S3、RDSへのアクセス）
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
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.app.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.app.arn
      }
    ]
  })
}

# ============================================
# セキュリティグループ
# ============================================
# ECSタスク用
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = data.aws_vpc.default.id

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
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

# ALB用
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = data.aws_vpc.default.id

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

# ============================================
# ECS クラスター
# ============================================
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

# ============================================
# ECS タスク定義
# ============================================
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
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
        { name = "DEBUG", value = var.debug },
        { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
        { name = "MYSQL_DATABASE", value = var.mysql_database },
        { name = "MYSQL_USER", value = var.mysql_user },
        { name = "MYSQL_PASSWORD", value = var.mysql_password },
        { name = "MYSQL_HOST", value = aws_db_instance.main.endpoint },
        { name = "MYSQL_PORT", value = "3306" },
        { name = "S3_BUCKET_NAME", value = aws_s3_bucket.app.id },
        { name = "AWS_STORAGE_BUCKET_NAME", value = aws_s3_bucket.app.id },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "FORCE_HTTPS", value = "true" },
        { name = "DOMAIN_NAME", value = var.domain_name },
        { name = "USE_S3", value = "true" },
        { name = "CLOUDFRONT_DOMAIN", value = aws_cloudfront_distribution.app.domain_name }
      ]

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
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-task"
  }
}

# ============================================
# ECS サービス
# ============================================
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
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
    aws_lb_listener.https,
    aws_db_instance.main
  ]

  tags = {
    Name = "${var.project_name}-service"
  }
}
```

---

### 6. ALB & Route53

**目的**: ロードバランシングとDNS管理

```hcl
# network.tf (既存のALB設定を更新)

# 既存のALB設定を維持しつつ、セキュリティグループをTerraform管理に変更
# （既存のdata sourceをresourceに変更）

# Route53レコード（ALB用）
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
```

---

### 7. CloudWatch

**目的**: ログとモニタリング

```hcl
# monitoring.tf

# アラーム（ECS CPU使用率）
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project_name}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [] # SNSトピックなどを追加可能

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.main.name
  }

  tags = {
    Name = "${var.project_name}-ecs-cpu-alarm"
  }
}

# アラーム（RDS CPU使用率）
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "${var.project_name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-rds-cpu-alarm"
  }
}
```

---

## 📝 変数定義（追加・更新）

```hcl
# variables.tf

# 既存の変数に加えて以下を追加

variable "ecr_repository_name" {
  description = "ECR repository name"
  type        = string
  default     = "mysfa_ver2"
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units (256, 512, 1024, etc.)"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 7
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "RDS max allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot when destroying RDS"
  type        = bool
  default     = false
}

variable "rds_performance_insights_enabled" {
  description = "Enable RDS Performance Insights"
  type        = bool
  default     = false
}

variable "debug" {
  description = "Django DEBUG mode"
  type        = bool
  default     = false
}
```

---

## 📤 出力定義（追加・更新）

```hcl
# outputs.tf

# 既存の出力に加えて以下を追加

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

output "s3_bucket_terraform_state" {
  description = "S3 bucket name for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
  sensitive   = false
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.app.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.app.domain_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_address" {
  description = "RDS instance address"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "iam_user_terraform_name" {
  description = "Terraform IAM user name"
  value       = aws_iam_user.terraform.name
}

output "iam_user_terraform_access_key_id" {
  description = "Terraform IAM user access key ID"
  value       = aws_iam_access_key.terraform.id
  sensitive   = true
}
```

---

## 🔄 移行手順

### ステップ1: バックアップ

```bash
# 現在のTerraform状態をバックアップ
cd infrastructure/terraform
terraform state pull > terraform.tfstate.backup
```

### ステップ2: 既存リソースのインポート

既存のリソースがある場合、Terraformにインポート：

```bash
# 例: 既存のセキュリティグループをインポート
terraform import aws_security_group.ecs_tasks sg-xxxxxxxxx
```

### ステップ3: 段階的な適用

1. **S3バケット（Terraform状態用）を先に作成**
   - バックエンド設定を更新
   - `terraform init -migrate-state`

2. **ネットワークリソース（VPC、セキュリティグループ）**
3. **ストレージリソース（S3、ECR）**
4. **データベース（RDS）**
5. **コンピューティング（ECS）**
6. **CDN（CloudFront）**
7. **IAM（最後に作成）**

---

## ⚠️ 注意事項

1. **CloudFrontの証明書**: `us-east-1`リージョンで作成する必要がある
2. **RDSのパスワード**: 機密情報のため、`terraform.tfvars`はgitignoreに追加
3. **IAMアクセスキー**: 初回作成後は手動で取得が必要
4. **既存リソース**: 既存のリソースがある場合は、インポートまたは手動削除が必要
5. **CloudShell**: AWSマネージドサービスのため、Terraformで管理しない

---

## 🔗 GitHub Actionsとの連携

deploy.ymlで使用する値は、Terraformのoutputsから取得：

```yaml
# GitHub Actions Secrets に設定する値
ECR_REPOSITORY: mysfa_ver2  # terraform output ecr_repository_url から取得
S3_BUCKET_NAME: mysfa-deploy-files  # terraform output s3_bucket_name から取得
MYSQL_HOST: <terraform output rds_endpoint>  # terraform output rds_endpoint から取得
```

---

## 📊 コスト見積もり（参考）

- **ECS Fargate**: 約$0.04/時間（512 CPU, 1GB RAM）
- **ALB**: 約$0.0225/時間 + データ転送料
- **RDS t3.micro**: 約$0.017/時間
- **S3**: ストレージ + リクエスト料
- **CloudFront**: データ転送料（最初の1TBは無料）
- **Route53**: $0.50/ホストゾーン/月

---

## 🎯 次のステップ

1. この設計案をレビュー
2. 段階的に実装（S3 → ネットワーク → データベース → コンピューティング → CDN）
3. GitHub Actionsとの連携を確認
4. テスト環境で検証

