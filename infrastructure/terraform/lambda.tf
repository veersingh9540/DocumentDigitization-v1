# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-lambda-execution-role"
    Environment = var.environment
  }
}

# Lambda Basic Execution Policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 Access Policy for Lambda
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${var.project_name}-lambda-s3-access-${var.environment}"
  description = "Allow Lambda functions to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectAcl",
          "s3:PutObjectAcl"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# RDS Access Policy for Lambda
resource "aws_iam_policy" "lambda_rds_access" {
  name        = "${var.project_name}-lambda-rds-access-${var.environment}"
  description = "Allow Lambda functions to access RDS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "rds-db:connect"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_rds_access_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_rds_access.arn
}

# Secrets Manager Access Policy for Lambda
resource "aws_iam_policy" "lambda_secretsmanager_access" {
  name        = "${var.project_name}-lambda-secretsmanager-access-${var.environment}"
  description = "Allow Lambda functions to access secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_secretsmanager_access_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_secretsmanager_access.arn
}

# Textract Access Policy for Lambda
resource "aws_iam_policy" "lambda_textract_access" {
  name        = "${var.project_name}-lambda-textract-access-${var.environment}"
  description = "Allow Lambda functions to use Textract"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_textract_access_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_textract_access.arn
}

# VPC Access Policy for Lambda (if using VPC)
resource "aws_iam_policy" "lambda_vpc_access" {
  name        = "${var.project_name}-lambda-vpc-access-${var.environment}"
  description = "Allow Lambda functions to access VPC resources"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_vpc_access.arn
}

# Create a zip file for the document processor Lambda function
data "archive_file" "document_processor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda/document_processor"
  output_path = "${path.module}/files/document_processor.zip"
}

# Create a zip file for the dashboard API Lambda function
data "archive_file" "dashboard_api_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda/dashboard_api"
  output_path = "${path.module}/files/dashboard_api.zip"
}

# Document Processor Lambda Function
resource "aws_lambda_function" "document_processor" {
  function_name    = "${var.project_name}-document-processor-${var.environment}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.9"
  filename         = data.archive_file.document_processor_zip.output_path
  source_code_hash = data.archive_file.document_processor_zip.output_base64sha256
  memory_size      = 1024
  timeout          = 300  # 5 minutes

  environment {
    variables = {
      OUTPUT_BUCKET  = aws_s3_bucket.documents.bucket
      DB_SECRET_NAME = aws_secretsmanager_secret.db_credentials.name
    }
  }

  tags = {
    Name        = "${var.project_name}-document-processor"
    Environment = var.environment
  }
}

# Dashboard API Lambda Function
resource "aws_lambda_function" "dashboard_api" {
  function_name    = "${var.project_name}-dashboard-api-${var.environment}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.9"
  filename         = data.archive_file.dashboard_api_zip.output_path
  source_code_hash = data.archive_file.dashboard_api_zip.output_base64sha256
  memory_size      = 512
  timeout          = 30

  environment {
    variables = {
      DB_SECRET_NAME = aws_secretsmanager_secret.db_credentials.name
      UPLOAD_BUCKET  = aws_s3_bucket.documents.bucket
    }
  }

  tags = {
    Name        = "${var.project_name}-dashboard-api"
    Environment = var.environment
  }
}

# S3 Event Trigger for Document Processor Lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.document_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ".pdf"
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}

# Permission for S3 to invoke Document Processor Lambda
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.documents.arn
}

# API Gateway for Dashboard API Lambda
resource "aws_apigatewayv2_api" "dashboard_api_gateway" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  tags = {
    Name        = "${var.project_name}-api-gateway"
    Environment = var.environment
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "dashboard_api_stage" {
  api_id      = aws_apigatewayv2_api.dashboard_api_gateway.id
  name        = var.environment
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = {
    Name        = "${var.project_name}-api-stage"
    Environment = var.environment
  }
}

# API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "dashboard_api_integration" {
  api_id           = aws_apigatewayv2_api.dashboard_api_gateway.id
  integration_type = "AWS_PROXY"

  connection_type      = "INTERNET"
  description          = "Lambda integration"
  integration_method   = "POST"
  integration_uri      = aws_lambda_function.dashboard_api.invoke_arn
  passthrough_behavior = "WHEN_NO_MATCH"
}

# API Gateway Routes
resource "aws_apigatewayv2_route" "documents_route" {
  api_id    = aws_apigatewayv2_api.dashboard_api_gateway.id
  route_key = "GET /documents"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api_integration.id}"
}

resource "aws_apigatewayv2_route" "document_route" {
  api_id    = aws_apigatewayv2_api.dashboard_api_gateway.id
  route_key = "GET /documents/{document_id}"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api_integration.id}"
}

resource "aws_apigatewayv2_route" "statistics_route" {
  api_id    = aws_apigatewayv2_api.dashboard_api_gateway.id
  route_key = "GET /statistics"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api_integration.id}"
}

resource "aws_apigatewayv2_route" "upload_url_route" {
  api_id    = aws_apigatewayv2_api.dashboard_api_gateway.id
  route_key = "GET /upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api_integration.id}"
}

# Add Cylinder Inventory route
resource "aws_apigatewayv2_route" "cylinder_inventory_route" {
  api_id    = aws_apigatewayv2_api.dashboard_api_gateway.id
  route_key = "GET /cylinder-inventory"
  target    = "integrations/${aws_apigatewayv2_integration.dashboard_api_integration.id}"
}

# Permission for API Gateway to invoke Dashboard API Lambda
resource "aws_lambda_permission" "api_gateway_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dashboard_api_gateway.execution_arn}/*/*"
}

# S3 bucket CORS configuration for direct uploads
resource "aws_s3_bucket_cors_configuration" "documents_cors" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]  # For production, restrict to your domain
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
