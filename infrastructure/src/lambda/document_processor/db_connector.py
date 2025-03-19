import psycopg2
import logging
import json
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DatabaseConnector:
    def __init__(self, host, port, dbname, user, password):
        """Initialize database connector with connection parameters"""
        self.connection_params = {
            'host': host,
            'port': port,
            'dbname': dbname,
            'user': user,
            'password': password
        }
        self.conn = None
    
    def connect(self):
        """Establish a database connection"""
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(**self.connection_params)
            return self.conn
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute a SQL query and optionally fetch results"""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch:
                    result = cursor.fetchall()
                    return result
                
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error executing query: {str(e)}")
            raise
    
    def insert_document_metadata(self, metadata):
        """Insert document metadata into the database"""
        query = """
        INSERT INTO document_metadata (
            document_id, original_bucket, original_key, 
            processed_bucket, processed_key, document_type, 
            page_count, status, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            metadata['document_id'],
            metadata['original_bucket'],
            metadata['original_key'],
            metadata['processed_bucket'],
            metadata['processed_key'],
            metadata['document_type'],
            metadata['page_count'],
            metadata['status'],
            datetime.now()
        )
        
        try:
            result = self.execute_query(query, params)
            logger.info(f"Inserted document metadata for {metadata['document_id']}")
            return result
        except Exception as e:
            logger.error(f"Error inserting document metadata: {str(e)}")
            raise
    
    def insert_document_fields(self, document_id, fields):
        """Insert extracted document fields into the database"""
        if not fields:
            logger.info(f"No fields to insert for document {document_id}")
            return 0
        
        query = """
        INSERT INTO document_fields (
            document_id, field_name, field_value, created_at
        ) VALUES (%s, %s, %s, %s)
        """
        
        count = 0
        conn = self.connect()
        
        try:
            with conn.cursor() as cursor:
                for field in fields:
                    for field_name, field_value in field.items():
                        params = (
                            document_id,
                            field_name,
                            str(field_value),
                            datetime.now()
                        )
                        cursor.execute(query, params)
                        count += 1
                
                conn.commit()
                logger.info(f"Inserted {count} fields for document {document_id}")
                return count
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error inserting document fields: {str(e)}")
            raise
