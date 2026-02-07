
output "db_endpoint" {
  description = "RDS endpoint (hostname)"
  value       = aws_db_instance.this.address
}

output "db_port" {
  description = "RDS port"
  value       = aws_db_instance.this.port
}

output "db_identifier" {
  description = "RDS DB instance identifier"
  value       = aws_db_instance.this.id
}

output "security_group_id" {
  description = "Security group ID used by RDS"
  value       = aws_security_group.this.id
}