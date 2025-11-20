variable "project_name" {
  description = "Project name (e.g., mysfa)"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, stg, prod)"
  type        = string
}

variable "repository_name" {
  description = "ECR repository name for the app image"
  type        = string
}

variable "image_tag_mutability" {
  description = "Whether image tags can be overwritten (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Enable image scan on push"
  type        = bool
  default     = true
}

variable "lifecycle_policy_enabled" {
  description = "Whether to enable lifecycle policy to clean up old images"
  type        = bool
  default     = true
}

variable "lifecycle_keep_last" {
  description = "How many image versions to keep if lifecycle policy is enabled"
  type        = number
  default     = 10
}
