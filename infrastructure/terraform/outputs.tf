output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.main.arn
}

output "acm_certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = aws_acm_certificate.main.arn
}

output "application_url_https" {
  description = "HTTPS URL to access the application (via ALB)"
  value       = "https://${var.domain_name}"
}

output "application_url_http" {
  description = "HTTP URL to access the application (redirects to HTTPS via ALB)"
  value       = "http://${var.domain_name}"
}