provider "aws" {
  region = var.aws_region
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# Reusing when using data, otherwise use resource to create new
resource "aws_iam_role" "iam_for_eratosthenes" {
  name = var.iam_role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.iam_for_eratosthenes.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["logs:*", "lambda:InvokeFunction"],
        Resource = "*"
      }
    ]
  })
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda.js"
  output_path = "lambda_function_src.zip"
}

resource "aws_lambda_function" "lambda" {
  filename      = "lambda_function_src.zip"
  function_name = var.lambda_function_name
  role          = aws_iam_role.iam_for_eratosthenes.arn

  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime = var.lambda_runtime
  handler = var.lambda_handler
}

# Create an API Gateway
resource "aws_api_gateway_rest_api" "api" {
  name        = var.api_name
  description = var.api_description
}

# Create a resource for the API
resource "aws_api_gateway_resource" "resource" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "lambda"
}

# Create a method for the resource
resource "aws_api_gateway_method" "method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resource.id
  http_method   = "POST"
  authorization = "NONE"  # No authorization needed for public access
}

# Integrate the method with the Lambda function
resource "aws_api_gateway_integration" "integration" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resource.id
  http_method             = aws_api_gateway_method.method.http_method
  integration_http_method = "POST"  # Same as your method
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.lambda.invoke_arn
}

# Deploy the API
resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.api_stage_name

  depends_on = [
    aws_api_gateway_method.method,
    aws_api_gateway_integration.integration
  ]
}

# Allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# Output the API endpoint
output "api_endpoint" {
  value = "${aws_api_gateway_deployment.deployment.invoke_url}/${aws_api_gateway_resource.resource.path_part}"
}
