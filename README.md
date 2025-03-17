# Dashboard Project

This project deploys a complete dashboard infrastructure on AWS, including:

- S3 bucket for document storage
- PostgreSQL RDS database
- EC2 instance for dashboard frontend
- Lambda functions for document processing and API

## Project Structure

```
dashboard-project/
├── terraform/         # Infrastructure as Code
├── lambda/            # Lambda functions
├── scripts/           # Deployment scripts
└── .github/workflows/ # CI/CD pipelines
```

## Setup Instructions

### Prerequisites

1. AWS account with appropriate permissions
2. GitHub repository
3. SSH key pair created in AWS

### GitHub Secrets

Set up the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: Your preferred AWS region (default: us-east-1)
- `DB_PASSWORD`: Password for PostgreSQL database

### Deployment

1. Push the code to your GitHub repository
2. The infrastructure will deploy automatically via GitHub Actions
3. You can also manually trigger deployments from the Actions tab

## Available Workflows

- **Terraform Deploy**: Deploys the infrastructure
- **Terraform Destroy**: Destroys the infrastructure (manual trigger with confirmation)
- **Lambda Deploy**: Deploys the Lambda functions

## Testing

After deployment, you can access:

- Dashboard: http://{ec2_instance_public_ip}
- pgAdmin: http://{ec2_instance_public_ip}:8080
- Lambda functions via AWS console
