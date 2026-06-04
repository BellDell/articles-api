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
# DynamoDB table
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "this" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "app_id"
  range_key    = "created_at"

  attribute {
    name = "app_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  tags = {
    Name        = var.dynamodb_table_name
    ManagedBy   = "terraform"
    Environment = "production"
  }
}

# ---------------------------------------------------------------------------
# App Runner access role (ECR image pull)
# ---------------------------------------------------------------------------

data "aws_iam_policy" "ecr_access" {
  name = "AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "app_runner_access" {
  name = "${var.service_name}-app-runner-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name      = "${var.service_name}-app-runner-access"
    ManagedBy = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "ecr_access" {
  role       = aws_iam_role.app_runner_access.name
  policy_arn = data.aws_iam_policy.ecr_access.arn
}

# ---------------------------------------------------------------------------
# App Runner instance role (DynamoDB access)
# ---------------------------------------------------------------------------

resource "aws_iam_role" "app_runner_instance" {
  name = "${var.service_name}-app-runner-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name      = "${var.service_name}-app-runner-instance"
    ManagedBy = "terraform"
  }
}

resource "aws_iam_role_policy" "app_runner_instance" {
  name = "dynamodb-access"
  role = aws_iam_role.app_runner_instance.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:DescribeTable",
        ]
        Resource = [aws_dynamodb_table.this.arn]
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# App Runner service
# ---------------------------------------------------------------------------

resource "aws_apprunner_service" "this" {
  service_name = var.service_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_access.arn
    }

    image_repository {
      image_configuration {
        port = "5000"

        runtime_environment_variables = {
          STORAGE_BACKEND = "dynamodb"
          DYNAMODB_TABLE  = var.dynamodb_table_name
          APP_ID          = var.app_id
          AWS_REGION      = var.aws_region
        }
      }

      image_identifier      = var.ecr_image_identifier
      image_repository_type = "ECR"
    }

    auto_deployments_enabled = true
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/health"
  }

  instance_configuration {
    cpu               = "1024"
    memory            = "2048"
    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  tags = {
    Name        = var.service_name
    ManagedBy   = "terraform"
    Environment = "production"
  }
}
