# Database Credentials Secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}-db-credentials-${var.environment}"
  description = "Database credentials for the document processing system"

  tags = {
    Name        = "${var.project_name}-db-credentials"
    Environment = var.environment
  }
}

# Database Credentials Secret Value
resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    engine   = "postgres"
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    dbname   = var.db_name
  })
}

# Database Subnet Group
resource "aws_db_subnet_group" "postgres" {
  name       = "${var.project_name}-db-subnet-group-${var.environment}"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Environment = var.environment
  }
}

# Database Security Group
resource "aws_security_group" "postgres" {
  name        = "${var.project_name}-postgres-sg-${var.environment}"
  description = "Security group for PostgreSQL RDS instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.dashboard.id, aws_security_group.lambda.id]
    description     = "PostgreSQL access from Lambda and EC2"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-postgres-sg"
    Environment = var.environment
  }
}

# Security Group for Lambda Functions
resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-lambda-sg-${var.environment}"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-lambda-sg"
    Environment = var.environment
  }
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
  db_subnet_group_name = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.environment
  }
}

# Lambda for Database Initialization
resource "aws_lambda_function" "db_init" {
  function_name    = "${var.project_name}-db-init-${var.environment}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "db_init.lambda_handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/db_init.zip"
  source_code_hash = filebase64sha256("${path.module}/files/db_init.zip")
  timeout          = 60

  environment {
    variables = {
      DB_SECRET_NAME = aws_secretsmanager_secret.db_credentials.name
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = {
    Name        = "${var.project_name}-db-init"
    Environment = var.environment
  }
}

# Null resource to invoke the DB init Lambda
resource "null_resource" "invoke_db_init" {
  depends_on = [aws_lambda_function.db_init, aws_db_instance.postgres]

  provisioner "local-exec" {
    command = <<EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.db_init.function_name} \
        --region ${var.aws_region} \
        /dev/null
    EOT
  }

  triggers = {
    db_instance_id = aws_db_instance.postgres.id
  }
}

# DB Init Lambda ZIP file
data "archive_file" "db_init_zip" {
  type        = "zip"
  output_path = "${path.module}/files/db_init.zip"

  source {
    content = <<EOF
import json
import boto3
import os
import psycopg2
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager_client = boto3.client('secretsmanager')

# Environment variables
DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME')

def get_db_credentials():
    """Retrieve database credentials from AWS Secrets Manager"""
    try:
        response = secretsmanager_client.get_secret_value(
            SecretId=DB_SECRET_NAME
        )
        secret = json.loads(response['SecretString'])
        return {
            'host': secret['host'],
            'port': secret['port'],
            'dbname': secret['dbname'],
            'user': secret['username'],
            'password': secret['password']
        }
    except Exception as e:
        logger.error(f"Error retrieving database credentials: {str(e)}")
        raise

def create_tables(conn):
    """Create database tables if they don't exist"""
    try:
        with conn.cursor() as cursor:
            # Create document_metadata table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(255) NOT NULL UNIQUE,
                original_bucket VARCHAR(255) NOT NULL,
                original_key VARCHAR(255) NOT NULL,
                processed_bucket VARCHAR(255) NOT NULL,
                processed_key VARCHAR(255) NOT NULL,
                document_type VARCHAR(50) NOT NULL,
                page_count INTEGER NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP
            );
            """)
            
            # Create document_fields table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_fields (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(255) NOT NULL,
                field_name VARCHAR(255) NOT NULL,
                field_value TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                FOREIGN KEY (document_id) REFERENCES document_metadata(document_id) ON DELETE CASCADE
            );
            """)
            
            # Create index on document_id
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_fields_document_id ON document_fields(document_id);
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        raise

def lambda_handler(event, context):
    """Initialize database schema"""
    try:
        # Get database credentials
        db_credentials = get_db_credentials()
        
        # Connect to the database
        conn = psycopg2.connect(
            host=db_credentials['host'],
            port=db_credentials['port'],
            dbname=db_credentials['dbname'],
            user=db_credentials['user'],
            password=db_credentials['password']
        )
        
        # Create tables
        create_tables(conn)
        
        # Close connection
        conn.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps('Database initialization completed successfully')
        }
    
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error initializing database: {str(e)}')
        }
EOF
    filename = "db_init.py"
  }

  source {
    content = <<EOF
psycopg2-binary>=2.9.5
boto3>=1.26.0
EOF
    filename = "requirements.txt"
  }
}
