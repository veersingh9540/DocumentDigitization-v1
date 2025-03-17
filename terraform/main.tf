provider "aws" {
  region = var.aws_region
}

# S3 Bucket for Documents
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents-${var.environment}"

  tags = {
    Name        = "${var.project_name}-documents"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# PostgreSQL RDS Instance
resource "aws_db_instance" "postgres" {
  identifier           = "${var.project_name}-postgres-${var.environment}"
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.postgres13"
  skip_final_snapshot  = true
  publicly_accessible  = false

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.environment
  }
}

# EC2 Instance for Dashboard
resource "aws_instance" "dashboard" {
  ami                    = var.ec2_ami
  instance_type          = "t2.micro"
  vpc_security_group_ids = [aws_security_group.dashboard.id]
  key_name               = var.ssh_key_name
  
  user_data = <<-EOF
              #!/bin/bash
              echo "Installing dashboard application"
              # Your installation scripts here
              EOF

  tags = {
    Name        = "${var.project_name}-dashboard"
    Environment = var.environment
  }
}

# EIP for Dashboard EC2
resource "aws_eip" "dashboard" {
  instance = aws_instance.dashboard.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-dashboard-eip"
    Environment = var.environment
  }
}

# Security Group for Dashboard
resource "aws_security_group" "dashboard" {
  name        = "${var.project_name}-dashboard-sg"
  description = "Security group for dashboard EC2 instance"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "pgAdmin access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-dashboard-sg"
    Environment = var.environment
  }
}

# Lambda for Document Processing
resource "aws_lambda_function" "document_processor" {
  function_name = "${var.project_name}-document-processor-${var.environment}"
  handler       = "index.handler"
  runtime       = "nodejs14.x"
  role          = aws_iam_role.lambda_role.arn
  filename      = "${path.module}/lambda/document_processor.zip"
  
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.documents.bucket
      DB_ENDPOINT = aws_db_instance.postgres.endpoint
    }
  }

  tags = {
    Name        = "${var.project_name}-document-processor"
    Environment = var.environment
  }
}

# Lambda for Dashboard API
resource "aws_lambda_function" "dashboard_api" {
  function_name = "${var.project_name}-dashboard-api-${var.environment}"
  handler       = "index.handler"
  runtime       = "nodejs14.x"
  role          = aws_iam_role.lambda_role.arn
  filename      = "${path.module}/lambda/dashboard_api.zip"
  
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.documents.bucket
      DB_ENDPOINT = aws_db_instance.postgres.endpoint
    }
  }

  tags = {
    Name        = "${var.project_name}-dashboard-api"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${var.project_name}-lambda-role"
    Environment = var.environment
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "dashboard_api" {
  name        = "${var.project_name}-api-${var.environment}"
  description = "API Gateway for dashboard"
}

# API Gateway Resource
resource "aws_api_gateway_resource" "dashboard_api" {
  rest_api_id = aws_api_gateway_rest_api.dashboard_api.id
  parent_id   = aws_api_gateway_rest_api.dashboard_api.root_resource_id
  path_part   = "dashboard"
}

# API Gateway Method
resource "aws_api_gateway_method" "dashboard_api" {
  rest_api_id   = aws_api_gateway_rest_api.dashboard_api.id
  resource_id   = aws_api_gateway_resource.dashboard_api.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Integration
resource "aws_api_gateway_integration" "dashboard_api" {
  rest_api_id = aws_api_gateway_rest_api.dashboard_api.id
  resource_id = aws_api_gateway_resource.dashboard_api.id
  http_method = aws_api_gateway_method.dashboard_api.http_method
  
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.dashboard_api.invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "dashboard_api" {
  depends_on = [
    aws_api_gateway_integration.dashboard_api
  ]

  rest_api_id = aws_api_gateway_rest_api.dashboard_api.id
  stage_name  = var.environment

  lifecycle {
    create_before_destroy = true
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard_api.function_name
  principal     = "apigateway.amazonaws.com"
  
  source_arn = "${aws_api_gateway_rest_api.dashboard_api.execution_arn}/*/${aws_api_gateway_method.dashboard_api.http_method}${aws_api_gateway_resource.dashboard_api.path}"
}
