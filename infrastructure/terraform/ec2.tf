# Security Group for Dashboard EC2
resource "aws_security_group" "dashboard" {
  name        = "${var.project_name}-dashboard-sg-${var.environment}"
  description = "Security group for dashboard EC2 instance"
  vpc_id      = aws_vpc.main.id

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
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-dashboard-sg-${var.environment}"
    Environment = var.environment
  }
}

# EC2 Instance for Dashboard
resource "aws_instance" "dashboard" {
  ami                    = var.ec2_ami
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.public_subnet_1.id
  vpc_security_group_ids = [aws_security_group.dashboard.id]
  key_name               = var.ssh_key_name
  
  user_data = <<-EOF
              #!/bin/bash
              # Update system
              echo "Updating system packages..."
              apt-get update
              apt-get upgrade -y
              
              # Install required packages
              echo "Installing required packages..."
              apt-get install -y nginx certbot python3-certbot-nginx git

              # Configure Nginx
              echo "Configuring Nginx..."
              cat > /etc/nginx/sites-available/default <<'NGINX'
              server {
                  listen 80 default_server;
                  listen [::]:80 default_server;
                  
                  root /var/www/html;
                  index index.html index.htm;
                  
                  server_name _;
                  
                  location / {
                      try_files $uri $uri/ /index.html;
                  }
                  
                  # API proxy
                  location /api/ {
                      proxy_pass ${aws_apigatewayv2_stage.dashboard_api_stage.invoke_url}/;
                      proxy_http_version 1.1;
                      proxy_set_header Host $host;
                      proxy_set_header X-Real-IP $remote_addr;
                  }
              }
              NGINX
              
              # Restart Nginx
              systemctl restart nginx
              
              # Create placeholder index
              echo "<h1>Dashboard Application</h1><p>Deploying dashboard application...</p>" > /var/www/html/index.html
              EOF

  tags = {
    Name        = "${var.project_name}-dashboard-${var.environment}"
    Environment = var.environment
  }
}

# EIP for Dashboard EC2
resource "aws_eip" "dashboard" {
  instance = aws_instance.dashboard.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-dashboard-eip-${var.environment}"
    Environment = var.environment
  }
}

# EC2 Instance for Document Processing (optional - can be used for batch processing)
resource "aws_instance" "processor" {
  count                  = var.create_processor_instance ? 1 : 0
  ami                    = var.ec2_ami
  instance_type          = "t2.small"
  subnet_id              = aws_subnet.public_subnet_1.id
  vpc_security_group_ids = [aws_security_group.dashboard.id]
  key_name               = var.ssh_key_name
  
  user_data = <<-EOF
              #!/bin/bash
              # Update system
              echo "Updating system packages..."
              apt-get update
              apt-get upgrade -y
              
              # Install required packages
              echo "Installing required packages..."
              apt-get install -y python3-pip python3-venv tesseract-ocr libtesseract-dev poppler-utils

              # Create directory for document processing
              mkdir -p /opt/document-processor
              
              # Set up virtual environment
              cd /opt/document-processor
              python3 -m venv venv
              source venv/bin/activate
              
              # Install Python dependencies
              pip install boto3 pytesseract pdf2image PyPDF2 Pillow
              
              # Create service user
              useradd -m -s /bin/bash processor
              chown -R processor:processor /opt/document-processor
              
              # Create systemd service for processor
              cat > /etc/systemd/system/document-processor.service <<'SERVICE'
              [Unit]
              Description=Document Processing Service
              After=network.target
              
              [Service]
              User=processor
              Group=processor
              WorkingDirectory=/opt/document-processor
              ExecStart=/opt/document-processor/venv/bin/python /opt/document-processor/processor.py
              Restart=on-failure
              RestartSec=5s
              
              [Install]
              WantedBy=multi-user.target
              SERVICE
              
              # Reload systemd
              systemctl daemon-reload
              EOF

  tags = {
    Name        = "${var.project_name}-processor-${var.environment}"
    Environment = var.environment
    Terraform   = "true"
  }
}

# EIP for Processor EC2 (if created)
resource "aws_eip" "processor" {
  count    = var.create_processor_instance ? 1 : 0
  instance = aws_instance.processor[0].id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-processor-eip-${var.environment}"
    Environment = var.environment
  }
}
