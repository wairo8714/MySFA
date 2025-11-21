#############################################
# modules/s3_app/variables.tf
#############################################

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "bucket_name" {
  description = "S3 bucket name for static and media files"
  type        = string
}

variable "domain_name" {
  description = "Primary domain name (used for CORS)"
  type        = string
}
