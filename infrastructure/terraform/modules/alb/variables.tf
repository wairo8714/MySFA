# modules/alb/variables.tf

variable "project_name" {
  description = "Project name prefix for tagging and naming"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application (e.g., mysfa.net)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ALB and target group will be created"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID to attach to the ALB"
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for creating DNS records"
  type        = string
}

variable "health_check_path" {
  description = "Health check path for the target group"
  type        = string
  default     = "/health/"
}
