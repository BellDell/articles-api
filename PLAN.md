# Plan: Step 4 — AWS App Runner + DynamoDB Terraform deployment

## 1. Goal

Provision the AWS infrastructure needed to deploy the application on AWS App Runner with DynamoDB as the history storage backend. This is the runtime deployment for the AWS environment (Kubernetes/ArgoCD remains unchanged).

## 2. Architecture

```
GitHub Actions (CI/CD)
  └── pushes Docker image to ECR
        └── App Runner service pulls image from ECR
              └── App Runner containers run the Flask app
                    └── App Runner uses DynamoDB for history storage
```

- App Runner pulls the container image from the existing ECR repository.
- The app runtime sets `STORAGE_BACKEND=dynamodb`.
- DynamoDB stores Broken Clock calculation history.
- SQLite continues to be used by Kubernetes/ArgoCD deployments.

## 3. In scope

- Add Terraform directory `infra/aws/app-runner/`.
- Create DynamoDB table for Broken Clock history.
- Create IAM roles and policies for App Runner.
- Create App Runner service wired to the ECR image.

## 4. Out of scope

- No app code changes.
- No route or JSON response shape changes.
- No GitHub Actions workflow changes in this step.
- No custom domain or TLS certificate.
- No VPC connector or WAF.
- No authentication.
- No data migration from SQLite.
- No production traffic cutover.

## 5. Terraform resources

| Resource | Purpose |
|---|---|
| `aws_dynamodb_table` | Broken Clock history storage — partition key `app_id` (string), sort key `created_at` (string), billing mode PAY_PER_REQUEST |
| `aws_iam_role.app_runner_access` | Grants App Runner access to pull images from ECR |
| `aws_iam_role.app_runner_instance` | Grants the running App Runner container access to DynamoDB |
| `aws_iam_role_policy_attachment` (managed: `AmazonEC2ContainerRegistryReadOnly`) | Attaches ECR read-only policy to the access role |
| `aws_iam_role_policy.app_runner_instance` (inline) | Least-privilege policy for DynamoDB PutItem, Query, DescribeTable on the table ARN |
| `aws_apprunner_service` | The App Runner service configured with the ECR image, container port 5000, health check `/health`, and environment variables |

Variables: `aws_region`, `aws_account_id`, `ecr_repository_name` (default `articles-api`), `image_tag` (default `latest`), `dynamodb_table_name` (default `articles-api-broken-clock-history`), `app_id` (default `articles-api`).

## 6. IAM / security rules

### App Runner access role (ECR pull)

- Trust policy allows `tasks.apprunner.amazonaws.com` to assume the role.
- Attached managed policy: `AmazonEC2ContainerRegistryReadOnly` — grants `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:BatchCheckLayerAvailability`.

### App Runner instance role (DynamoDB write/query)

- Trust policy allows `tasks.apprunner.amazonaws.com`.
- Inline policy scoped to the specific DynamoDB table ARN:
  - `dynamodb:PutItem`
  - `dynamodb:Query`
  - `dynamodb:DescribeTable`
- No `dynamodb:Scan` on the table (the app uses Query with partition key).
- No `dynamodb:*` on any resource — least privilege.

## 7. App Runner runtime config

| Setting | Value |
|---|---|
| Source | ECR, repository from `ecr_repository_name`, tag from `image_tag` |
| Port | 5000 |
| Health check | `/health` |
| CPU/Memory | 1 vCPU / 2 GB (configurable via variable) |
| Auto-deployment | Enabled on ECR push |
| Environment variables | `STORAGE_BACKEND=dynamodb`, `DYNAMODB_TABLE=<table_name>`, `APP_ID=articles-api`, `AWS_REGION=<region>` |

## 8. Validation strategy

- `terraform fmt` and `terraform validate` on the new directory.
- No real `terraform apply` in this step.
- App code tests (47 existing) remain unchanged.
- After apply, verify App Runner service URL returns `/health` with `{"status": "ok"}`, and `/broken-clock/history` works with DynamoDB backend.

## 9. Follow-up steps

- Add GitHub Actions `deploy` job that runs `terraform apply` on `infra/aws/app-runner/`.
- Add custom domain and TLS.
- Add VPC connector for RDS or other private resources.
- Add WAF for production traffic.
- Add monitoring and alarms.
