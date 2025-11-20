# VPC 情報
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
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
output "s3_app_bucket_name" {
  description = "S3 bucket name for static and media files"
  value       = module.s3_app.bucket_name
}

output "s3_app_bucket_arn" {
  description = "S3 bucket ARN for static and media files"
  value       = module.s3_app.bucket_arn
}

# ECR
output "ecr_app_repository_url" {
  description = "ECR repository URL for the app"
  value       = module.ecr_app.repository_url
}

