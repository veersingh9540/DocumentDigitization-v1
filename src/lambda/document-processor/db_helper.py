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

def save_document(document_data):
    """
    Save extracted document data to the database.
    
    Args:
        document_data (dict): Document data to save
        
    Returns:
        str: Document ID of the saved document
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert non-string data to JSON
        table_data = json.dumps(document_data.get('table_data', []))
        form_data = json.dumps(document_data.get('form_data', []))
        entities = json.dumps(document_data.get('entities', []))
        key_phrases = json.dumps(document_data.get('key_phrases', []))
        
        # Insert into documents table
        cursor.execute('''
            INSERT INTO documents (
                document_id, file_name, bucket, key, processed_date,
                extracted_text, table_data, form_data, entities, key_phrases
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (document_id) DO UPDATE SET
                file_name = EXCLUDED.file_name,
                bucket = EXCLUDED.bucket,
                key = EXCLUDED.key,
                processed_date = EXCLUDED.processed_date,
                extracted_text = EXCLUDED.extracted_text,
                table_data = EXCLUDED.table_data,
                form_data = EXCLUDED.form_data,
                entities = EXCLUDED.entities,
                key_phrases = EXCLUDED.key_phrases
            RETURNING document_id
        ''', (
            document_data['document_id'],
            document_data['file_name'],
            document_data['bucket'],
            document_data['key'],
            document_data['processed_date'],
            document_data.get('extracted_text', ''),
            table_data,
            form_data,
            entities,
            key_phrases
        ))
        
        document_id = cursor.fetchone()[0]
        conn.commit()
        
        logger.info(f"Document saved to database with ID: {document_id}")
        return document_id
    
    except Exception as e:
        logger.error(f"Error saving document to database: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()

def save_cylinder_logs(document_id, cylinder_data):
    """
    Save cylinder logs data to the database.
    
    Args:
        document_id (str): Document ID
        cylinder_data (dict): Cylinder logs data
        
    Returns:
        int: ID of the saved cylinder logs record
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Parse month_year to date if possible
        month_year = cylinder_data.get('month_year', 'Unknown Date')
        date_recorded = None
        
        if month_year != 'Unknown Date':
            try:
                import datetime
                date_parts = month_year.split()
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_map.get(date_parts[0][:3], 1)
                year = int(date_parts[1])
                date_recorded = datetime.date(year, month, 1)
            except Exception as e:
                logger.warning(f"Could not parse date from {month_year}: {str(e)}")
        
        # Convert cylinder data to JSON
        filled_cylinders = json.dumps(cylinder_data.get('filled_cylinders', {}))
        empty_cylinders = json.dumps(cylinder_data.get('empty_cylinders', {}))
        analysis = json.dumps(cylinder_data.get('analysis', {}))
        
        # Insert into cylinder_logs table
        cursor.execute('''
            INSERT INTO cylinder_logs (
                document_id, month_year, date_recorded, filled_cylinders, 
                empty_cylinders, analysis
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (document_id) DO UPDATE SET
                month_year = EXCLUDED.month_year,
                date_recorded = EXCLUDED.date_recorded,
                filled_cylinders = EXCLUDED.filled_cylinders,
                empty_cylinders = EXCLUDED.empty_cylinders,
                analysis = EXCLUDED.analysis
            RETURNING id
        ''', (
            document_id,
            month_year,
            date_recorded,
            filled_cylinders,
            empty_cylinders,
            analysis
        ))
        
        log_id = cursor.fetchone()[0]
        conn.commit()
        
        # Update monthly stats
        update_monthly_stats(conn, month_year, date_recorded, cylinder_data)
        
        logger.info(f"Cylinder logs saved to database with ID: {log_id}")
        return log_id
    
    except Exception as e:
        logger.error(f"Error saving cylinder logs to database: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()

def update_monthly_stats(conn, month_year, date_recorded, cylinder_data):
    """
    Update monthly statistics for cylinder logs.
    
    Args:
        conn (connection): Database connection
        month_year (str): Month and year
        date_recorded (date): Date recorded
        cylinder_data (dict): Cylinder logs data
    """
    try:
        cursor = conn.cursor()
        
        # Check if stats exist for this month
        cursor.execute('''
            SELECT id FROM monthly_stats WHERE month_year = %s
        ''', (month_year,))
        
        result = cursor.fetchone()
        
        # Calculate filled cylinder stats
        filled_cylinders = cylinder_data.get('filled_cylinders', {})
        filled_stats = {
            'avg_opening_stock': calculate_average(filled_cylinders.get('opening_stock', [])),
            'avg_closing_stock': calculate_average(filled_cylinders.get('closing_stock', [])),
            'avg_receipts': calculate_average(filled_cylinders.get('receipts', [])),
            'avg_issues': calculate_average(filled_cylinders.get('issues', [])),
            'total_receipts': calculate_sum(filled_cylinders.get('receipts', [])),
            'total_issues': calculate_sum(filled_cylinders.get('issues', []))
        }
        
        # Calculate empty cylinder stats
        empty_cylinders = cylinder_data.get('empty_cylinders', {})
        empty_stats = {
            'avg_opening_stock': calculate_average(empty_cylinders.get('opening_stock', [])),
            'avg_closing_stock': calculate_average(empty_cylinders.get('closing_stock', [])),
            'avg_receipts': calculate_average(empty_cylinders.get('receipts', [])),
            'avg_returns': calculate_average(empty_cylinders.get('returns', [])),
            'total_receipts': calculate_sum(empty_cylinders.get('receipts', [])),
            'total_returns': calculate_sum(empty_cylinders.get('returns', []))
        }
        
        # Convert stats to JSON
        filled_stats_json = json.dumps(filled_stats)
        empty_stats_json = json.dumps(empty_stats)
        
        if result:
            # Update existing stats
            cursor.execute('''
                UPDATE monthly_stats SET
                    filled_cylinder_stats = %s,
                    empty_cylinder_stats = %s,
                    total_transactions = (
                        SELECT COUNT(*) FROM cylinder_logs 
                        WHERE month_year = %s
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE month_year = %s
            ''', (
                filled_stats_json,
                empty_stats_json,
                month_year,
                month_year
            ))
        else:
            # Insert new stats
            # Calculate date range for the month
            start_date = date_recorded
            end_date = None
            
            if start_date:
                import datetime
                import calendar
                
                # Calculate the last day of the month
                _, last_day = calendar.monthrange(start_date.year, start_date.month)
                end_date = datetime.date(start_date.year, start_date.month, last_day)
            
            cursor.execute('''
                INSERT INTO monthly_stats (
                    month_year, start_date, end_date, filled_cylinder_stats, 
                    empty_cylinder_stats, total_transactions
                ) VALUES (
                    %s, %s, %s, %s, %s, 1
                )
            ''', (
                month_year,
                start_date,
                end_date,
                filled_stats_json,
                empty_stats_json
            ))
        
        logger.info(f"Monthly stats updated for {month_year}")
    
    except Exception as e:
        logger.error(f"Error updating monthly stats: {str(e)}", exc_info=True)
        conn.rollback()
        raise

def calculate_average(values):
    """
    Calculate the average of a list of values.
    
    Args:
        values (list): List of numeric values
        
    Returns:
        float: Average value
    """
    if not values:
        return 0
    
    # Convert all values to float
    try:
        numeric_values = [float(v) for v in values if v is not None]
        if not numeric_values:
            return 0
        return round(sum(numeric_values) / len(numeric_values), 2)
    except (ValueError, TypeError):
        return 0

def calculate_sum(values):
    """
    Calculate the sum of a list of values.
    
    Args:
        values (list): List of numeric values
        
    Returns:
        float: Sum of values
    """
    if not values:
        return 0
    
    # Convert all values to float
    try:
        numeric_values = [float(v) for v in values if v is not None]
        return round(sum(numeric_values), 2)
    except (ValueError, TypeError):
        return 0

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
