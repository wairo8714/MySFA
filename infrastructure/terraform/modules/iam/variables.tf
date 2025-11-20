variable "project_name" {
  description = "Project name (e.g., mysfa)"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "app_bucket_arn" {
  description = "ARN of the S3 bucket for static/media files"
  type        = string
}

variable "app_bucket_name" {
  description = "Name of the S3 bucket for static/media files"
  type        = string
}

variable "cloudwatch_log_group_name" {
  description = "CloudWatch Logs group name for ECS task logs"
  type        = string
  default     = ""
}
