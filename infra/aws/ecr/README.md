# ECR Infrastructure — articles-api

This directory contains Terraform configuration for the Amazon ECR repository
and GitHub Actions OIDC IAM role used by the CI/CD pipeline.

## Resources created

| Resource | Name | Description |
|---|---|---|
| ECR repository | `articles-api` | Stores Docker images pushed from GitHub Actions |
| IAM role | `github-actions-ecr-push-role` | Assumed by GitHub Actions via OIDC federation |
| IAM policy (inline) | `ecr-push` | Least-privilege policy allowing push to the ECR repository |

## Prerequisites

- Terraform >= 1.5
- AWS credentials with permissions to create IAM roles, OIDC providers, and ECR repositories
- The GitHub OIDC provider (`arn:aws:iam::<aws-account-id>:oidc-provider/token.actions.githubusercontent.com`)
  is created **once at account level**. If it does not exist, uncomment the
  `aws_iam_openid_connect_provider` resource in `main.tf`.

## Required variables

| Variable | Default | Description |
|---|---|---|
| `aws_region` | `eu-west-2` | AWS region for the ECR repository |
| `github_repo_owner` | — | GitHub organization or user that owns the repo |
| `github_repo_name` | — | GitHub repository name |
| `github_ref` | `refs/heads/master` | Git ref the OIDC role trusts (only pushes from this ref can assume the role) |
| `ecr_repository_name` | `articles-api` | Name of the ECR repository |
| `iam_role_name` | `github-actions-ecr-push-role` | Name of the IAM role for GitHub Actions OIDC |

## Outputs

| Output | Description |
|---|---|
| `ecr_repository_arn` | ARN of the created ECR repository |
| `ecr_repository_url` | Full registry URL of the ECR repository |
| `iam_role_arn` | ARN of the IAM role for GitHub Actions — set this as the `AWS_ROLE_TO_ASSUME` GitHub variable |

## Usage

```bash
cd infra/aws/ecr
terraform init
terraform plan
terraform apply
```

After apply, set the following GitHub repository **variables**:

| Variable | Description |
|---|---|
| `AWS_REGION` | Same value as `aws_region` |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `ECR_REPOSITORY` | Same value as `ecr_repository_name` |
| `AWS_ROLE_TO_ASSUME` | value of `iam_role_arn` output |

## Notes

- Authentication uses GitHub OIDC — no long-lived AWS keys are stored.
- The OIDC trust policy is restricted to the ref defined by `github_ref` (default: `refs/heads/master`).
- This only provisions the ECR repository and push role. App Runner deployment
  and database backend are separate follow-up work.
