# src/lambda/document_processor/textract_helper.py
import boto3
import time
import os
import re
from collections import defaultdict

def process_document(document_path):
    """
    Process document using AWS Textract and extract text and table data
    
    Args:
        document_path: Path to the document file
        
    Returns:
        tuple: (raw_text, table_data)
    """
    # Read document content
    with open(document_path, 'rb') as document:
        document_bytes = document.read()
    
    # Get the file extension
    _, file_extension = os.path.splitext(document_path)
    file_extension = file_extension.lower()
    
    # Create Textract client
    textract = boto3.client('textract')
    
    # Process document based on type
    if file_extension in ['.png', '.jpg', '.jpeg']:
        response = textract.analyze_document(
            Document={'Bytes': document_bytes},
            FeatureTypes=['TABLES']
        )
        return extract_text_and_tables(response)
    elif file_extension == '.pdf':
        # For PDFs, we need to use async operations for multi-page documents
        return process_pdf_document(document_bytes, textract)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def process_pdf_document(document_bytes, textract):
    """Process PDF document using async Textract operations"""
    # Start document analysis job
    response = textract.start_document_analysis(
        DocumentLocation={'Bytes': document_bytes},
        FeatureTypes=['TABLES']
    )
    
    job_id = response['JobId']
    
    # Wait for the job to complete
    status = 'IN_PROGRESS'
    while status == 'IN_PROGRESS':
        time.sleep(5)
        response = textract.get_document_analysis(JobId=job_id)
        status = response['JobStatus']
        
        if status == 'FAILED':
            raise Exception("Textract analysis job failed")
    
    # Collect all pages of results
    pages = []
    next_token = None
    
    while True:
        if next_token:
            response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
        else:
            response = textract.get_document_analysis(JobId=job_id)
            
        pages.append(response)
        
        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break
    
    # Combine results from all pages
    all_blocks = []
    for page in pages:
        all_blocks.extend(page['Blocks'])
        
    # Create a mock response with all blocks
    mock_response = {'Blocks': all_blocks}
    
    return extract_text_and_tables(mock_response)

def extract_text_and_tables(response):
    """Extract text and tables from Textract response"""
    # Extract raw text
    raw_text = ""
    for item in response['Blocks']:
        if item['BlockType'] == 'LINE':
            raw_text += item['Text'] + "\n"
    
    # Extract tables
    tables = []
    
    # Get all blocks
    blocks = response['Blocks']
    
    # Find all tables
    table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
    
    for table_block in table_blocks:
        table_id = table_block['Id']
        
        # Find all cells in this table
        cell_blocks = [block for block in blocks if 
                      block['BlockType'] == 'CELL' and 
                      'EntityTypes' not in block and
                      block.get('TableId') == table_id]
        
        # Get the dimensions of the table
        max_row = max([cell['RowIndex'] for cell in cell_blocks]) if cell_blocks else 0
        max_col = max([cell['ColumnIndex'] for cell in cell_blocks]) if cell_blocks else 0
        
        # Initialize table as 2D list filled with None
        table = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]
        
        # Fill in table with cell data
        for cell in cell_blocks:
            row_idx = cell['RowIndex'] - 1  # Convert to 0-indexed
            col_idx = cell['ColumnIndex'] - 1  # Convert to 0-indexed
            
            # Find all word blocks for this cell
            cell_content = ""
            for relationship in cell.get('Relationships', []):
                if relationship['Type'] == 'CHILD':
                    child_ids = relationship['Ids']
                    word_blocks = [block for block in blocks if 
                                  block['Id'] in child_ids and
                                  block['BlockType'] in ['WORD', 'LINE']]
                    
                    for word_block in word_blocks:
                        if cell_content:
                            cell_content += " "
                        cell_content += word_block['Text']
            
            # Set cell content in table
            if cell_content:
                # Try to convert to number if possible
                if cell_content.strip().replace('.', '', 1).isdigit():
                    try:
                        cell_content = float(cell_content)
                        # Convert to int if it's a whole number
                        if cell_content.is_integer():
                            cell_content = int(cell_content)
                    except ValueError:
                        pass
                
            table[row_idx][col_idx] = cell_content
        
        tables.append(table)
    
    # Combine all tables into a single 2D list
    combined_table = []
    for table in tables:
        combined_table.extend(table)
    
    return raw_text, combined_table

def extract_cylinder_table(table_data):
    """Extract cylinder data from table format"""
    # Filter out empty rows
    non_empty_rows = []
    
    for row in table_data:
        if any(cell is not None and str(cell).strip() for cell in row):
            non_empty_rows.append(row)
    
    return non_empty_rows
