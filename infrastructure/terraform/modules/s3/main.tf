#############################################
# modules/s3_app/main.tf
#############################################

resource "aws_s3_bucket" "app" {
  bucket = var.bucket_name

  tags = {
    Name        = "${var.project_name}-app-s3"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "static-and-media"
  }
}

# バージョニング有効化（誤削除・上書き対策）
resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id

  versioning_configuration {
    status = "Enabled"
  }
}

# サーバーサイド暗号化（SSE-S3）
resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# パブリックアクセスブロック設定
# → バケットポリシーで許可した範囲だけ公開する前提
resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id

  block_public_acls  = true
  ignore_public_acls = true

  # バケットポリシーは使うので、ここは false にしておく
  block_public_policy     = false
  restrict_public_buckets = false
}

# static / media 用の公開読み取りポリシー
# - /static/* と /media/* のみ GetObject を公開
resource "aws_s3_bucket_policy" "app" {
  bucket = aws_s3_bucket.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowPublicReadForStaticAndMedia"
        Effect    = "Allow"
        Principal = "*"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.app.arn}/static/*",
          "${aws_s3_bucket.app.arn}/media/*"
        ]
      }
    ]
  })
}

# CORS 設定（必要に応じて調整）
resource "aws_s3_bucket_cors_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [
      "https://${var.domain_name}",
      "https://www.${var.domain_name}"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
