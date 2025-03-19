aws_region  = "us-east-1"
project_name = "document-processing"
environment  = "dev"
db_name      = "documentdb"
db_username  = "postgres"
# Do not store actual password in this file
# db_password will be provided via environment variable TF_VAR_db_password
# or via GitHub Actions secrets
ssh_key_name = "ssh-key" # Replace with your SSH key name

# EC2 options
create_processor_instance = false
ec2_ami = "ami-0c7217cdde317cfec" # Ubuntu 22.04 LTS in us-east-1

# RDS options
db_instance_class = "db.t3.micro"
db_allocated_storage = 20
db_backup_retention_period = 7
db_multi_az = false
enable_enhanced_monitoring = false

# Lambda options
lambda_memory_size = 1024
document_processor_timeout = 300
dashboard_api_timeout = 30

# API Gateway options
api_gateway_throttling_rate_limit = 50
api_gateway_throttling_burst_limit = 100

# S3 lifecycle options
s3_lifecycle_transition_ia_days = 30
s3_lifecycle_transition_glacier_days = 60
s3_lifecycle_expiration_days = 365
