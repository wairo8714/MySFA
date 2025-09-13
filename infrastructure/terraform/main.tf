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

