output "s3_bucket_name" {
  description = "The name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.bucket
}

output "rds_endpoint" {
  description = "The endpoint of the RDS PostgreSQL instance"
  value       = aws_db_instance.postgres.endpoint
}

output "api_gateway_url" {
  description = "The URL of the API Gateway deployment"
  value       = aws_api_gateway_deployment.dashboard_api.invoke_url
}

output "ec2_instance_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_eip.dashboard.public_ip
}

output "dashboard_url" {
  description = "The URL to access the dashboard"
  value       = "http://${aws_eip.dashboard.public_ip}"
}

output "pgadmin_url" {
  description = "The URL to access pgAdmin"
  value       = "http://${aws_eip.dashboard.public_ip}:8080"
}

output "lambda_document_processor_name" {
  description = "The name of the document processor Lambda function"
  value       = aws_lambda_function.document_processor.function_name
}

output "lambda_dashboard_api_name" {
  description = "The name of the dashboard API Lambda function"
  value       = aws_lambda_function.dashboard_api.function_name
}
