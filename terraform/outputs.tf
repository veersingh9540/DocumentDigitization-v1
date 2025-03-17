output "s3_bucket_name" {
  description = "Name of the S3 bucket for document storage"
  value       = aws_s3_bucket.documents.bucket
}

output "ec2_instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.dashboard.public_ip
}

output "lambda_document_processor_name" {
  description = "Name of the document processor Lambda function"
  value       = aws_lambda_function.document_processor.function_name
}

output "lambda_dashboard_api_name" {
  description = "Name of the dashboard API Lambda function"
  value       = aws_lambda_function.dashboard_api.function_name
}
