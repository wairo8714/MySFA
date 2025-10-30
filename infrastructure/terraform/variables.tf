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

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "dockerhub_username" {
  description = "Docker Hub username for image pulling"
  type        = string
}

variable "mysql_host" {
  description = "MySQL host"
  type        = string
}

variable "mysql_database" {
  description = "MySQL database name"
  type        = string
  default     = "mysfa_db"
}

variable "mysql_user" {
  description = "MySQL user"
  type        = string
  default     = "admin"
}

variable "mysql_password" {
  description = "MySQL password"
  type        = string
  sensitive   = true
}

variable "mysql_root_password" {
  description = "MySQL root password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS setting"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}
