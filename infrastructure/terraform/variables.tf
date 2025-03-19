variable "aws_region" {
  description = "The AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "document-processing"
}

variable "environment" {
  description = "The deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "db_name" {
  description = "The name of the database"
  type        = string
  default     = "documentdb"
}

variable "db_username" {
  description = "The username for the database"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "The password for the database"
  type        = string
  sensitive   = true
}

variable "ec2_ami" {
  description = "The AMI ID for the EC2 instance"
  type        = string
  default     = "ami-0c7217cdde317cfec" # Ubuntu 22.04 LTS in us-east-1
}

variable "ssh_key_name" {
  description = "The name of the SSH key pair"
  type        = string
}

variable "create_processor_instance" {
  description = "Whether to create a separate EC2 instance for document processing"
  type        = bool
  default     = false
}

variable "enable_enhanced_monitoring" {
  description = "Whether to enable enhanced monitoring for RDS"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "The instance class for the RDS instance"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "The allocated storage for the RDS instance in GB"
  type        = number
  default     = 20
}

variable "db_backup_retention_period" {
  description = "The backup retention period for the RDS instance in days"
  type        = number
  default     = 7
}

variable "db_multi_az" {
  description = "Whether to enable multi-AZ for the RDS instance"
  type        = bool
  default     = false
}

variable "api_gateway_throttling_rate_limit" {
  description = "The API Gateway throttling rate limit"
  type        = number
  default     = 50
}

variable "api_gateway_throttling_burst_limit" {
  description = "The API Gateway throttling burst limit"
  type        = number
  default     = 100
}

variable "lambda_memory_size" {
  description = "The memory size for Lambda functions in MB"
  type        = number
  default     = 1024
}

variable "document_processor_timeout" {
  description = "The timeout for the document processor Lambda function in seconds"
  type        = number
  default     = 300
}

variable "dashboard_api_timeout" {
  description = "The timeout for the dashboard API Lambda function in seconds"
  type        = number
  default     = 30
}

variable "s3_lifecycle_transition_ia_days" {
  description = "The number of days after which objects are transitioned to STANDARD_IA"
  type        = number
  default     = 30
}

variable "s3_lifecycle_transition_glacier_days" {
  description = "The number of days after which objects are transitioned to GLACIER"
  type        = number
  default     = 60
}

variable "s3_lifecycle_expiration_days" {
  description = "The number of days after which objects are deleted"
  type        = number
  default     = 365
}
