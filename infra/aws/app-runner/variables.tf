variable "aws_region" {
  description = "AWS region for App Runner and DynamoDB"
  type        = string
  default     = "eu-west-2"
}

variable "service_name" {
  description = "Name of the App Runner service"
  type        = string
  default     = "articles-api"
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for Broken Clock history"
  type        = string
  default     = "articles-api-broken-clock-history"
}

variable "app_id" {
  description = "Value of the APP_ID environment variable passed to the container"
  type        = string
  default     = "articles-api"
}

variable "ecr_image_identifier" {
  description = "Full ECR image identifier, including tag, e.g. <account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>"
  type        = string
}
