output "app_runner_service_url" {
  description = "URL of the App Runner service"
  value       = aws_apprunner_service.this.service_url
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.this.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.this.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.this.arn
}

output "app_runner_access_role_arn" {
  description = "ARN of the App Runner access role (ECR pull)"
  value       = aws_iam_role.app_runner_access.arn
}

output "app_runner_instance_role_arn" {
  description = "ARN of the App Runner instance role (DynamoDB access)"
  value       = aws_iam_role.app_runner_instance.arn
}
