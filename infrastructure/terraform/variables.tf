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
  description = "Application environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

variable "mysql_host" {
  description = "MySQL host"
  type        = string
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

variable "secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS"
  type        = string
  default     = "mysfa.net,www.mysfa.net"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "mysfa.net"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for static and media files"
  type        = string
}
