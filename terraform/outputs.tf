output "s3_bucket_name" {
  description = "The name of the S3 bucket for documents"
  value       = aws_s3_bucket.documents.bucket
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
