import json
import os
import boto3
import logging
from db_connector import DatabaseConnector

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager_client = boto3.client('secretsmanager')
s3_client = boto3.client('s3')

# Environment variables
DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME')
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET')

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

def build_response(status_code, body):
    """Build a standardized API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body, default=str)
    }

def get_document(db, document_id):
    """Retrieve a single document by ID"""
    try:
        document = db.get_document_by_id(document_id)
        
        if document:
            return build_response(200, document)
        else:
            return build_response(404, {'error': 'Document not found'})
    
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_recent_documents(db, limit=10):
    """Retrieve a list of recent documents"""
    try:
        documents = db.get_recent_documents(int(limit))
        return build_response(200, {'documents': documents})
    
    except Exception as e:
        logger.error(f"Error retrieving recent documents: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def search_documents(db, query_text, limit=20):
    """Search for documents"""
    try:
        documents = db.search_documents(query_text, int(limit))
        return build_response(200, {'documents': documents})
    
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_document_statistics(db):
    """Get statistics about processed documents"""
    try:
        stats = db.get_document_statistics()
        return build_response(200, stats)
    
    except Exception as e:
        logger.error(f"Error retrieving document statistics: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_cylinder_inventory(db, month=None, year=None, limit=100):
    """Get cylinder inventory data"""
    try:
        inventory_data = db.get_cylinder_inventory_data(month, year, limit)
        return build_response(200, {'inventory_data': inventory_data})
    
    except Exception as e:
        logger.error(f"Error retrieving cylinder inventory: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def create_signed_upload_url(file_name, file_type):
    """Create a signed URL for direct S3 upload"""
    try:
        # Generate unique S3 key
        s3_key = f"uploads/{file_name}"
        
        # Generate presigned URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': s3_key,
                'ContentType': file_type
            },
            ExpiresIn=300  # URL expires in 5 minutes
        )
        
        return build_response(200, {
            'signedUrl': presigned_url,
            'objectKey': s3_key,
            'bucket': UPLOAD_BUCKET
        })
    
    except Exception as e:
        logger.error(f"Error generating signed URL: {str(e)}")
        return build_response(500, {'error': 'Error generating upload URL'})

def handle_options_request():
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': ''
    }

def lambda_handler(event, context):
    """
    Lambda function handler for dashboard API
    
    Routes:
    - GET /documents                     -> List recent documents
    - GET /documents/{document_id}       -> Get document details
    - GET /documents/search?q=query      -> Search documents
    - GET /statistics                    -> Get document statistics
    - GET /cylinder-inventory            -> Get cylinder inventory data
    - GET /upload-url                    -> Get signed URL for S3 upload
    """
    logger.info(f"API request: {json.dumps(event)}")
    
    # Handle CORS preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return handle_options_request()
    
    try:
        # Get database connection
        db_credentials = get_db_credentials()
        db = DatabaseConnector(**db_credentials)
        
        # Parse request
        path = event.get('path', '').rstrip('/')
        http_method = event.get('httpMethod', '')
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Extract path parameters
        path_params = event.get('pathParameters', {}) or {}
        document_id = path_params.get('document_id')
        
        # Routing logic
        if http_method == 'GET':
            if path == '/documents' and document_id is None:
                limit = query_params.get('limit', '10')
                query = query_params.get('q')
                
                if query:
                    return search_documents(db, query, limit)
                else:
                    return get_recent_documents(db, limit)
            
            elif path == '/documents/{document_id}' or (path == '/documents' and document_id is not None):
                return get_document(db, document_id)
            
            elif path == '/statistics':
                return get_document_statistics(db)
            
            elif path == '/cylinder-inventory':
                month = query_params.get('month')
                year = query_params.get('year')
                limit = query_params.get('limit', '100')
                return get_cylinder_inventory(db, month, year, int(limit))
            
            elif path == '/upload-url':
                file_name = query_params.get('fileName')
                file_type = query_params.get('fileType')
                
                if not file_name or not file_type:
                    return build_response(400, {'error': 'Missing required parameters: fileName, fileType'})
                
                return create_signed_upload_url(file_name, file_type)
        
        # Close database connection
        db.close()
        
        # If no route matched
        return build_response(404, {'error': 'Route not found'})
    
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})
