# Define the AWS region
variable "aws_region" {
  description = "The AWS region to deploy resources to"
  type        = string
  default     = "eu-central-1"  # Default value
}

# IAM role name
variable "iam_role_name" {
  description = "Name of the IAM role for Lambda function"
  type        = string
  default     = "sieve_simulation_role"
}

# Lambda function details
variable "lambda_function_name" {
  description = "The name of the Lambda function"
  type        = string
  default     = "sieve_simulation_lambda"
}

variable "lambda_runtime" {
  description = "The runtime environment for the Lambda function"
  type        = string
  default     = "nodejs20.x"
}

variable "lambda_handler" {
  description = "The handler function in the Lambda code"
  type        = string
  default     = "lambda.handler"
}

# API Gateway
variable "api_name" {
  description = "Name of the API Gateway"
  type        = string
  default     = "sieve_simulation_api"
}

variable "api_description" {
  description = "Description of the API Gateway"
  type        = string
  default     = "API for Lambda Function used to test Sieve of Eratosthenes simulations"
}

variable "api_stage_name" {
  description = "Stage name for the API Gateway deployment"
  type        = string
  default     = "dev"
}

variable "memory_size" {
  description = "Memory Size for Function"
  type = number
  default = 512
}