import json
import os
import boto3
import logging
import urllib.parse
from datetime import datetime
import uuid
import traceback
import textract_helper
import ocr_helper
import db_helper
import pdf_extractor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
comprehend_client = boto3.client('comprehend')

# Get environment variables
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME')
DB_NAME = os.environ.get('DB_NAME', 'dashboard')

def lambda_handler(event, context):
    """
    Main Lambda handler function for processing documents uploaded to S3.
    
    Args:
        event (dict): Event data from S3 trigger
        context (object): Lambda context
        
    Returns:
        dict: Response containing processing results
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract bucket and key from the S3 event
        if 'Records' in event:
            # This is an S3 event
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        elif 'detail' in event and 'requestParameters' in event['detail']:
            # This is an EventBridge event
            bucket = event['detail']['requestParameters']['bucketName']
            key = event['detail']['requestParameters']['key']
        else:
            logger.error("Unsupported event format")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Unsupported event format',
                    'event_received': event
                })
            }
        
        logger.info(f"Processing file {key} from bucket {bucket}")
        
        # Extract file information
        file_name = os.path.basename(key)
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Process based on file type
        if file_extension in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']:
            # For PDF files, use our specialized PDF extractor for cylinder logs
            if file_extension == '.pdf' and ('cylinder' in file_name.lower() or 'log' in file_name.lower()):
                try:
                    # Use specialized PDF extractor for cylinder logs
                    cylinder_data = pdf_extractor.process_cylinder_pdf(bucket, key)
                    
                    # Process was successful, save to database
                    document_data = {
                        'document_id': document_id,
                        'file_name': file_name,
                        'bucket': bucket,
                        'key': key,
                        'processed_date': datetime.now().isoformat(),
                        'extracted_text': json.dumps(cylinder_data),
                        'table_data': [],
                        'form_data': [],
                        'entities': [],
                        'key_phrases': []
                    }
                    
                    # Save document metadata to the database
                    db_helper.save_document(document_data)
                    
                    # Save cylinder logs to the database
                    db_helper.save_cylinder_logs(document_id, cylinder_data)
                    
                    # Save processed data to output bucket
                    if OUTPUT_BUCKET:
                        output_key = f"processed/{document_id}/result.json"
                        s3_client.put_object(
                            Bucket=OUTPUT_BUCKET,
                            Key=output_key,
                            Body=json.dumps(cylinder_data, indent=2),
                            ContentType='application/json'
                        )
                        logger.info(f"Saved processed data to {OUTPUT_BUCKET}/{output_key}")
                    
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Document processed successfully as cylinder log',
                            'document_id': document_id,
                            'file_name': file_name
                        })
                    }
                except Exception as e:
                    logger.error(f"Error processing cylinder log PDF: {str(e)}", exc_info=True)
                    logger.info("Falling back to standard document processing")
                    # Fall back to standard processing
            
            # Standard document processing with Textract
            extracted_text, table_data = textract_helper.process_document(bucket, key)
            
            # Process extracted text with OCR helper
            processed_data = ocr_helper.process_cylinder_logs(extracted_text, table_data)
            
            # Save document metadata to the database
            document_data = {
                'document_id': document_id,
                'file_name': file_name,
                'bucket': bucket,
                'key': key,
                'processed_date': datetime.now().isoformat(),
                'extracted_text': extracted_text,
                'table_data': table_data,
                'form_data': [],
                'entities': [],
                'key_phrases': []
            }
            
            # Save document to the database
            db_helper.save_document(document_data)
            
            # Save cylinder logs to the database if applicable
            if isinstance(processed_data, dict) and 'month_year' in processed_data:
                db_helper.save_cylinder_logs(document_id, processed_data)
            
            # Save processed data to output bucket
            if OUTPUT_BUCKET:
                # Save extracted text
                s3_client.put_object(
                    Bucket=OUTPUT_BUCKET,
                    Key=f"processed/{document_id}/text.txt",
                    Body=extracted_text,
                    ContentType='text/plain'
                )
                
                # Save processed data
                s3_client.put_object(
                    Bucket=OUTPUT_BUCKET,
                    Key=f"processed/{document_id}/data.json",
                    Body=json.dumps(processed_data, indent=2),
                    ContentType='application/json'
                )
                
                logger.info(f"Saved processed data to {OUTPUT_BUCKET}/processed/{document_id}/")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Document processed successfully',
                    'document_id': document_id,
                    'file_name': file_name
                })
            }
        else:
            logger.warning(f"Unsupported file format: {file_extension}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': f'Unsupported file format: {file_extension}',
                    'supported_formats': ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']
                })
            }
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing document',
                'error': str(e)
            })
        }

# Initialize the database when the Lambda is first loaded
try:
    db_helper.create_tables()
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
