output "s3_bucket_name" {
  description = "The name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.bucket
}

output "processed_data_bucket_name" {
  description = "The name of the S3 bucket for processed document data"
  value       = aws_s3_bucket.processed_data.bucket
}

output "frontend_bucket_name" {
  description = "The name of the S3 bucket for frontend hosting"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_domain_name" {
  description = "The domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "rds_endpoint" {
  description = "The endpoint of the RDS PostgreSQL instance"
  value       = aws_db_instance.postgres.endpoint
}

output "ec2_instance_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_eip.dashboard.public_ip
}

output "dashboard_url" {
  description = "The URL to access the dashboard"
  value       = "http://${aws_eip.dashboard.public_ip}"
}

output "api_gateway_url" {
  description = "The URL of the API Gateway"
  value       = aws_apigatewayv2_stage.dashboard_api_stage.invoke_url
}

output "document_processor_lambda_arn" {
  description = "The ARN of the document processor Lambda function"
  value       = aws_lambda_function.document_processor.arn
}

output "dashboard_api_lambda_arn" {
  description = "The ARN of the dashboard API Lambda function"
  value       = aws_lambda_function.dashboard_api.arn
}

output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets"
  value       = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
}
