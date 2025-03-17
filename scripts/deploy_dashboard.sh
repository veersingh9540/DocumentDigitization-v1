#!/bin/bash
# Script to deploy dashboard app to EC2

# Get S3 bucket name and EC2 IP from Terraform output
S3_BUCKET=$(cd terraform && terraform output -raw s3_bucket_name)
EC2_IP=$(cd terraform && terraform output -raw ec2_instance_public_ip)

# Upload dashboard app to S3
echo "Uploading dashboard app to S3..."
aws s3 cp src/dashboard s3://$S3_BUCKET/app/ --recursive

# SSH into EC2 instance and deploy app
echo "Deploying dashboard app to EC2..."
ssh -o StrictHostKeyChecking=no ec2-user@$EC2_IP << EOF
    # Pull app from S3
    aws s3 cp s3://$S3_BUCKET/app/ /app/ --recursive
    
    # Restart dashboard service
    sudo systemctl restart dashboard
EOF

echo "Dashboard app deployed successfully!"
