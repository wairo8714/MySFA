
variable "project_name" {
  description = "Project name (e.g., mysfa)"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where RDS will be placed"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for RDS subnet group (2+ subnets in different AZs recommended)"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to connect to this RDS instance (e.g., ECS tasks SG)"
  type        = list(string)
}

variable "db_name" {
  description = "Initial database name"
  type        = string
}

variable "username" {
  description = "Master username for RDS MySQL"
  type        = string
}

variable "password" {
  description = "Master password for RDS MySQL"
  type        = string
  sensitive   = true
}

variable "engine_version" {
  description = "MySQL engine version"
  type        = string
  default     = "8.0"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "multi_az" {
  description = "Whether to enable Multi-AZ"
  type        = bool
  default     = false
}

variable "publicly_accessible" {
  description = "Whether the DB instance is publicly accessible"
  type        = bool
  default     = false
}

variable "port" {
  description = "Database port"
  type        = number
  default     = 3306
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection"
  type        = bool
  default     = false
}

variable "apply_immediately" {
  description = "Whether modifications are applied immediately or during the next maintenance window"
  type        = bool
  default     = true
}