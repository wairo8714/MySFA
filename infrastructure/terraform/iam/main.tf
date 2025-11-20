locals {
  ecs_task_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# ============================================
# 1. ECS タスク実行ロール（execution role）
#    - ECR からの pull, CloudWatch Logs など
# ============================================
resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-${var.environment}-ecs-task-execution-role"
  assume_role_policy = local.ecs_task_assume_role_policy

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-task-execution-role"
    Project     = var.project_name
    Environment = var.environment
  }
}

# AWS 管理ポリシーをアタッチ（ECR pull, CloudWatch Logs 等が含まれている）
resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# （必要ならここに追加のポリシーを足すことも可能）
# 例: SSM Parameter Store から環境変数を読む等


# ============================================
# 2. ECS タスクロール（task role）
#    - アプリケーションが使う権限（S3 など）
# ============================================
resource "aws_iam_role" "ecs_task" {
  name               = "${var.project_name}-${var.environment}-ecs-task-role"
  assume_role_policy = local.ecs_task_assume_role_policy

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-task-role"
    Project     = var.project_name
    Environment = var.environment
  }
}

# S3 (static/media バケット) へのアクセス権限
data "aws_iam_policy_document" "ecs_task_s3_policy" {
  statement {
    sid    = "AllowAccessToAppBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      var.app_bucket_arn
    ]
  }

  statement {
    sid    = "AllowObjectOperationsOnAppBucket"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${var.app_bucket_arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name   = "${var.project_name}-${var.environment}-ecs-task-s3-policy"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_s3_policy.json
}

# （必要なら CloudWatch Logs などの追加権限もここに付けられる）
# ただし通常はログ出力は execution role 側が担当するのでここでは省略
