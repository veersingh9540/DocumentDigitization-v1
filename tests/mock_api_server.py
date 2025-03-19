import os
import json
import time
import psycopg2
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Mock S3 storage (for local testing)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'mock_uploads')
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), 'mock_processed')

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Database connection
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', 5432)
DB_NAME = os.environ.get('DB_NAME', 'documentdb')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

def get_db_connection():
    """Get a connection to the database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

# Mock document data
mock_documents = [
    {
        'document_id': 'mock-doc-001',
        'document_type': 'cylinder_inventory',
        'status': 'processed',
        'created_at': '2023-01-01T12:00:00'
    },
    {
        'document_id': 'mock-doc-002',
        'document_type': 'invoice',
        'status': 'processed',
        'created_at': '2023-01-02T12:00:00'
    }
]

mock_inventory_data = [
    {
        'date': '01/01/16',
        'month': 'Jan',
        'year': '2016',
        'opening_stock': '210',
        'receipt': '--',
        'total_stock': '210',
        'closing_stock': '108'
    },
    {
        'date': '02/01/16',
        'month': 'Jan',
        'year': '2016',
        'opening_stock': '108',
        'receipt': '270',
        'total_stock': '378',
        'closing_stock': '245'
    }
]

@app.route('/documents', methods=['GET'])
def get_documents():
    """Get list of documents"""
    conn = get_db_connection()
    try:
        if conn:
            # Try to get from database first
            cursor = conn.cursor()
            cursor.execute("""
                SELECT document_id, document_type, status, created_at
                FROM document_metadata
                ORDER BY created_at DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            
            if rows:
                documents = []
                for row in rows:
                    doc = {
                        'document_id': row[0],
                        'document_type': row[1],
                        'status': row[2],
                        'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else row[3]
                    }
                    documents.append(doc)
                return jsonify({'documents': documents})
    except Exception as e:
        print(f"Error getting documents from database: {str(e)}")
    
    # Fall back to mock data
    return jsonify({'documents': mock_documents})

@app.route('/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get a single document by ID"""
    conn = get_db_connection()
    try:
        if conn:
            # Try to get from database first
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM document_metadata WHERE document_id = %s
            """, (document_id,))
            metadata_row = cursor.fetchone()
            
            if metadata_row:
                # Get fields
                cursor.execute("""
                    SELECT field_name, field_value FROM document_fields 
                    WHERE document_id = %s
                """, (document_id,))
                fields_rows = cursor.fetchall()
                
                # Check for cylinder inventory data
                try:
                    cursor.execute("""
                        SELECT * FROM cylinder_inventory 
                        WHERE document_id = %s
                    """, (document_id,))
                    inventory_rows = cursor.fetchall()
                except:
                    inventory_rows = []
                
                # Format document data
                columns = ['id', 'document_id', 'original_bucket', 'original_key', 
                          'processed_bucket', 'processed_key', 'document_type', 
                          'page_count', 'status', 'created_at', 'updated_at']
                metadata_dict = dict(zip(columns, metadata_row))
                
                # Convert datetime objects to strings
                for key in metadata_dict:
                    if hasattr(metadata_dict[key], 'isoformat'):
                        metadata_dict[key] = metadata_dict[key].isoformat()
                
                # Convert fields to dictionary
                fields_dict = {field[0]: field[1] for field in fields_rows}
                
                result = {
                    'metadata': metadata_dict,
                    'fields': fields_dict
                }
                
                # Add inventory data if available
                if inventory_rows:
                    inventory_columns = ['id', 'document_id', 'date', 'month', 'year', 
                                        'opening_stock', 'receipt', 'total_stock', 
                                        'closing_stock', 'created_at']
                    
                    inventory_list = []
                    for row in inventory_rows:
                        inventory_item = dict(zip(inventory_columns, row))
                        # Convert datetime to string
                        if hasattr(inventory_item.get('created_at'), 'isoformat'):
                            inventory_item['created_at'] = inventory_item['created_at'].isoformat()
                        inventory_list.append(inventory_item)
                    
                    result['inventory_data'] = inventory_list
                
                return jsonify(result)
    except Exception as e:
        print(f"Error getting document from database: {str(e)}")
    
    # Fall back to mock data
    mock_document = {
        'metadata': {
            'document_id': document_id,
            'document_type': 'cylinder_inventory',
            'page_count': 3,
            'status': 'processed',
            'created_at': '2023-01-01T12:00:00'
        },
        'fields': {
            'title': 'Test Document'
        },
        'inventory_data': mock_inventory_data
    }
    
    return jsonify(mock_document)

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Get document statistics"""
    conn = get_db_connection()
    try:
        if conn:
            # Try to get from database first
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM document_metadata")
            total_count = cursor.fetchone()[0]
            
            # Get counts by type
            cursor.execute("""
                SELECT document_type, COUNT(*) 
                FROM document_metadata 
                GROUP BY document_type
            """)
            type_counts = cursor.fetchall()
            types = {row[0]: row[1] for row in type_counts}
            
            # Get daily counts
            cursor.execute("""
                SELECT DATE(created_at) as day, COUNT(*) 
                FROM document_metadata 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY day
                ORDER BY day
            """)
            daily_counts = cursor.fetchall()
            
            daily_data = []
            for row in daily_counts:
                daily_data.append({
                    'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    'count': row[1]
                })
            
            # Return statistics
            return jsonify({
                'total_documents': total_count,
                'by_type': types,
                'daily_counts': daily_data
            })
    except Exception as e:
        print(f"Error getting statistics from database: {str(e)}")
    
    # Fall back to mock data
    return jsonify({
        'total_documents': 42,
        'by_type': {
            'cylinder_inventory': 15,
            'invoice': 18,
            'contract': 5,
            'unknown': 4
        },
        'daily_counts': [
            {'date': '2023-01-01', 'count': 5},
            {'date': '2023-01-02', 'count': 7},
            {'date': '2023-01-03', 'count': 3},
            {'date': '2023-01-04', 'count': 8},
            {'date': '2023-01-05', 'count': 6},
            {'date': '2023-01-06', 'count': 7},
            {'date': '2023-01-07', 'count': 6}
        ]
    })

@app.route('/cylinder-inventory', methods=['GET'])
def get_cylinder_inventory():
    """Get cylinder inventory data"""
    # Get query parameters
    month = request.args.get('month')
    year = request.args.get('year')
    
    conn = get_db_connection()
    try:
        if conn:
            # Try to get from database first
            cursor = conn.cursor()
            
            # Build query based on filters
            query = """
                SELECT * FROM cylinder_inventory
                WHERE 1=1
            """
            params = []
            
            if month:
                query += " AND month = %s"
                params.append(month)
            
            if year:
                query += " AND year = %s"
                params.append(year)
            
            query += " ORDER BY year, month, date LIMIT 100"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if rows:
                columns = ['id', 'document_id', 'date', 'month', 'year', 
                          'opening_stock', 'receipt', 'total_stock', 
                          'closing_stock', 'created_at']
                
                inventory_data = []
                for row in rows:
                    item = dict(zip(columns, row))
                    # Convert datetime to string
                    if hasattr(item.get('created_at'), 'isoformat'):
                        item['created_at'] = item['created_at'].isoformat()
                    inventory_data.append(item)
                
                return jsonify({'inventory_data': inventory_data})
    except Exception as e:
        print(f"Error getting cylinder inventory from database: {str(e)}")
    
    # Filter mock data if needed
    filtered_data = mock_inventory_data
    if month:
        filtered_data = [item for item in filtered_data if item['month'] == month]
    if year:
        filtered_data = [item for item in filtered_data if item['year'] == year]
    
    return jsonify({'inventory_data': filtered_data})

@app.route('/upload-url', methods=['GET'])
def get_upload_url():
    """Get a signed URL for uploading files"""
    file_name = request.args.get('fileName')
    file_type = request.args.get('fileType')
    
    if not file_name or not file_type:
        return jsonify({'error': 'Missing required parameters: fileName, fileType'}), 400
    
    # Generate a mock signed URL (for local testing)
    object_key = f"uploads/{secure_filename(file_name)}"
    signed_url = f"http://localhost:5000/mock-upload/{object_key}"
    
    return jsonify({
        'signedUrl': signed_url,
        'objectKey': object_key,
        'bucket': 'mock-bucket'
    })

@app.route('/mock-upload/<path:object_key>', methods=['PUT'])
def mock_upload(object_key):
    """Handle mock uploads (for local testing)"""
    try:
        # Save the file locally
        file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(object_key))
        with open(file_path, 'wb') as f:
            f.write(request.data)
        
        # Generate a document ID
        document_id = f"{os.path.splitext(os.path.basename(object_key))[0]}-{uuid.uuid4().hex[:8]}"
        
        # Mock processing delay
        time.sleep(1)
        
        # Create mock processed data
        processed_data = {
            'document_id': document_id,
            'document_type': 'cylinder_inventory',
            'page_count': 3,
            'extracted_fields': mock_inventory_data,
            'full_text': 'Jan. 2016 14.2 kg DNSC FILLED CYLINDERS EMPTY CYLINDERS'
        }
        
        # Save processed data
        processed_file = os.path.join(PROCESSED_FOLDER, f"{document_id}.json")
        with open(processed_file, 'w') as f:
            json.dump(processed_data, f)
        
        # Insert into mock database
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Insert document metadata
                cursor.execute("""
                    INSERT INTO document_metadata (
                        document_id, original_bucket, original_key, 
                        processed_bucket, processed_key, document_type, 
                        page_count, status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    document_id,
                    'mock-bucket',
                    object_key,
                    'mock-bucket',
                    f"processed/{document_id}.json",
                    'cylinder_inventory',
                    3,
                    'processed'
                ))
                
                # Insert cylinder inventory data
                for item in mock_inventory_data:
                    cursor.execute("""
                        INSERT INTO cylinder_inventory (
                            document_id, date, month, year,
                            opening_stock, receipt, total_stock, closing_stock,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        document_id,
                        item['date'],
                        item['month'],
                        item['year'],
                        item['opening_stock'],
                        item['receipt'],
                        item['total_stock'],
                        item['closing_stock']
                    ))
                
                conn.commit()
                print(f"Inserted mock data for document {document_id}")
            except Exception as e:
                conn.rollback()
                print(f"Error inserting mock data: {str(e)}")
        
        return "", 200
    except Exception as e:
        print(f"Error handling mock upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting mock API server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
