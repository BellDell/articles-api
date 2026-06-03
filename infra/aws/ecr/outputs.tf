output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.this.arn
}

output "ecr_repository_url" {
  description = "Full registry URL of the ECR repository"
  value       = aws_ecr_repository.this.repository_url
}

output "iam_role_arn" {
  description = "ARN of the IAM role for GitHub Actions — set as the AWS_ROLE_TO_ASSUME GitHub variable"
  value       = aws_iam_role.github_actions.arn
}
