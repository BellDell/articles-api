# App Runner + DynamoDB — articles-api

This directory contains Terraform configuration for deploying the application
on AWS App Runner with DynamoDB as the Broken Clock history storage backend.

## Resources created

| Resource | Name | Description |
|---|---|---|
| DynamoDB table | configurable, default `articles-api-broken-clock-history` | Partition key `app_id` (String), sort key `created_at` (String), PAY_PER_REQUEST billing |
| IAM role | `<service-name>-app-runner-access` | Trusted by `build.apprunner.amazonaws.com` for ECR image pull |
| IAM role | `<service-name>-app-runner-instance` | Trusted by `tasks.apprunner.amazonaws.com`, allows DynamoDB PutItem/Query/DescribeTable |
| App Runner service | configurable, default `articles-api` | Runs the Flask container with DynamoDB backend |

## Prerequisites

- Terraform >= 1.5
- AWS credentials with permissions to create DynamoDB tables, IAM roles, and App Runner services
- ECR repository and image already published (see `infra/aws/ecr/`)
- State backend (S3, DynamoDB, or local) — do not commit state files

## Required variables

| Variable | Example | Description |
|---|---|---|
| `ecr_image_identifier` | `<account-id>.dkr.ecr.<region>.amazonaws.com/articles-api:latest` | Full ECR image identifier |

### Variables with defaults

| Variable | Default | Description |
|---|---|---|
| `aws_region` | `eu-west-2` | AWS region |
| `service_name` | `articles-api` | Name of the App Runner service |
| `dynamodb_table_name` | `articles-api-broken-clock-history` | DynamoDB table name |
| `app_id` | `articles-api` | Value of the `APP_ID` env var |

## Outputs

| Output | Description |
|---|---|
| `app_runner_service_url` | URL of the App Runner service |
| `app_runner_service_arn` | ARN of the App Runner service |
| `dynamodb_table_name` | Name of the DynamoDB table |
| `dynamodb_table_arn` | ARN of the DynamoDB table |
| `app_runner_access_role_arn` | ARN of the ECR access role |
| `app_runner_instance_role_arn` | ARN of the instance role |

## Usage

```bash
cd infra/aws/app-runner
terraform init
terraform plan
terraform apply
```

## Notes

- The container must have `STORAGE_BACKEND=dynamodb` set at runtime (injected via environment variables).
- This does not configure a custom domain, VPC connector, WAF, or data migration from SQLite.
- Terraform state must not be committed to the repository (use S3 or similar backend).
