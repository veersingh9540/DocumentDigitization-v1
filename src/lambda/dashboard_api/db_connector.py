import psycopg2
import logging
from datetime import datetime, timedelta

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
    
    def get_document_by_id(self, document_id):
        """Retrieve document metadata and fields by document ID"""
        metadata_query = """
        SELECT * FROM document_metadata WHERE document_id = %s
        """
        
        fields_query = """
        SELECT field_name, field_value FROM document_fields 
        WHERE document_id = %s
        """
        
        try:
            metadata = self.execute_query(metadata_query, (document_id,), fetch=True)
            
            if not metadata:
                return None
            
            fields = self.execute_query(fields_query, (document_id,), fetch=True)
            
            # Convert metadata row to dictionary
            columns = ['id', 'document_id', 'original_bucket', 'original_key', 
                      'processed_bucket', 'processed_key', 'document_type', 
                      'page_count', 'status', 'created_at', 'updated_at']
            
            metadata_dict = dict(zip(columns, metadata[0]))
            
            # Convert datetime objects to strings
            for key in metadata_dict:
                if isinstance(metadata_dict[key], datetime):
                    metadata_dict[key] = metadata_dict[key].isoformat()
            
            # Convert fields to dictionary
            fields_dict = {field[0]: field[1] for field in fields}
            
            result = {
                'metadata': metadata_dict,
                'fields': fields_dict
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            raise
    
    def get_recent_documents(self, limit=10):
        """Retrieve recent documents with their metadata"""
        query = """
        SELECT document_id, document_type, status, created_at 
        FROM document_metadata 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        
        try:
            rows = self.execute_query(query, (limit,), fetch=True)
            
            documents = []
            for row in rows:
                doc = {
                    'document_id': row[0],
                    'document_type': row[1],
                    'status': row[2],
                    'created_at': row[3].isoformat() if isinstance(row[3], datetime) else row[3]
                }
                documents.append(doc)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error retrieving recent documents: {str(e)}")
            raise
    
    def search_documents(self, query_text, limit=20):
        """Search for documents containing specific text"""
        query = """
        SELECT DISTINCT d.document_id, d.document_type, d.status, d.created_at
        FROM document_metadata d
        JOIN document_fields f ON d.document_id = f.document_id
        WHERE f.field_value ILIKE %s
        ORDER BY d.created_at DESC
        LIMIT %s
        """
        
        try:
            search_pattern = f"%{query_text}%"
            rows = self.execute_query(query, (search_pattern, limit), fetch=True)
            
            documents = []
            for row in rows:
                doc = {
                    'document_id': row[0],
                    'document_type': row[1],
                    'status': row[2],
                    'created_at': row[3].isoformat() if isinstance(row[3], datetime) else row[3]
                }
                documents.append(doc)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise
    
    def get_document_statistics(self):
        """Get statistics about processed documents"""
        # Get total document count
        count_query = "SELECT COUNT(*) FROM document_metadata"
        
        # Get document count by type
        type_query = """
        SELECT document_type, COUNT(*) 
        FROM document_metadata 
        GROUP BY document_type
        ORDER BY COUNT(*) DESC
        """
        
        # Get documents processed in the last 7 days
        recent_query = """
        SELECT DATE(created_at) as day, COUNT(*) 
        FROM document_metadata 
        WHERE created_at >= %s
        GROUP BY day
        ORDER BY day
        """
        
        try:
            # Get total count
            total_count = self.execute_query(count_query, fetch=True)[0][0]
            
            # Get counts by type
            type_counts = self.execute_query(type_query, fetch=True)
            types = {row[0]: row[1] for row in type_counts}
            
            # Get daily counts for last 7 days
            seven_days_ago = datetime.now() - timedelta(days=7)
            daily_counts = self.execute_query(recent_query, (seven_days_ago,), fetch=True)
            
            daily_data = []
            for row in daily_counts:
                daily_data.append({
                    'date': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                    'count': row[1]
                })
            
            # Return compiled statistics
            return {
                'total_documents': total_count,
                'by_type': types,
                'daily_counts': daily_data
            }
        
        except Exception as e:
            logger.error(f"Error retrieving document statistics: {str(e)}")
            raise
