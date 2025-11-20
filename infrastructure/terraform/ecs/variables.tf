#############################################
# modules/ecs_app/variables.tf
#############################################

variable "project_name" {
  description = "Project name (e.g., mysfa)"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for ECS tasks (usually public subnets for now)"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups for ECS tasks"
  type        = list(string)
}

variable "alb_target_group_arn" {
  description = "ALB target group ARN for this ECS service"
  type        = string
}

variable "task_role_arn" {
  description = "IAM role ARN for ECS task (application role)"
  type        = string
}

variable "execution_role_arn" {
  description = "IAM role ARN for ECS task execution (pull image, logs, etc.)"
  type        = string
}

variable "container_image" {
  description = "Docker image for the app (e.g., ECR URL + tag)"
  type        = string
}

variable "container_port" {
  description = "Container port for the web app (e.g., 80)"
  type        = number
  default     = 80
}

# Fargate の CPU / メモリ（文字列で指定するやつ）
variable "task_cpu" {
  description = "Fargate task CPU (valid Fargate value, e.g., 256, 512, 1024...)"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Fargate task memory (valid Fargate value, e.g., 512, 1024...)"
  type        = string
  default     = "512"
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "aws_region" {
  description = "AWS region (for logs and S3 env var)"
  type        = string
}

# ===== Django 用の環境変数 =====

variable "secret_key" {
  description = "Django SECRET_KEY"
  type        = string
  sensitive   = true
}

variable "debug" {
  description = "Django DEBUG flag"
  type        = bool
  default     = false
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS (comma-separated string)"
  type        = string
}

variable "mysql_host" {
  description = "MySQL host for Django"
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

variable "s3_bucket_name" {
  description = "S3 bucket name for static/media (AWS_STORAGE_BUCKET_NAME)"
  type        = string
}

variable "use_s3" {
  description = "Whether to use S3 in Django (USE_S3 env var)"
  type        = bool
  default     = true
}

# ===== CloudWatch Logs =====

variable "log_group_name" {
  description = "CloudWatch Logs group name for ECS tasks (empty = default)"
  type        = string
  default     = ""
}

variable "log_retention_in_days" {
  description = "Log retention days for CloudWatch Logs group"
  type        = number
  default     = 30
}
