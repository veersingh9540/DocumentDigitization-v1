import os
import logging
import json
import boto3
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables for DB connection
DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME')
DB_NAME = os.environ.get('DB_NAME', 'dashboard')

def get_db_connection():
    """
    Create a connection to the PostgreSQL database using credentials from Secrets Manager.
    
    Returns:
        connection: PostgreSQL database connection
    """
    try:
        # Get database credentials from Secrets Manager
        secrets = get_db_credentials()
        
        # Create connection
        conn = psycopg2.connect(
            host=secrets['host'],
            port=secrets['port'],
            database=secrets['dbname'],
            user=secrets['username'],
            password=secrets['password']
        )
        
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}", exc_info=True)
        raise

def get_db_credentials():
    """
    Retrieve database credentials from AWS Secrets Manager.
    
    Returns:
        dict: Database credentials
    """
    if not DB_SECRET_NAME:
        # For local development or testing
        logger.warning("DB_SECRET_NAME not provided, using dummy credentials for testing")
        return {
            'username': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', 'postgres'),
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', 5432),
            'dbname': DB_NAME
        }
    
    # Get the secret from Secrets Manager
    client = boto3.client('secretsmanager')
    
    try:
        response = client.get_secret_value(SecretId=DB_SECRET_NAME)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        logger.error(f"Error retrieving database credentials: {str(e)}", exc_info=True)
        raise

def create_tables():
    """
    Create necessary database tables if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100) UNIQUE NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                bucket VARCHAR(255) NOT NULL,
                key VARCHAR(1000) NOT NULL,
                processed_date TIMESTAMP NOT NULL,
                extracted_text TEXT,
                table_data JSONB,
                form_data JSONB,
                entities JSONB,
                key_phrases JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create cylinder_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cylinder_logs (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(100) REFERENCES documents(document_id),
                month_year VARCHAR(100),
                date_recorded DATE,
                filled_cylinders JSONB,
                empty_cylinders JSONB,
                analysis JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create monthly_stats table for aggregated statistics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_stats (
                id SERIAL PRIMARY KEY,
                month_year VARCHAR(100) UNIQUE NOT NULL,
                start_date DATE,
                end_date DATE,
                filled_cylinder_stats JSONB,
                empty_cylinder_stats JSONB,
                total_transactions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database tables created successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

def get_document_by_id(document_id):
    """
    Retrieve a document by its ID.
    
    Args:
        document_id (str): Document ID
        
    Returns:
        dict: Document data
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT document_id, file_name, bucket, key, processed_date,
                   extracted_text, table_data, form_data, entities, key_phrases,
                   created_at
            FROM documents WHERE document_id = %s
        ''', (document_id,))
        
        result = cursor.fetchone()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            document = dict(zip(columns, result))
            
            # Convert JSONB fields from string to dict
            for field in ['table_data', 'form_data', 'entities', 'key_phrases']:
                if document[field]:
                    document[field] = json.loads(document[field])
            
            return document
        else:
            return None
    
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}", exc_info=True)
        raise
    
    finally:
        if conn:
            conn.close()

def get_cylinder_logs(month_year=None, limit=10, offset=0):
    """
    Retrieve cylinder logs from the database.
    
    Args:
        month_year (str, optional): Filter by month and year
        limit (int): Maximum number of records to return
        offset (int): Offset for pagination
        
    Returns:
        list: List of cylinder logs
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT c.id, c.document_id, c.month_year, c.date_recorded,
                   c.filled_cylinders, c.empty_cylinders, c.analysis,
                   d.file_name, d.bucket, d.key, c.created_at
            FROM cylinder_logs c
            JOIN documents d ON c.document_id = d.document_id
        '''
        
        params = []
        
        if month_year:
            query += ' WHERE c.month_year = %s'
            params.append(month_year)
        
        query += ' ORDER BY c.date_recorded DESC, c.created_at DESC'
        query += ' LIMIT %s OFFSET %s'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        logs = []
        for result in results:
            log = dict(zip(columns, result))
            
            # Convert JSONB fields from string to dict
            for field in ['filled_cylinders', 'empty_cylinders', 'analysis']:
                if log[field]:
                    log[field] = json.loads(log[field])
            
            logs.append(log)
        
        return logs
    
    except Exception as e:
        logger.error(f"Error retrieving cylinder logs: {str(e)}", exc_info=True)
        raise
    
    finally:
        if conn:
            conn.close()

def get_monthly_stats(start_date=None, end_date=None):
    """
    Retrieve monthly statistics.
    
    Args:
        start_date (str, optional): Start date in ISO format (YYYY-MM-DD)
        end_date (str, optional): End date in ISO format (YYYY-MM-DD)
        
    Returns:
        list: List of monthly statistics
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, month_year, start_date, end_date,
                   filled_cylinder_stats, empty_cylinder_stats,
                   total_transactions, created_at, updated_at
            FROM monthly_stats
        '''
        
        params = []
        
        if start_date and end_date:
            query += ' WHERE start_date >= %s AND end_date <= %s'
            params.extend([start_date, end_date])
        elif start_date:
            query += ' WHERE start_date >= %s'
            params.append(start_date)
        elif end_date:
            query += ' WHERE end_date <= %s'
            params.append(end_date)
        
        query += ' ORDER BY start_date DESC'
        
        cursor.execute(query, params)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        stats = []
        for result in results:
            stat = dict(zip(columns, result))
            
            # Convert JSONB fields from string to dict
            for field in ['filled_cylinder_stats', 'empty_cylinder_stats']:
                if stat[field]:
                    stat[field] = json.loads(stat[field])
            
            stats.append(stat)
        
        return stats
    
    except Exception as e:
        logger.error(f"Error retrieving monthly stats: {str(e)}", exc_info=True)
        raise
    
    finally:
        if conn:
            conn.close()
