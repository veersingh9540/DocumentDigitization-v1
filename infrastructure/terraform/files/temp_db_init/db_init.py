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
            
            # Create cylinder_inventory table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cylinder_inventory (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(255) NOT NULL,
                date VARCHAR(50),
                month VARCHAR(20),
                year VARCHAR(10),
                opening_stock VARCHAR(50),
                receipt VARCHAR(50),
                total_stock VARCHAR(50),
                closing_stock VARCHAR(50),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                FOREIGN KEY (document_id) REFERENCES document_metadata(document_id) ON DELETE CASCADE
            );
            """)
            
            # Create index on document_id
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_fields_document_id ON document_fields(document_id);
            """)
            
            # Create index on cylinder inventory
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cylinder_inventory_document_id ON cylinder_inventory(document_id);
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
