output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.main.public_ip
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.main.id
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.main.id
}

output "application_url_https" {
  description = "HTTPS URL to access the application"
  value       = "https://${var.domain_name}"
}

output "application_url_http" {
  description = "HTTP URL to access the application (redirects to HTTPS)"
  value       = "http://${var.domain_name}"
}

output "application_url_ip" {
  description = "Direct IP access URL (for testing)"
  value       = "https://${aws_instance.main.public_ip}"
}

output "ami_id" {
  description = "AMI ID used for the instance"
  value       = data.aws_ami.amazon_linux.id
}

output "elastic_ip" {
  description = "Elastic IP address"
  value       = aws_eip.main.public_ip
}