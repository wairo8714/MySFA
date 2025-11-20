resource "aws_ecr_repository" "app" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecr"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "app-container-image"
  }
}

# 古いイメージを自動で掃除するライフサイクルポリシー（任意だがあると便利）
resource "aws_ecr_lifecycle_policy" "app" {
  count      = var.lifecycle_policy_enabled ? 1 : 0
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last N images, expire older ones"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = var.lifecycle_keep_last
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
