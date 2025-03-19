import json
import os
import boto3
import logging
import base64
from urllib.parse import unquote_plus
from ocr_processor import process_document
from db_connector import DatabaseConnector

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
secretsmanager_client = boto3.client('secretsmanager')

# Environment variables
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
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

def lambda_handler(event, context):
    """
    Lambda function handler for processing document uploads to S3
    """
    logger.info("Document processing started")
    
    try:
        # Extract bucket and key from event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing document: s3://{bucket}/{key}")
            
            # Download the file from S3
            download_path = f"/tmp/{os.path.basename(key)}"
            s3_client.download_file(bucket, key, download_path)
            
            # Process the document using OCR
            document_data = process_document(download_path)
            
            # Create a unique document ID
            document_id = f"{os.path.splitext(os.path.basename(key))[0]}-{context.aws_request_id[:8]}"
            
            # Save processed data to S3
            output_key = f"processed/{document_id}.json"
            s3_client.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=json.dumps(document_data, default=str),
                ContentType='application/json'
            )
            
            # Save to database
            db_credentials = get_db_credentials()
            db = DatabaseConnector(**db_credentials)
            
            # Insert document metadata
            metadata = {
                'document_id': document_id,
                'original_bucket': bucket,
                'original_key': key,
                'processed_bucket': OUTPUT_BUCKET,
                'processed_key': output_key,
                'document_type': document_data.get('document_type', 'unknown'),
                'page_count': document_data.get('page_count', 0),
                'status': 'processed'
            }
            
            db.insert_document_metadata(metadata)
            
            # Insert extracted fields
            if 'extracted_fields' in document_data:
                db.insert_document_fields(document_id, document_data['extracted_fields'])
            
            # Clean up local file
            os.remove(download_path)
            
            logger.info(f"Document processed successfully: {document_id}")
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document processing completed successfully'
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing document',
                'error': str(e)
            })
        }
