output "task_execution_role_arn" {
  description = "IAM role ARN for ECS task execution"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "task_role_arn" {
  description = "IAM role ARN for ECS task"
  value       = aws_iam_role.ecs_task.arn
}
