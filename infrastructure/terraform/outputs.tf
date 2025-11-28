# VPC 情報
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

# ALB / Route53
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "application_url_https" {
  description = "HTTPS URL to access the application"
  value       = "https://${var.domain_name}"
}

# S3（static / media）
output "s3_bucket_name" {
  description = "S3 bucket name for static and media files"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for static and media files"
  value       = module.s3.bucket_arn
}

# ECR
output "ecr_repository_url" {
  description = "ECR repository URL for the app"
  value       = module.ecr.repository_url
}

# IAM
output "ecs_task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  value       = module.iam.task_execution_role_arn
}

output "ecs_task_role_arn" {
  description = "ARN of ECS task role"
  value       = module.iam.task_role_arn
}

# ECS
output "ecs_cluster_id" {
  value = module.ecs.cluster_id
}

output "ecs_service_name" {
  value = module.ecs.service_name
}

