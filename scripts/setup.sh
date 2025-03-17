#!/bin/bash
# Initial setup script for the project

# Create S3 bucket for Terraform state
aws s3 mb s3://document-processing-tf-state --region us-east-1

echo "S3 bucket for Terraform state created."

# Initialize Terraform
cd terraform
terraform init

echo "Terraform initialized. Ready to proceed with deployment."
