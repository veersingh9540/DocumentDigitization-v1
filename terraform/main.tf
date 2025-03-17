provider "aws" {
  region = var.aws_region
}

# S3 Bucket for Documents
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents-${var.environment}"

  tags = {
    Name        = "${var.project_name}-documents"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# PostgreSQL RDS Instance
resource "aws_db_instance" "postgres" {
  identifier           = "${var.project_name}-postgres-${var.environment}"
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "14"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.postgres14"
  skip_final_snapshot  = true
  publicly_accessible  = false

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.environment
  }
}

# EC2 Instance for Dashboard
resource "aws_instance" "dashboard" {
  ami                    = var.ec2_ami
  instance_type          = "t2.micro"
  vpc_security_group_ids = [aws_security_group.dashboard.id]
  key_name               = var.ssh_key_name
  
  user_data = <<-EOF
              #!/bin/bash
              echo "Installing dashboard application"
              # Your installation scripts here
              EOF

  tags = {
    Name        = "${var.project_name}-dashboard"
    Environment = var.environment
  }
}

# EIP for Dashboard EC2
resource "aws_eip" "dashboard" {
  instance = aws_instance.dashboard.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-dashboard-eip"
    Environment = var.environment
  }
}

# Security Group for Dashboard
resource "aws_security_group" "dashboard" {
  name        = "${var.project_name}-dashboard-sg"
  description = "Security group for dashboard EC2 instance"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "pgAdmin access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-dashboard-sg"
    Environment = var.environment
  }
}
