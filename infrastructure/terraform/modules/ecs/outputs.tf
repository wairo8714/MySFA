# modules/ecs_app/outputs.tf

output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.app.id
}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "ECS task definition ARN"
  value       = aws_ecs_task_definition.app.arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch Logs group name used by ECS tasks"
  value       = aws_cloudwatch_log_group.app.name
}
