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
                # If fields is a dict
                if isinstance(fields, dict):
                    for field_name, field_value in fields.items():
                        params = (
                            document_id,
                            field_name,
                            str(field_value),
                            datetime.now()
                        )
                        cursor.execute(query, params)
                        count += 1
                # If fields is a list
                elif isinstance(fields, list):
                    for item in fields:
                        if isinstance(item, dict):
                            for field_name, field_value in item.items():
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
    
    def insert_cylinder_inventory(self, inventory_data):
        """Insert cylinder inventory record into specialized table"""
        try:
            # First check if the cylinder_inventory table exists, create it if not
            self.create_cylinder_inventory_table()
            
            query = """
            INSERT INTO cylinder_inventory (
                document_id, date, month, year, opening_stock, 
                receipt, total_stock, closing_stock, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                inventory_data['document_id'],
                inventory_data['date'],
                inventory_data['month'],
                inventory_data['year'],
                inventory_data.get('opening_stock'),
                inventory_data.get('receipt'),
                inventory_data.get('total_stock'),
                inventory_data.get('closing_stock'),
                datetime.now()
            )
            
            result = self.execute_query(query, params)
            logger.info(f"Inserted cylinder inventory record for document {inventory_data['document_id']}")
            return result
        except Exception as e:
            logger.error(f"Error inserting cylinder inventory: {str(e)}")
            raise
    
    def create_cylinder_inventory_table(self):
        """Create the cylinder inventory table if it doesn't exist"""
        query = """
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
        CREATE INDEX IF NOT EXISTS idx_cylinder_inventory_document_id ON cylinder_inventory(document_id);
        CREATE INDEX IF NOT EXISTS idx_cylinder_inventory_date ON cylinder_inventory(date);
        CREATE INDEX IF NOT EXISTS idx_cylinder_inventory_month_year ON cylinder_inventory(month, year);
        """
        
        try:
            self.execute_query(query)
            logger.info("Cylinder inventory table created or verified")
            return True
        except Exception as e:
            logger.error(f"Error creating cylinder inventory table: {str(e)}")
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
        
        inventory_query = """
        SELECT * FROM cylinder_inventory 
        WHERE document_id = %s
        ORDER BY date
        """
        
        try:
            metadata = self.execute_query(metadata_query, (document_id,), fetch=True)
            
            if not metadata:
                return None
            
            # First try to get cylinder inventory data if this is that type of document
            inventory_data = self.execute_query(inventory_query, (document_id,), fetch=True)
            
            # Also get general fields
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
            
            # Prepare result
            result = {
                'metadata': metadata_dict,
                'fields': fields_dict
            }
            
            # Add inventory data if available
            if inventory_data:
                inventory_columns = ['id', 'document_id', 'date', 'month', 'year', 
                                    'opening_stock', 'receipt', 'total_stock', 
                                    'closing_stock', 'created_at']
                
                inventory_list = []
                for row in inventory_data:
                    inventory_item = dict(zip(inventory_columns, row))
                    # Convert datetime to string
                    if isinstance(inventory_item.get('created_at'), datetime):
                        inventory_item['created_at'] = inventory_item['created_at'].isoformat()
                    inventory_list.append(inventory_item)
                
                result['inventory_data'] = inventory_list
            
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
        LEFT JOIN document_fields f ON d.document_id = f.document_id
        WHERE f.field_value ILIKE %s
           OR d.document_id ILIKE %s
           OR d.document_type ILIKE %s
        ORDER BY d.created_at DESC
        LIMIT %s
        """
        
        try:
            search_pattern = f"%{query_text}%"
            rows = self.execute_query(query, (search_pattern, search_pattern, search_pattern, limit), fetch=True)
            
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
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY day
        ORDER BY day
        """
        
        # Get cylinder inventory stats if table exists
        cylinder_query = """
        SELECT 
            month, 
            year, 
            COUNT(*) as record_count,
            AVG(CAST(NULLIF(REGEXP_REPLACE(opening_stock, '[^0-9.]', '', 'g'), '') AS NUMERIC)) as avg_opening,
            AVG(CAST(NULLIF(REGEXP_REPLACE(closing_stock, '[^0-9.]', '', 'g'), '') AS NUMERIC)) as avg_closing
        FROM 
            cylinder_inventory
        GROUP BY 
            month, year
        ORDER BY 
            year, month
        """
        
        try:
            # Get total count
            total_count = self.execute_query(count_query, fetch=True)[0][0]
            
            # Get counts by type
            type_counts = self.execute_query(type_query, fetch=True)
            types = {row[0]: row[1] for row in type_counts}
            
            # Get daily counts for last 7 days
            daily_counts = self.execute_query(recent_query, fetch=True)
            
            daily_data = []
            for row in daily_counts:
                daily_data.append({
                    'date': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                    'count': row[1]
                })
            
            # Check if cylinder inventory table exists and get stats
            cylinder_stats = []
            try:
                cylinder_data = self.execute_query(cylinder_query, fetch=True)
                for row in cylinder_data:
                    cylinder_stats.append({
                        'month': row[0],
                        'year': row[1],
                        'record_count': row[2],
                        'avg_opening_stock': float(row[3]) if row[3] is not None else 0,
                        'avg_closing_stock': float(row[4]) if row[4] is not None else 0
                    })
            except Exception as cylinder_err:
                # Table might not exist yet, that's okay
                logger.warning(f"Could not retrieve cylinder stats: {str(cylinder_err)}")
            
            # Return compiled statistics
            stats = {
                'total_documents': total_count,
                'by_type': types,
                'daily_counts': daily_data
            }
            
            if cylinder_stats:
                stats['cylinder_stats'] = cylinder_stats
            
            return stats
        
        except Exception as e:
            logger.error(f"Error retrieving document statistics: {str(e)}")
            raise
    
    def get_cylinder_inventory_data(self, month=None, year=None, limit=100):
        """Get cylinder inventory data with optional month/year filter"""
        try:
            params = []
            query = """
            SELECT ci.*, dm.document_id, dm.created_at 
            FROM cylinder_inventory ci
            JOIN document_metadata dm ON ci.document_id = dm.document_id
            WHERE 1=1
            """
            
            if month:
                query += " AND ci.month = %s"
                params.append(month)
            
            if year:
                query += " AND ci.year = %s"
                params.append(year)
            
            query += " ORDER BY ci.year, ci.month, ci.date LIMIT %s"
            params.append(limit)
            
            rows = self.execute_query(query, tuple(params), fetch=True)
            
            inventory_data = []
            columns = ['id', 'document_id', 'date', 'month', 'year', 
                      'opening_stock', 'receipt', 'total_stock', 
                      'closing_stock', 'created_at', 'doc_id', 'doc_created_at']
            
            for row in rows:
                item = dict(zip(columns, row))
                # Convert datetime objects to strings
                for key in item:
                    if isinstance(item[key], datetime):
                        item[key] = item[key].isoformat()
                inventory_data.append(item)
            
            return inventory_data
            
        except Exception as e:
            logger.error(f"Error retrieving cylinder inventory data: {str(e)}")
            raise
