import os
import boto3
import logging
import json
import io
import PyPDF2
import pytesseract
from PIL import Image
import pdf2image
import re
import pandas as pd
import numpy as np
from tabula import read_pdf

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS textract client
textract = boto3.client('textract')

def extract_text_from_pdf_textract(file_path):
    """Extract text from PDF using AWS Textract"""
    with open(file_path, 'rb') as file:
        file_bytes = file.read()
    
    # Use Textract's analyze_document with TABLES feature type to detect tables
    response = textract.analyze_document(
        Document={'Bytes': file_bytes},
        FeatureTypes=['TABLES']
    )
    
    # Process detected tables and text
    text = ""
    tables = []
    
    # Extract all blocks
    blocks = response['Blocks']
    
    # Extract table structures
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + "\n"
        
        # Process tables
        if block['BlockType'] == 'TABLE':
            table_data = extract_table_from_textract(blocks, block['Id'])
            tables.append(table_data)
    
    return {
        'text': text,
        'tables': tables
    }

def extract_table_from_textract(blocks, table_id):
    """Extract table data from Textract blocks"""
    cells = {}
    table_data = []
    
    # Get all cells belonging to this table
    for block in blocks:
        if block['BlockType'] == 'CELL' and block.get('TableId') == table_id:
            row_index = block['RowIndex'] - 1  # 0-based indexing
            col_index = block['ColumnIndex'] - 1  # 0-based indexing
            
            # Get cell content
            cell_content = ""
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            child_block = next((b for b in blocks if b['Id'] == child_id), None)
                            if child_block and child_block['BlockType'] == 'WORD':
                                cell_content += child_block['Text'] + " "
            
            cells[(row_index, col_index)] = cell_content.strip()
    
    # Find table dimensions
    max_row = max([k[0] for k in cells.keys()]) if cells else 0
    max_col = max([k[1] for k in cells.keys()]) if cells else 0
    
    # Create table data
    for row_idx in range(max_row + 1):
        row_data = []
        for col_idx in range(max_col + 1):
            row_data.append(cells.get((row_idx, col_idx), ""))
        table_data.append(row_data)
    
    return table_data

def extract_tables_with_tabula(file_path):
    """Extract tables from PDF using Tabula"""
    try:
        # Try to extract tables automatically
        tables = read_pdf(file_path, pages='all', multiple_tables=True)
        
        # Convert tables to list of lists format
        processed_tables = []
        for table in tables:
            # Convert any NaN values to empty strings
            table = table.fillna('')
            # Convert DataFrame to list of lists
            table_data = table.values.tolist()
            # Add header if it exists
            if not table.columns.str.contains('^Unnamed').all():
                header = table.columns.tolist()
                table_data.insert(0, header)
            processed_tables.append(table_data)
        
        return processed_tables
    except Exception as e:
        logger.error(f"Error extracting tables with Tabula: {str(e)}")
        return []

def extract_text_from_pdf_tesseract(file_path):
    """Extract text from PDF using pytesseract (fallback)"""
    text = ""
    try:
        # Convert PDF to images
        pages = pdf2image.convert_from_path(file_path, dpi=300)
        
        for i, page in enumerate(pages):
            text += f"\n--- Page {i+1} ---\n"
            text += pytesseract.image_to_string(page)
    
    except Exception as e:
        logger.error(f"Error in tesseract OCR: {str(e)}")
    
    return text

def extract_cylinder_inventory_data(tables, text):
    """Extract specific cylinder inventory data from tables"""
    inventory_data = []
    
    # Check if we have any tables
    if not tables:
        logger.warning("No tables detected in the document")
        return inventory_data
    
    # Try to identify the cylinder inventory table
    for table in tables:
        # Skip empty tables
        if not table or len(table) <= 1:
            continue
        
        # Check if this looks like a cylinder inventory table
        header_row = table[0] if table else []
        header_text = ' '.join([str(h).lower() for h in header_row])
        
        if 'cylinder' in header_text or 'filled' in header_text or 'empty' in header_text:
            # This looks like our inventory table
            
            # Extract month and year from the document text
            month_year_match = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})', 
                                         text.lower())
            month = month_year_match.group(1)[:3].capitalize() if month_year_match else "Unknown"
            year = month_year_match.group(2) if month_year_match else "Unknown"
            
            # Process each row (skip header)
            for row in table[1:]:
                # Skip rows with insufficient data
                if len(row) < 5:
                    continue
                
                # Try to extract date and inventory data
                try:
                    # First column usually contains the date
                    date_cell = str(row[0]).strip()
                    
                    # Extract numeric values where possible
                    numeric_values = []
                    for cell in row[1:]:
                        cell_str = str(cell).strip()
                        # Try to extract numbers
                        number_match = re.search(r'(\d+(?:\.\d+)?)', cell_str)
                        if number_match:
                            numeric_values.append(number_match.group(1))
                        else:
                            numeric_values.append("")
                    
                    # Create inventory record
                    inventory_record = {
                        'date': date_cell,
                        'month': month,
                        'year': year,
                        'values': numeric_values
                    }
                    
                    inventory_data.append(inventory_record)
                except Exception as e:
                    logger.warning(f"Error processing row: {str(e)}")
                    continue
    
    return inventory_data

def get_pdf_metadata(file_path):
    """Extract metadata from PDF"""
    metadata = {}
    try:
        with open(file_path, 'rb') as file:
            pdf = PyPDF2.PdfReader(file)
            metadata = {
                'page_count': len(pdf.pages),
                'title': None,
                'author': None,
                'creator': None,
                'producer': None,
                'subject': None,
                'creation_date': None
            }
            
            if pdf.metadata:
                for key in metadata.keys():
                    if key in pdf.metadata and key != 'page_count':
                        metadata[key] = pdf.metadata[key]
    
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {str(e)}")
    
    return metadata

def identify_document_type(text, tables):
    """Identify the type of document based on its content"""
    text_lower = text.lower()
    
    # Check for cylinder inventory keywords
    if 'cylinder' in text_lower or 'filled' in text_lower or 'empty' in text_lower:
        if tables and len(tables) > 0:
            return "cylinder_inventory"
    
    # Check for other document types
    if "invoice" in text_lower or "bill" in text_lower:
        return "invoice"
    elif "receipt" in text_lower:
        return "receipt"
    elif "contract" in text_lower or "agreement" in text_lower:
        return "contract"
    elif "report" in text_lower:
        return "report"
    
    # Default to unknown
    return "unknown"

def extract_fields_by_document_type(text, tables, document_type):
    """Extract fields based on document type"""
    if document_type == "cylinder_inventory":
        return extract_cylinder_inventory_data(tables, text)
    elif document_type == "invoice":
        return extract_fields_from_invoice(text)
    # Add more document type handlers here
    else:
        return {}

def extract_fields_from_invoice(text):
    """Extract relevant fields from invoice text"""
    fields = {}
    
    # Extract invoice number
    invoice_match = re.search(r'invoice\s*(?:#|number|num|no|no\.)\s*[:]?\s*([a-z0-9\-]+)', text.lower())
    if invoice_match:
        fields['invoice_number'] = invoice_match.group(1)
    
    # Extract date
    date_match = re.search(r'(?:date|issued|invoice date)[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text.lower())
    if date_match:
        fields['date'] = date_match.group(1)
    
    # Extract amount
    amount_match = re.search(r'(?:total|amount|sum)[:\s]*[$€£]?\s*(\d+[,\.]?\d*)', text.lower())
    if amount_match:
        fields['total_amount'] = amount_match.group(1).replace(',', '')
    
    # Extract vendor/seller
    vendor_match = re.search(r'(?:from|seller|vendor|company|billed from)[:\s]*([a-z0-9\s]+(?:inc|llc|corp|ltd)?)', text.lower())
    if vendor_match:
        fields['vendor'] = vendor_match.group(1).strip()
    
    return fields

def process_document(file_path):
    """Process a document and extract text, metadata, and structured information"""
    logger.info(f"Processing document: {file_path}")
    
    result = {}
    
    try:
        # Extract PDF metadata
        metadata = get_pdf_metadata(file_path)
        result.update(metadata)
        
        # Try table extraction with Tabula first
        tables = extract_tables_with_tabula(file_path)
        
        # If tabula didn't work well, try AWS Textract
        if not tables or len(tables) == 0:
            logger.info("No tables detected with Tabula, trying Textract")
            try:
                textract_result = extract_text_from_pdf_textract(file_path)
                extracted_text = textract_result.get('text', '')
                tables = textract_result.get('tables', [])
            except Exception as e:
                logger.warning(f"Textract extraction failed, falling back to tesseract: {str(e)}")
                extracted_text = extract_text_from_pdf_tesseract(file_path)
        else:
            # Extract full text for better context
            extracted_text = extract_text_from_pdf_tesseract(file_path)
        
        # Identify document type
        document_type = identify_document_type(extracted_text, tables)
        result['document_type'] = document_type
        
        # Extract fields based on document type
        extracted_fields = extract_fields_by_document_type(extracted_text, tables, document_type)
        result['extracted_fields'] = extracted_fields
        
        # Add the full extracted text
        result['full_text'] = extracted_text
        
        # Add tables data
        result['tables'] = tables
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise
