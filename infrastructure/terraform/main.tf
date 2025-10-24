terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
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

# EC2インスタンス（セキュア構成）
resource "aws_instance" "main" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.main.key_name
  vpc_security_group_ids = [aws_security_group.main.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_s3_profile.name

  user_data = templatefile("${path.module}/../config/user_data.sh", {
    dockerhub_username  = var.dockerhub_username
    mysql_host         = var.mysql_host
    mysql_database     = var.mysql_database
    mysql_user         = var.mysql_user
    mysql_password     = var.mysql_password
    mysql_root_password = var.mysql_root_password
    secret_key         = var.secret_key
    allowed_hosts      = var.allowed_hosts
    domain_name        = var.domain_name
  })

  tags = {
    Name = "${var.project_name}-server"
  }
}

# キーペア
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-keypair"
  public_key = file("${path.module}/../keys/mysfa-dev-keypair.pub")
}

# セキュリティグループ（セキュア構成）
resource "aws_security_group" "main" {
  name_prefix = "${var.project_name}-"
  description = "Security group for MySFA application"

  # SSH - 特定IPからのみアクセス許可
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
    description = "SSH access from specific IPs only"
  }

  # HTTP - HTTPSリダイレクト用
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP for HTTPS redirect"
  }

  # HTTPS - Nginxリバースプロキシ経由
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access via Nginx reverse proxy"
  }


  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# Elastic IP
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-eip"
  }
}

# Route 53 Hosted Zone
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# Route 53 A Record
resource "aws_route53_record" "main" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.main.public_ip]
}

# S3バケット（デプロイファイル用）
resource "aws_s3_bucket" "deploy_files" {
  bucket = "${var.project_name}-deploy-files"
  tags = {
    Name = "${var.project_name}-deploy-files"
  }
}

# S3バケットのバージョニング
resource "aws_s3_bucket_versioning" "deploy_files" {
  bucket = aws_s3_bucket.deploy_files.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3バケットのパブリックアクセスブロック
resource "aws_s3_bucket_public_access_block" "deploy_files" {
  bucket = aws_s3_bucket.deploy_files.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ランダム文字列（バケット名の重複回避）
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# IAMロール（EC2用）
resource "aws_iam_role" "ec2_s3_role" {
  name = "${var.project_name}-ec2-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# IAMポリシー（S3アクセス用）
resource "aws_iam_policy" "ec2_s3_policy" {
  name = "${var.project_name}-ec2-s3-policy"

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
        Resource = "${aws_s3_bucket.deploy_files.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.deploy_files.arn
      }
    ]
  })
}

# IAMロールにポリシーをアタッチ
resource "aws_iam_role_policy_attachment" "ec2_s3_policy_attachment" {
  role       = aws_iam_role.ec2_s3_role.name
  policy_arn = aws_iam_policy.ec2_s3_policy.arn
}

# EC2インスタンスプロファイル
resource "aws_iam_instance_profile" "ec2_s3_profile" {
  name = "${var.project_name}-ec2-s3-profile"
  role = aws_iam_role.ec2_s3_role.name
}

