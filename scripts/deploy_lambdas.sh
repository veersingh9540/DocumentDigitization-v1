#!/bin/bash
set -e

# Check if functions exist first
echo "Checking if Lambda functions exist..."

# Try to get function info - if it fails, create the function
function deploy_lambda() {
  local FUNCTION_NAME=$1
  local ZIP_FILE=$2
  local ROLE_ARN=$3
  local ENV_VARS=$4
  
  echo "Deploying $FUNCTION_NAME..."
  
  # Check if function exists
  if aws lambda get-function --function-name $FUNCTION_NAME 2>&1 | grep -q "Function not found"; then
    echo "Creating new Lambda function: $FUNCTION_NAME"
    
    # Create function with environment variables if provided
    if [ -n "$ENV_VARS" ]; then
      aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime nodejs18.x \
        --role $ROLE_ARN \
        --handler index.handler \
        --zip-file fileb://$ZIP_FILE \
        --environment "$ENV_VARS"
    else
      aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime nodejs18.x \
        --role $ROLE_ARN \
        --handler index.handler \
        --zip-file fileb://$ZIP_FILE
    fi
  else
    echo "Updating existing Lambda function: $FUNCTION_NAME"
    
    # Update function code
    aws lambda update-function-code \
      --function-name $FUNCTION_NAME \
      --zip-file fileb://$ZIP_FILE
      
    # Update environment variables if provided
    if [ -n "$ENV_VARS" ]; then
      aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "$ENV_VARS"
    fi
  fi
}

# Get or create IAM role for Lambda execution
LAMBDA_ROLE_NAME="lambda-execution-role"
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
  echo "Creating Lambda execution role..."
  
  # Create the policy document for the role
  cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

  # Create role
  ROLE_ARN=$(aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json \
    --query 'Role.Arn' --output text)
  
  # Attach basic Lambda execution policy
  aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  
  # Attach S3 read-only access for document processing
  aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
  
  # Wait for role to propagate
  echo "Waiting for IAM role to propagate..."
  sleep 10
fi

echo "Using Lambda execution role: $ROLE_ARN"

# Get S3 bucket and RDS endpoint from Terraform outputs
S3_BUCKET=$(cd terraform && terraform output -raw s3_bucket_name 2>/dev/null || echo "")
DB_ENDPOINT=$(cd terraform && terraform output -raw rds_endpoint 2>/dev/null || echo "")

# Prepare environment variables
if [ -n "$S3_BUCKET" ] && [ -n "$DB_ENDPOINT" ]; then
  ENV_VARS="{\"Variables\":{\"S3_BUCKET\":\"$S3_BUCKET\",\"DB_ENDPOINT\":\"$DB_ENDPOINT\"}}"
  echo "Using environment variables from Terraform: S3_BUCKET=$S3_BUCKET, DB_ENDPOINT=$DB_ENDPOINT"
else
  ENV_VARS=""
  echo "Warning: Could not get S3 bucket or DB endpoint from Terraform outputs."
fi

# Deploy both Lambda functions
deploy_lambda "document-processor" "document_processor.zip" "$ROLE_ARN" "$ENV_VARS"
deploy_lambda "dashboard-api" "dashboard_api.zip" "$ROLE_ARN" "$ENV_VARS"

echo "Lambda deployment completed successfully!"

# Create a simple test event file
cat > test-event.json << EOF
{
  "path": "/stats",
  "httpMethod": "GET",
  "queryStringParameters": {}
}
EOF

# Test the Lambda functions
echo "Testing document-processor Lambda function..."
aws lambda invoke --function-name document-processor --payload '{}' document-processor-output.json
cat document-processor-output.json

echo "Testing dashboard-api Lambda function..."
aws lambda invoke --function-name dashboard-api --payload file://test-event.json dashboard-api-output.json
cat dashboard-api-output.json

echo "Tests completed."
