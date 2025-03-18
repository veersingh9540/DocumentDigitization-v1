import boto3
import time
import logging
import json
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
textract_client = boto3.client('textract')
s3_client = boto3.client('s3')

def process_document(bucket, key):
    """
    Process a document stored in S3 using AWS Textract.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        tuple: (extracted_text, table_data)
    """
    logger.info(f"Processing document: s3://{bucket}/{key}")
    
    # Determine file type
    file_extension = os.path.splitext(key)[1].lower()
    
    if file_extension == '.pdf':
        # Handle PDF documents with asynchronous API
        return process_pdf(bucket, key)
    else:
        # Handle image documents with synchronous API
        return process_image(bucket, key)

def process_pdf(bucket, key):
    """
    Process a PDF document using asynchronous Textract API.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        tuple: (extracted_text, table_data)
    """
    try:
        # Start document analysis job
        response = textract_client.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        job_id = response['JobId']
        logger.info(f"Started Textract analysis job with ID: {job_id}")
        
        # Wait for job to complete
        status = 'IN_PROGRESS'
        max_retries = 60  # 5 minutes maximum wait time
        retry_count = 0
        
        while status == 'IN_PROGRESS' and retry_count < max_retries:
            time.sleep(5)  # Wait 5 seconds between checks
            retry_count += 1
            
            get_response = textract_client.get_document_analysis(JobId=job_id)
            status = get_response['JobStatus']
            
            logger.info(f"Job status: {status}, retry {retry_count}/{max_retries}")
            
            if status == 'SUCCEEDED':
                # Process results
                return extract_text_and_tables(get_response, job_id)
            elif status == 'FAILED':
                error_message = get_response.get('StatusMessage', 'No status message provided')
                logger.error(f"Textract job failed: {error_message}")
                raise Exception(f"Textract job failed: {error_message}")
        
        if status == 'IN_PROGRESS':
            logger.error("Textract job timeout")
            raise Exception("Textract job timeout")
        
    except Exception as e:
        logger.error(f"Error in process_pdf: {str(e)}", exc_info=True)
        # Return empty results in case of error
        return "", []

def process_image(bucket, key):
    """
    Process an image document using synchronous Textract API.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        tuple: (extracted_text, table_data)
    """
    try:
        # Call Textract to analyze the document
        response = textract_client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        # Extract text and tables from response
        text, tables = extract_text_and_tables_from_single_response(response)
        
        return text, tables
        
    except Exception as e:
        logger.error(f"Error in process_image: {str(e)}", exc_info=True)
        # Return empty results in case of error
        return "", []

def extract_text_and_tables(initial_response, job_id):
    """
    Extract text and tables from a document analysis job result.
    
    Args:
        initial_response (dict): Initial get_document_analysis response
        job_id (str): Textract job ID
        
    Returns:
        tuple: (extracted_text, table_data)
    """
    try:
        blocks = initial_response['Blocks']
        next_token = initial_response.get('NextToken')
        
        # Get all pages if there are more
        while next_token:
            response = textract_client.get_document_analysis(
                JobId=job_id,
                NextToken=next_token
            )
            blocks.extend(response['Blocks'])
            next_token = response.get('NextToken')
        
        # Extract text
        text = ""
        for block in blocks:
            if block['BlockType'] == 'LINE':
                text += block['Text'] + "\n"
        
        # Extract tables
        tables = extract_tables_from_blocks(blocks)
        
        return text, tables
        
    except Exception as e:
        logger.error(f"Error in extract_text_and_tables: {str(e)}", exc_info=True)
        return "", []

def extract_text_and_tables_from_single_response(response):
    """
    Extract text and tables from a single analyze_document response.
    
    Args:
        response (dict): analyze_document response
        
    Returns:
        tuple: (extracted_text, table_data)
    """
    try:
        blocks = response['Blocks']
        
        # Extract text
        text = ""
        for block in blocks:
            if block['BlockType'] == 'LINE':
                text += block['Text'] + "\n"
        
        # Extract tables
        tables = extract_tables_from_blocks(blocks)
        
        return text, tables
        
    except Exception as e:
        logger.error(f"Error in extract_text_and_tables_from_single_response: {str(e)}", exc_info=True)
        return "", []

def extract_tables_from_blocks(blocks):
    """
    Extract tables from Textract blocks.
    
    Args:
        blocks (list): List of Textract blocks
        
    Returns:
        list: List of tables
    """
    # Map block IDs to blocks for easy lookup
    block_map = {block['Id']: block for block in blocks}
    
    # Find all tables
    tables = []
    tables_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
    
    for table_block in tables_blocks:
        table_id = table_block['Id']
        
        # Get all cells for this table
        cells = [block for block in blocks if block['BlockType'] == 'CELL' and 
                 'Relationships' in block and 
                 any(rel['Type'] == 'TABLE' and table_id in rel['Ids'] for rel in block['Relationships'])]
        
        # Determine table dimensions
        rows = max(cell['RowIndex'] for cell in cells) if cells else 0
        cols = max(cell['ColumnIndex'] for cell in cells) if cells else 0
        
        if rows == 0 or cols == 0:
            continue
        
        # Initialize empty table
        table = [[''] * cols for _ in range(rows)]
        
        # Fill in cell values
        for cell in cells:
            row_idx = cell['RowIndex'] - 1  # Convert to 0-based index
            col_idx = cell['ColumnIndex'] - 1  # Convert to 0-based index
            
            # Extract text from cell
            cell_text = ""
            if 'Relationships' in cell and any(rel['Type'] == 'CHILD' for rel in cell['Relationships']):
                # Get all child blocks
                for rel in cell['Relationships']:
                    if rel['Type'] == 'CHILD':
                        for child_id in rel['Ids']:
                            child_block = block_map.get(child_id)
                            if child_block and child_block['BlockType'] == 'WORD':
                                cell_text += child_block['Text'] + " "
            
            # Set cell value
            if row_idx < len(table) and col_idx < len(table[row_idx]):
                table[row_idx][col_idx] = cell_text.strip()
        
        # Add table to results
        tables.append(table)
    
    return tables
