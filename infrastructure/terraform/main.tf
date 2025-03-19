provider "aws" {
  region = var.aws_region
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
