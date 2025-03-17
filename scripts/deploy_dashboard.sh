#!/bin/bash

# Script to deploy dashboard app

# Get S3 bucket name
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name document-processing-stack --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" --output text)

# Upload dashboard app to S3
aws s3 cp src/dashboard s3://$S3_BUCKET/app/ --recursive

# Get EC2 instance IP
EC2_IP=$(aws cloudformation describe-stacks --stack-name document-processing-stack --query "Stacks[0].Outputs[?OutputKey=='EC2InstancePublicIP'].OutputValue" --output text)

# Deploy dashboard app to EC2
ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no ec2-user@$EC2_IP "aws s3 cp s3://$S3_BUCKET/app/ /app/ --recursive && sudo systemctl restart dashboard"

echo "Dashboard app deployed successfully!"
