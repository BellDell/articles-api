variable "aws_region" {
  description = "AWS region for the ECR repository"
  type        = string
  default     = "eu-west-2"
}

variable "github_repo_owner" {
  description = "GitHub organization or user that owns the repository"
  type        = string
}

variable "github_repo_name" {
  description = "GitHub repository name"
  type        = string
}

variable "github_ref" {
  description = "Git ref that the OIDC role trusts (e.g. refs/heads/master)"
  type        = string
  default     = "refs/heads/master"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "articles-api"
}

variable "iam_role_name" {
  description = "Name of the IAM role for GitHub Actions OIDC"
  type        = string
  default     = "github-actions-ecr-push-role"
}
