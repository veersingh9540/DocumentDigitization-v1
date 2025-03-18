output "s3_bucket_name" {
  description = "The name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.bucket
}

output "processed_bucket_name" {
  description = "The name of the S3 bucket for processed documents"
  value       = aws_s3_bucket.processed.bucket
}

output "rds_endpoint" {
  description = "The endpoint of the RDS PostgreSQL instance"
  value       = aws_db_instance.postgres.endpoint
}

output "secret_name" {
  description = "The name of the Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.name
}

output "document_processor_lambda" {
  description = "The ARN of the document processor Lambda function"
  value       = aws_lambda_function.document_processor.arn
}

output "dashboard_api_lambda" {
  description = "The ARN of the dashboard API Lambda function"
  value       = aws_lambda_function.dashboard_api.arn
}

output "ec2_instance_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_eip.dashboard.public_ip
}

output "dashboard_url" {
  description = "The URL to access the dashboard"
  value       = "http://${aws_eip.dashboard.public_ip}"
}

output "api_endpoint" {
  description = "The endpoint URL for the API Gateway"
  value       = "${aws_apigatewayv2_stage.dashboard_api.invoke_url}"
}
