# Document Processing Dashboard

A complete AWS infrastructure for automatically processing documents (PDF, images) using OCR, storing extracted data in a database, and visualizing it through a dashboard.

## Features

- **Automated Document Processing**: Upload documents to S3 to trigger automatic processing
- **OCR Capabilities**: Extract text, tables, and form data from PDF and image files
- **Data Storage**: Store extracted data in PostgreSQL database
- **Dashboard Visualization**: View and analyze document data through interactive dashboards
- **Infrastructure as Code**: Complete AWS infrastructure defined using Terraform
- **CI/CD Pipeline**: Automated testing, building, and deployment with GitHub Actions

## Architecture

The system consists of:

- **S3 Buckets**: For document storage (input and processed)
- **Lambda Functions**: For document processing and API
- **PostgreSQL Database**: For storing extracted data
- **EC2 Instance**: For hosting the dashboard frontend
- **EventBridge**: For triggering document processing on S3 uploads
- **API Gateway**: For exposing the dashboard API

## Setup Instructions

### Prerequisites

1. AWS account with appropriate permissions
2. GitHub repository for hosting the code
3. SSH key pair created in AWS (for EC2 access)
4. Terraform installed locally (for manual deployments)
5. AWS CLI configured locally (for manual operations)

### GitHub Secrets

Set up the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: Your preferred AWS region (default: us-east-1)
- `AWS_ACCOUNT_ID`: Your AWS account ID (for IAM roles)
- `DB_PASSWORD`: Password for PostgreSQL database
- `SSH_PRIVATE_KEY`: Private key for SSH access to EC2 instance (created in AWS)

### Deployment

#### Automatic Deployment (Recommended)

1. Fork this repository
2. Set up the required GitHub secrets
3. Push to the `main` branch to trigger automatic deployment
4. Monitor the deployment progress in the GitHub Actions tab
5. Once complete, access the dashboard using the provided URL

#### Manual Deployment

1. Clone the repository
2. Initialize Terraform:
   ```sh
   cd terraform
   terraform init
   ```
3. Create a `terraform.tfvars` file with your configuration:
   ```
   aws_region = "us-east-1"
   project_name = "dashboard"
   environment = "dev"
   db_name = "dashboard"
   db_username = "postgres"
   db_password = "your-secure-password"
   ssh_key_name = "your-ssh-key"
   ```
4. Apply the Terraform configuration:
   ```sh
   terraform apply
   ```
5. Package and deploy Lambda functions:
   ```sh
   cd ..
   # Create deployment packages
   mkdir -p build
   
   # Package document processor Lambda
   cd src/lambda/document_processor
   pip install -r requirements.txt -t .
   zip -r ../../../build/document_processor.zip .
   cd ../../..
   
   # Package dashboard API Lambda
   cd src/lambda/dashboard_api
   pip install -r requirements.txt -t .
   zip -r ../../../build/dashboard_api.zip .
   cd ../../..
   
   # Deploy Lambda functions using AWS CLI
   aws lambda update-function-code --function-name document-processor --zip-file fileb://build/document_processor.zip
   aws lambda update-function-code --function-name dashboard-api --zip-file fileb://build/dashboard_api.zip
   ```
6. Build and deploy the dashboard frontend:
   ```sh
   # Build React app
   cd src/dashboard
   npm install
   npm run build
   
   # Deploy to EC2 using SCP
   scp -r build/* ec2-user@<ec2-instance-ip>:/var/www/html/
   ```

## Usage

### Processing Documents

1. Upload documents to the input folder of the S3 bucket:
   ```sh
   aws s3 cp your-document.pdf s3://dashboard-documents-dev/input/
   ```
2. The document will be automatically processed, and the data will be stored in the database
3. You can monitor the processing status in the CloudWatch Logs

### Accessing the Dashboard

1. After deployment, you can access the dashboard at:
   ```
   http://<ec2-instance-public-ip>
   ```
2. The dashboard displays visualizations of the processed data, including:
   - Monthly cylinder inventory trends
   - Filled vs. empty cylinder statistics
   - Stock changes over time

### API Endpoints

The system exposes the following API endpoints:

- **GET /api/documents**: List all processed documents
- **GET /api/documents/{id}**: Get specific document details
- **GET /api/cylinder-logs**: Get cylinder logs data
- **GET /api/stats**: Get aggregated statistics
- **GET /api/stats/monthly**: Get monthly statistics
- **GET /api/stats/summary**: Get summary statistics

## Repository Structure

```
document-processing-dashboard/
├── .github/workflows/        # GitHub Actions workflows
│   ├── ci-cd-pipeline.yml    # Main CI/CD workflow
│   └── terraform-destroy.yml # Infrastructure teardown workflow
│
├── terraform/                # Infrastructure as code
│   ├── main.tf               # Main Terraform configuration
│   ├── variables.tf          # Variable definitions
│   ├── outputs.tf            # Output definitions
│   └── backend.tf            # Remote state configuration
│
├── src/                      # Application source code
│   ├── lambda/               # Lambda functions
│   │   ├── document_processor/   # Document processing function
│   │   │   ├── index.py          # Main handler
│   │   │   ├── textract_helper.py # AWS Textract helper
│   │   │   ├── ocr_helper.py     # OCR processing
│   │   │   ├── db_helper.py      # Database operations
│   │   │   ├── pdf_extractor.py  # PDF extraction utilities
│   │   │   └── requirements.txt  # Dependencies
│   │   └── dashboard_api/        # API for dashboard
│   │       ├── index.py          # Main handler
│   │       ├── db_helper.py      # Database operations
│   │       └── requirements.txt  # Dependencies
│   │
│   └── dashboard/            # Frontend application
│       ├── public/           # Static assets
│       ├── src/              # React application source
│       │   ├── components/   # React components
│       │   ├── App.js        # Main application component
│       │   └── App.css       # Application styles
│       └── package.json      # Dependencies
│
└── README.md                 # Project documentation
```

## Destroying Infrastructure

If you need to tear down the infrastructure:

1. Go to GitHub Actions
2. Select the "Terraform Destroy" workflow
3. Run the workflow with the appropriate environment
4. Type "destroy-[environment]" to confirm

Alternatively, for manual destruction:

```sh
cd terraform
terraform destroy
```

## Troubleshooting

### Common Issues

1. **Lambda Timeout**: For large documents, you might need to increase the Lambda function timeout in the Terraform configuration.
2. **Database Connection Issues**: Ensure the Lambda functions have proper network access to the RDS instance.
3. **S3 Trigger Not Working**: Check CloudWatch Logs for errors and ensure the IAM roles have proper permissions.

### Logs

- **Lambda Logs**: Check CloudWatch Logs for Lambda function execution logs.
- **EC2 Logs**: SSH into the EC2 instance and check Nginx logs at `/var/log/nginx/`.
- **Terraform Logs**: Set the `TF_LOG=DEBUG` environment variable for detailed Terraform logs.

## Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature-name`
3. Make changes and commit: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License.
