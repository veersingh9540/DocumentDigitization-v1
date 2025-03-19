provider "aws" {
  region = var.aws_region
}

# Use local backend for testing and then move to S3 for production
terraform {
  # backend "local" {
  #   path = "terraform.tfstate"
  # }
  
  # Uncomment this block and comment the local backend to use S3 as backend
  backend "s3" {
    bucket = "document-processing-tf-state"
    key    = "terraform/state"
    region = "us-east-1"
  }
}

# Tags for all resources
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Terraform   = "true"
    ManagedBy   = "terraform"
  }
}
