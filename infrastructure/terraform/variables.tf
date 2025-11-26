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

# ドメイン
variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS (comma-separated string)"
  type        = string
}

# VPC 設定
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

# S3（static / media 用）
variable "s3_bucket_name" {
  description = "S3 bucket name for static and media files"
  type        = string
}

# ====== 以下は ECS / アプリ側で使う想定の変数（既存設定を踏襲） ======

# Django
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

# MySQL / RDS

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
