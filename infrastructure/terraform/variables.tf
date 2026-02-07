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

variable "domain_name" {
  description = "Primary domain name for the application"
  type        = string
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS (comma-separated string)"
  type        = string
}

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

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "s3_bucket_name" {
  description = "S3 bucket name for static and media files"
  type        = string
}


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
