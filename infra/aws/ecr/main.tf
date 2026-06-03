terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# ECR repository
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "this" {
  name = var.ecr_repository_name

  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = var.ecr_repository_name
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# ---------------------------------------------------------------------------
# GitHub OIDC provider
#
# This resource is account-level and should be created only once.
# If an OIDC provider for token.actions.githubusercontent.com already
# exists in the account, comment out the data source block below and
# use the existing one. If it does not exist, uncomment the resource
# block instead.
# ---------------------------------------------------------------------------

# resource "aws_iam_openid_connect_provider" "github" {
#   url            = "https://token.actions.githubusercontent.com"
#   client_id_list = ["sts.amazonaws.com"]
#   thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
# }

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# ---------------------------------------------------------------------------
# IAM role for GitHub Actions
# ---------------------------------------------------------------------------

resource "aws_iam_role" "github_actions" {
  name = var.iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo_owner}/${var.github_repo_name}:ref:${var.github_ref}"
          }
        }
      }
    ]
  })

  tags = {
    Name      = var.iam_role_name
    ManagedBy = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Least-privilege ECR push policy
# ---------------------------------------------------------------------------

resource "aws_iam_role_policy" "ecr_push" {
  name = "ecr-push"
  role = aws_iam_role.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = [aws_ecr_repository.this.arn]
      }
    ]
  })
}
