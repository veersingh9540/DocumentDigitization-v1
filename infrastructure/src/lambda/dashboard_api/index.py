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
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', 'document-processing-documents-dev')

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
        # For demo purposes, return mock data
        return build_response(200, {
            'metadata': {
                'document_id': document_id,
                'document_type': 'cylinder_inventory',
                'page_count': 3,
                'status': 'processed',
                'created_at': '2023-01-01T12:00:00'
            },
            'fields': {},
            'inventory_data': [
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
        })
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_recent_documents(db, limit=10):
    """Retrieve a list of recent documents"""
    try:
        # For demo purposes, return mock data
        return build_response(200, {
            'documents': [
                {
                    'document_id': 'mock-doc-001',
                    'document_type': 'cylinder_inventory',
                    'status': 'processed',
                    'created_at': '2023-01-01T12:00:00'
                }
            ]
        })
    except Exception as e:
        logger.error(f"Error retrieving recent documents: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_document_statistics(db):
    """Get statistics about processed documents"""
    try:
        # For demo purposes, return mock data
        return build_response(200, {
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
    except Exception as e:
        logger.error(f"Error retrieving document statistics: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def get_cylinder_inventory(db, month=None, year=None):
    """Get cylinder inventory data"""
    try:
        # For demo purposes, return mock data
        return build_response(200, {
            'inventory_data': [
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
        })
    except Exception as e:
        logger.error(f"Error retrieving cylinder inventory: {str(e)}")
        return build_response(500, {'error': 'Internal server error'})

def create_signed_upload_url(file_name, file_type):
    """Create a signed URL for direct S3 upload"""
    try:
        s3_key = f"uploads/{file_name}"
        
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET,
                'Key': s3_key,
                'ContentType': file_type
            },
            ExpiresIn=300
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
    """Lambda function handler for dashboard API"""
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
                return get_recent_documents(db, limit)
            
            elif path == '/documents/{document_id}' or (path == '/documents' and document_id is not None):
                return get_document(db, document_id)
            
            elif path == '/statistics':
                return get_document_statistics(db)
            
            elif path == '/cylinder-inventory':
                month = query_params.get('month')
                year = query_params.get('year')
                return get_cylinder_inventory(db, month, year)
            
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
