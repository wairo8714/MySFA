#############################################
# modules/ecs_app/main.tf
#############################################

locals {
  # Django 用 bool → 文字列変換
  debug_string  = var.debug ? "True" : "False"
  use_s3_string = var.use_s3 ? "True" : "False"

  # ロググループ名（指定が空ならデフォルト）
  log_group_name = var.log_group_name != "" ?
    var.log_group_name :
    "/ecs/${var.project_name}-${var.environment}"

  # web コンテナに渡す環境変数（Django 用）
  container_environment_web = [
    {
      name  = "SECRET_KEY"
      value = var.secret_key
    },
    {
      name  = "DEBUG"
      value = local.debug_string
    },
    {
      name  = "ALLOWED_HOSTS"
      value = var.allowed_hosts
    },
    {
      name  = "MYSQL_HOST"
      value = var.mysql_host
    },
    {
      name  = "MYSQL_PORT"
      value = tostring(var.mysql_port)
    },
    {
      name  = "MYSQL_DATABASE"
      value = var.mysql_database
    },
    {
      name  = "MYSQL_USER"
      value = var.mysql_user
    },
    {
      name  = "MYSQL_PASSWORD"
      value = var.mysql_password
    },
    {
      name  = "AWS_STORAGE_BUCKET_NAME"
      value = var.s3_bucket_name
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "USE_S3"
      value = local.use_s3_string
    },
  ]

  # mysql コンテナに渡す環境変数（公式 mysql イメージ想定）
  container_environment_mysql = [
    {
      name  = "MYSQL_DATABASE"
      value = var.mysql_database
    },
    {
      name  = "MYSQL_USER"
      value = var.mysql_user
    },
    {
      name  = "MYSQL_PASSWORD"
      value = var.mysql_password
    },
    {
      name  = "MYSQL_ROOT_PASSWORD"
      value = var.mysql_root_password
    }
  ]
}

# ============================================
# ECS クラスタ
# ============================================
resource "aws_ecs_cluster" "app" {
  name = var.cluster_name

  tags = {
    Name        = var.cluster_name
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================
# CloudWatch Logs グループ
# ============================================
resource "aws_cloudwatch_log_group" "app" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_in_days

  tags = {
    Name        = local.log_group_name
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================
# ECS タスク定義（web + mysql 同居）
# ============================================
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-${var.environment}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  # MySQL データ用のエフェメラルボリューム
  volume {
    name = "mysql_data"
    # Fargate では host / efsVolumeConfiguration を指定しないと
    # タスクのエフェメラルストレージが使われる
  }

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = local.container_environment_web

      # MySQL コンテナが START するまで待ってから起動
      dependsOn = [
        {
          containerName = "mysql"
          condition     = "START"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    },
    {
      name      = "mysql"
      image     = var.mysql_image
      essential = true

      portMappings = [
        {
          containerPort = var.mysql_port
          protocol      = "tcp"
        }
      ]

      environment = local.container_environment_mysql

      # MySQL データディレクトリにボリュームをマウント
      mountPoints = [
        {
          sourceVolume  = "mysql_data"
          containerPath = "/var/lib/mysql"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "mysql"
        }
      }

      # 必要に応じて healthCheck を追加することも可能
      # healthCheck = {
      #   command     = ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -P 3306 || exit 1"]
      #   interval    = 30
      #   timeout     = 5
      #   retries     = 3
      #   startPeriod = 60
      # }
    }
  ])

  tags = {
    Name        = "${var.project_name}-${var.environment}-taskdef"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================
# ECS サービス
# ============================================
resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-${var.environment}-service"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = true  # 今はパブリックサブネット運用
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "web"
    container_port   = var.container_port
  }

  enable_execute_command = true

  lifecycle {
    # 手動で desired_count だけ変える運用を許容する
    ignore_changes = [desired_count]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-service"
    Project     = var.project_name
    Environment = var.environment
  }
}
