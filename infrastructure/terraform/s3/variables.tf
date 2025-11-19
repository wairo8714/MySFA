variable "project_name" {
  description = "Project name (e.g. mysfa)"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. prod, staging)"
  type        = string
}

# アプリ用 (static / media) バケット名
variable "app_bucket_name" {
  description = "S3 bucket name for application static/media files"
  type        = string
}

# tfstate 用バケットをこのモジュールで管理するかどうか
variable "create_state_bucket" {
  description = "Whether to manage a Terraform state bucket from this module"
  type        = bool
  default     = false
}

# tfstate 用バケット名（省略時は ${project_name}-terraform-state）
variable "state_bucket_name" {
  description = "S3 bucket name for Terraform remote state (optional)"
  type        = string
  default     = null
}

# app バケットを destroy するとき、中身ごと消せるようにするか
variable "app_bucket_force_destroy" {
  description = "Allow destroying the app bucket even if it contains objects"
  type        = bool
  default     = true
}

# state バケットは基本削除したくないので別フラグ
variable "state_bucket_force_destroy" {
  description = "Allow destroying the state bucket even if it contains objects (not recommended in production)"
  type        = bool
  default     = false
}