import boto3
import os
import json
import re
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import io

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')

def process_cylinder_pdf(bucket, key):
    """
    Main function to process cylinder logs PDF.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        dict: Extracted data from the PDF
    """
    logger.info(f"Processing cylinder logs PDF: s3://{bucket}/{key}")
    
    try:
        # Extract the month and year from the filename or metadata if available
        file_name = os.path.basename(key)
        month_year = extract_date_from_filename(file_name)
        
        # Submit the PDF to Textract for analysis
        textract_result = extract_text_from_pdf(bucket, key)
        
        # Process the Textract result
        processed_data = process_textract_result(textract_result, month_year)
        
        return processed_data
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise

def extract_date_from_filename(file_name):
    """
    Extract date information from the filename.
    
    Args:
        file_name (str): Name of the file
        
    Returns:
        str: Month and year (e.g., "Jan 2016")
    """
    # Try to match common date patterns in the filename
    # Pattern for "month_year" or "month-year"
    pattern1 = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[_\-\.](20\d{2})'
    match = re.search(pattern1, file_name.lower())
    
    if match:
        month_map = {
            'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 
            'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'aug': 'Aug', 
            'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
        }
        month = month_map.get(match.group(1), match.group(1).capitalize())
        year = match.group(2)
        return f"{month} {year}"
    
    # Pattern for dates in format "YYYY-MM" or "YYYY_MM"
    pattern2 = r'(20\d{2})[_\-\.](\d{1,2})'
    match = re.search(pattern2, file_name)
    
    if match:
        month_map = {
            '1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', 
            '5': 'May', '6': 'Jun', '7': 'Jul', '8': 'Aug', 
            '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec',
            '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', 
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug', 
            '09': 'Sep'
        }
        year = match.group(1)
        month = month_map.get(match.group(2), f"Month {match.group(2)}")
        return f"{month} {year}"
    
    # Look for month patterns in the file name
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    for month in months:
        if month in file_name.lower():
            # Look for a year pattern near the month
            year_pattern = r'(20\d{2})'
            year_match = re.search(year_pattern, file_name)
            if year_match:
                year = year_match.group(1)
                return f"{month.capitalize()} {year}"
    
    # If no match is found, try to extract from content later
    return "Unknown Date"

def extract_text_from_pdf(bucket, key):
    """
    Extract text from PDF using AWS Textract.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        list: Textract results for each page
    """
    logger.info(f"Extracting text from PDF: s3://{bucket}/{key}")
    
    try:
        # Start the text detection job
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
        logger.info(f"Started Textract job with ID: {job_id}")
        
        # Wait for the job to complete
        job_status = 'IN_PROGRESS'
        while job_status == 'IN_PROGRESS':
            response = textract_client.get_document_analysis(JobId=job_id)
            job_status = response['JobStatus']
            
            if job_status == 'FAILED':
                raise Exception(f"Textract job failed: {response.get('StatusMessage', 'No message')}")
        
        # Get all pages from the result
        pages = []
        pages.append(response)
        
        next_token = response.get('NextToken')
        while next_token:
            response = textract_client.get_document_analysis(JobId=job_id, NextToken=next_token)
            pages.append(response)
            next_token = response.get('NextToken')
        
        logger.info(f"Successfully extracted text from PDF with {len(pages)} page(s)")
        return pages
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}", exc_info=True)
        raise

def process_textract_result(textract_pages, month_year):
    """
    Process Textract result to extract cylinder logs data.
    
    Args:
        textract_pages (list): Textract results for each page
        month_year (str): Month and year
        
    Returns:
        dict: Processed cylinder logs data
    """
    logger.info(f"Processing Textract results for {month_year}")
    
    try:
        # Extract all tables from the Textract result
        all_tables = []
        extracted_text = ""
        
        for page in textract_pages:
            blocks = page['Blocks']
            
            # Extract text
            for block in blocks:
                if block['BlockType'] == 'LINE':
                    extracted_text += block['Text'] + "\n"
            
            # Extract tables
            tables = extract_tables_from_blocks(blocks)
            all_tables.extend(tables)
        
        logger.info(f"Extracted {len(all_tables)} tables from Textract results")
        
        # If month_year is unknown, try to extract it from the text
        if month_year == "Unknown Date":
            month_year = extract_month_year_from_text(extracted_text)
        
        # Process the tables to identify cylinder logs
        cylinder_data = process_cylinder_tables(all_tables, month_year, extracted_text)
        
        return cylinder_data
    
    except Exception as e:
        logger.error(f"Error processing Textract result: {str(e)}", exc_info=True)
        raise

def extract_month_year_from_text(text):
    """
    Extract month and year from text content.
    
    Args:
        text (str): Extracted text
        
    Returns:
        str: Month and year (e.g., "Jan 2016")
    """
    # Look for month and year pattern in the text
    month_year_pattern = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*[,]?\s*(\d{4})"
    match = re.search(month_year_pattern, text)
    
    if match:
        month = match.group(1)
        year = match.group(2)
        return f"{month} {year}"
    
    # Look for year patterns and nearby month patterns
    year_pattern = r"(20\d{2})"
    year_matches = list(re.finditer(year_pattern, text))
    
    for year_match in year_matches:
        year = year_match.group(1)
        # Look for a month within 20 characters of the year
        context = text[max(0, year_match.start() - 20):min(len(text), year_match.end() + 20)]
        
        month_pattern = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        month_match = re.search(month_pattern, context)
        
        if month_match:
            month = month_match.group(1)
            return f"{month} {year}"
    
    # If all else fails, look for date patterns
    date_pattern = r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"
    match = re.search(date_pattern, text)
    
    if match:
        month_map = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        
        day = int(match.group(1))
        month_num = int(match.group(2))
        year = match.group(3)
        
        # Adjust short year format
        if len(year) == 2:
            year = f"20{year}" if int(year) < 50 else f"19{year}"
            
        month = month_map.get(month_num, str(month_num))
        return f"{month} {year}"
    
    return "Unknown Date"

def extract_tables_from_blocks(blocks):
    """
    Extract tables from Textract blocks.
    
    Args:
        blocks (list): Textract blocks
        
    Returns:
        list: Extracted tables
    """
    # Map to store table IDs and their cells
    tables = {}
    cells_by_table = {}
    
    # First pass: Identify tables and cells
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_id = block['Id']
            tables[table_id] = {
                'id': table_id,
                'cells': []
            }
            cells_by_table[table_id] = []
        
        elif block['BlockType'] == 'CELL':
            # Find the parent table
            if 'Relationships' not in block:
                continue
                
            table_ids = []
            for relationship in block['Relationships']:
                if relationship['Type'] == 'TABLE':
                    table_ids.extend(relationship['Ids'])
            
            for table_id in table_ids:
                if table_id in cells_by_table:
                    # Add cell to the table
                    row_index = block.get('RowIndex', 0) - 1  # 0-based indexing
                    col_index = block.get('ColumnIndex', 0) - 1  # 0-based indexing
                    
                    cells_by_table[table_id].append({
                        'id': block['Id'],
                        'row_index': row_index,
                        'col_index': col_index,
                        'text': '',
                        'block': block
                    })
    
    # Second pass: Extract text for each cell
    block_map = {block['Id']: block for block in blocks}
    
    for table_id, cells in cells_by_table.items():
        for cell in cells:
            cell_block = cell['block']
            # Find child relationships for this cell
            if 'Relationships' in cell_block:
                for relationship in cell_block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        # Extract text from child word blocks
                        text_parts = []
                        for child_id in relationship['Ids']:
                            child_block = block_map.get(child_id)
                            if child_block and child_block['BlockType'] == 'WORD':
                                text_parts.append(child_block['Text'])
                        
                        cell['text'] = ' '.join(text_parts)
    
    # Third pass: Convert cells to tables
    extracted_tables = []
    for table_id, cells in cells_by_table.items():
        if not cells:
            continue
        
        # Determine table dimensions
        max_row = max(cell['row_index'] for cell in cells)
        max_col = max(cell['col_index'] for cell in cells)
        
        # Create an empty table
        table = [[''] * (max_col + 1) for _ in range(max_row + 1)]
        
        # Fill in cell values
        for cell in cells:
            row = cell['row_index']
            col = cell['col_index']
            text = cell['text']
            
            if row < len(table) and col < len(table[row]):
                table[row][col] = text
        
        # Add the table to the result
        extracted_tables.append(table)
    
    return extracted_tables

def process_cylinder_tables(tables, month_year, extracted_text):
    """
    Process tables to extract cylinder logs data.
    
    Args:
        tables (list): List of tables
        month_year (str): Month and year
        extracted_text (str): Full extracted text from the document
        
    Returns:
        dict: Cylinder logs data
    """
    logger.info(f"Processing {len(tables)} tables from cylinder logs for {month_year}")
    
    # Find the cylinder logs tables
    filled_cylinders_table = None
    empty_cylinders_table = None
    
    # Based on the sample PDF provided, identify tables by looking for specific headers
    for table in tables:
        # Skip tables that are too small
        if len(table) < 3 or len(table[0]) < 5:
            continue
        
        # Check for headers that indicate filled cylinders or empty cylinders
        header_text = ' '.join([str(cell) for row in table[:2] for cell in row])
        
        if 'FILLED CYLINDERS' in header_text.upper():
            filled_cylinders_table = table
            logger.info("Found filled cylinders table")
        
        elif 'EMPTY CYLINDERS' in header_text.upper():
            empty_cylinders_table = table
            logger.info("Found empty cylinders table")
    
    # If no tables were identified by header text, try to identify by column structure
    if not filled_cylinders_table and not empty_cylinders_table and tables:
        for table in tables:
            if len(table) < 3 or len(table[0]) < 5:
                continue
                
            # Look for tables with date, opening stock, receipt columns
            header_row = table[0] if len(table) > 0 else []
            header_text = ' '.join([str(cell) for cell in header_row])
            
            date_match = any('date' in str(cell).lower() for cell in header_row)
            opening_match = any('opening' in str(cell).lower() for cell in header_row)
            stock_match = any('stock' in str(cell).lower() for cell in header_row)
            
            if date_match or opening_match or stock_match:
                if not filled_cylinders_table:
                    filled_cylinders_table = table
                    logger.info("Found filled cylinders table by column structure")
                elif not empty_cylinders_table:
                    empty_cylinders_table = table
                    logger.info("Found empty cylinders table by column structure")
    
    # If still not found, try the largest table
    if not filled_cylinders_table and not empty_cylinders_table and tables:
        # Sort tables by size (number of cells)
        sorted_tables = sorted(tables, key=lambda t: len(t) * len(t[0]), reverse=True)
        largest_table = sorted_tables[0]
        
        # Determine if this is likely a cylinder logs table
        if len(largest_table) > 3 and len(largest_table[0]) > 8:
            # Check the first few rows for indicators
            header_text = ' '.join([str(cell) for row in largest_table[:3] for cell in row])
            
            if 'date' in header_text.lower() or 'stock' in header_text.lower():
                # This is likely a cylinder logs table
                # Try to determine if it contains both filled and empty cylinders
                if len(largest_table[0]) > 15:  # Wide table that might contain both
                    # Split the table in the middle
                    middle_index = len(largest_table[0]) // 2
                    
                    filled_cylinders_table = [row[:middle_index] for row in largest_table]
                    empty_cylinders_table = [row[middle_index:] for row in largest_table]
                    
                    logger.info("Split the largest table into filled and empty cylinders tables")
                else:
                    # Use as filled cylinders table
                    filled_cylinders_table = largest_table
                    logger.info("Using the largest table as filled cylinders table")
    
    # Process the filled cylinders table
    filled_data = None
    if filled_cylinders_table:
        filled_data = extract_cylinder_data(filled_cylinders_table, 'filled')
    
    # Process the empty cylinders table
    empty_data = None
    if empty_cylinders_table:
        empty_data = extract_cylinder_data(empty_cylinders_table, 'empty')
    
    # If table extraction failed, try to extract from text
    if not filled_data and not empty_data:
        logger.info("Table extraction failed, trying to extract from text")
        return extract_from_text(extracted_text, month_year)
    
    # Perform analysis on the extracted data
    analysis = analyze_cylinder_data(filled_data, empty_data)
    
    return {
        'month_year': month_year,
        'filled_cylinders': filled_data or {},
        'empty_cylinders': empty_data or {},
        'analysis': analysis
    }

def extract_cylinder_data(table, cylinder_type):
    """
    Extract cylinder data from a table.
    
    Args:
        table (list): Table containing cylinder data
        cylinder_type (str): Type of cylinders ('filled' or 'empty')
        
    Returns:
        dict: Extracted cylinder data
    """
    try:
        # Convert table to DataFrame
        df = pd.DataFrame(table)
        
        # Identify header rows
        # Look for rows containing common header terms
        header_terms = ['date', 'opening', 'stock', 'receipt', 'issue', 'refill', 'return', 'closing', 'cum']
        header_row = None
        
        for i in range(min(3, len(df))):
            row_text = ' '.join([str(cell).lower() for cell in df.iloc[i]])
            matches = sum(1 for term in header_terms if term in row_text)
            
            if matches >= 3:  # If row contains at least 3 header terms
                header_row = i
                break
        
        # If no header row found, use row 0
        if header_row is None:
            header_row = 0
        
        # Extract data rows (rows after the header row)
        data_rows = df.iloc[header_row+1:].copy()
        
        # Filter out rows that don't contain date information
        date_pattern = r'\d{1,2}[/\|]\d{1,2}'
        has_date = data_rows[0].astype(str).str.contains(date_pattern, regex=True)
        data_rows_with_dates = data_rows[has_date]
        
        # If no date rows found, try to use all rows
        if len(data_rows_with_dates) == 0:
            # Just use all rows after header
            data_rows_with_dates = data_rows
        
        # Extract cylinder data based on column patterns
        if cylinder_type == 'filled':
            # For filled cylinders, look for standard columns
            opening_stock = extract_numeric_column(data_rows_with_dates, ['opening', 'stock', 'opening stock'], [1, 2])
            closing_stock = extract_numeric_column(data_rows_with_dates, ['closing', 'stock', 'closing stock'], [12, 13, 5])
            receipts = extract_numeric_column(data_rows_with_dates, ['receipt', 'from', 'ioc'], [2, 3])
            issues = extract_numeric_column(data_rows_with_dates, ['issue', 'against', 'refill', 'sv'], [5, 6, 7, 8, 9])
            
            return {
                'opening_stock': opening_stock,
                'closing_stock': closing_stock,
                'receipts': receipts,
                'issues': issues
            }
        
        else:  # empty cylinders
            # For empty cylinders, look for standard columns
            opening_stock = extract_numeric_column(data_rows_with_dates, ['opening', 'stock', 'opening stock'], [14, 15, 1])
            closing_stock = extract_numeric_column(data_rows_with_dates, ['closing', 'stock', 'empty closing'], [19, 20, 7, 8])
            receipts = extract_numeric_column(data_rows_with_dates, ['receipt', 'against', 'refill'], [15, 16, 2, 3])
            returns = extract_numeric_column(data_rows_with_dates, ['return', 'to', 'ioc'], [18, 19, 6])
            
            return {
                'opening_stock': opening_stock,
                'closing_stock': closing_stock,
                'receipts': receipts,
                'returns': returns
            }
    
    except Exception as e:
        logger.error(f"Error extracting {cylinder_type} cylinder data: {str(e)}", exc_info=True)
        return {}

def extract_numeric_column(df, keywords, possible_indexes):
    """
    Extract a numeric column from the DataFrame based on keywords or column indexes.
    
    Args:
        df (DataFrame): DataFrame containing the data
        keywords (list): List of keywords to look for in column headers
        possible_indexes (list): List of possible column indexes to try
        
    Returns:
        list: List of numeric values
    """
    # First try to find the column by keywords
    header_row = df.iloc[0] if len(df) > 0 else []
    
    for col in range(len(df.columns)):
        if col < len(header_row):
            col_header = str(header_row[col]).lower()
            if any(keyword in col_header for keyword in keywords):
                try:
                    values = pd.to_numeric(df.iloc[1:, col], errors='coerce').dropna().tolist()
                    if values:
                        return values
                except:
                    pass
    
    # If not found by keywords, try the possible indexes
    for idx in possible_indexes:
        if idx < len(df.columns):
            try:
                values = pd.to_numeric(df.iloc[:, idx], errors='coerce').dropna().tolist()
                if values:
                    return values
            except:
                pass
    
    # If still not found, check all columns and return the one with most numeric values
    max_count = 0
    best_values = []
    
    for col in range(len(df.columns)):
        try:
            values = pd.to_numeric(df.iloc[:, col], errors='coerce').dropna().tolist()
            if len(values) > max_count:
                max_count = len(values)
                best_values = values
        except:
            pass
    
    return best_values

def extract_from_text(text, month_year):
    """
    Extract cylinder logs data from raw text.
    
    Args:
        text (str): Raw text extracted from the document
        month_year (str): Month and year
        
    Returns:
        dict: Cylinder logs data
    """
    # Look for date patterns to identify rows
    date_pattern = r'(\d{1,2})[/\|](\d{1,2})[/\|](\d{2,4})'
    date_matches = list(re.finditer(date_pattern, text))
    
    if not date_matches:
        logger.warning("No date patterns found in raw text")
        return {
            "month_year": month_year,
            "filled_cylinders": {},
            "empty_cylinders": {},
            "analysis": {}
        }
    
    # Extract filled cylinder data
    filled_data = {
        "opening_stock": [],
        "receipts": [],
        "issues": [],
        "closing_stock": []
    }
    
    # Extract empty cylinder data
    empty_data = {
        "opening_stock": [],
        "receipts": [],
        "returns": [],
        "closing_stock": []
    }
    
    # Try to extract numeric values following common labels
    opening_pattern = r'Opening[^\d]*(\d+)'
    receipt_pattern = r'Receipt[^\d]*(\d+)'
    issue_pattern = r'Issue[^\d]*(\d+)'
    closing_pattern = r'Closing[^\d]*(\d+)'
    return_pattern = r'Return[^\d]*(\d+)'
    
    # Attempt to extract patterns for each section of the document
    for i, match in enumerate(date_matches):
        line_start = match.start()
        line_end = date_matches[i+1].start() if i < len(date_matches) - 1 else len(text)
        line_text = text[line_start:line_end]
        
        # Try to find values for each field in filled cylinders section
        opening_match = re.search(opening_pattern, line_text)
        if opening_match:
            filled_data["opening_stock"].append(float(opening_match.group(1)))
        
        receipt_match = re.search(receipt_pattern, line_text)
        if receipt_match:
            filled_data["receipts"].append(float(receipt_match.group(1)))
        
        issue_match = re.search(issue_pattern, line_text)
        if issue_match:
            filled_data["issues"].append(float(issue_match.group(1)))
        
        closing_match = re.search(closing_pattern, line_text)
        if closing_match:
            filled_data["closing_stock"].append(float(closing_match.group(1)))
        
        # Try to find values for empty cylinders if they exist
        return_match = re.search(return_pattern, line_text)
        if return_match:
            empty_data["returns"].append(float(return_match.group(1)))
    
    # Perform analysis on the extracted data
    analysis = analyze_cylinder_data(filled_data, empty_data)
    
    return {
        "month_year": month_year,
        "filled_cylinders": filled_data,
        "empty_cylinders": empty_data,
        "analysis": analysis,
        "note": "Data extracted from raw text, may be less accurate than table extraction"
    }

def analyze_cylinder_data(filled_data, empty_data):
    """
    Analyze cylinder data to extract insights.
    
    Args:
        filled_data (dict): Filled cylinder data
        empty_data (dict): Empty cylinder data
        
    Returns:
        dict: Analysis results
    """
    analysis = {}
    
    # Analyze filled cylinders if data is available
    if filled_data and 'opening_stock' in filled_data and 'closing_stock' in filled_data:
        filled_opening = filled_data['opening_stock']
        filled_closing = filled_data['closing_stock']
        
        # Calculate averages
        avg_opening = np.mean(filled_opening) if filled_opening else 0
        avg_closing = np.mean(filled_closing) if filled_closing else 0
        
        # Calculate change
        stock_change = avg_closing - avg_opening
        stock_change_pct = (stock_change / avg_opening * 100) if avg_opening else 0
        
        # Add to analysis
        analysis['filled_cylinders'] = {
            'avg_opening_stock': round(avg_opening, 2),
            'avg_closing_stock': round(avg_closing, 2),
            'stock_change': round(stock_change, 2),
            'stock_change_percent': round(stock_change_pct, 2)
        }
        
        # Add receipts and issues analysis
        if 'receipts' in filled_data and 'issues' in filled_data:
            receipts = filled_data['receipts']
            issues = filled_data['issues']
            
            avg_receipts = np.mean(receipts) if receipts else 0
            avg_issues = np.mean(issues) if issues else 0
            total_receipts = sum(receipts) if receipts else 0
            total_issues = sum(issues) if issues else 0
            
            analysis['filled_cylinders'].update({
                'avg_receipts': round(avg_receipts, 2),
                'avg_issues': round(avg_issues, 2),
                'total_receipts': round(total_receipts, 2),
                'total_issues': round(total_issues, 2)
            })
    
    # Analyze empty cylinders if data is available
    if empty_data and 'opening_stock' in empty_data and 'closing_stock' in empty_data:
        empty_opening = empty_data['opening_stock']
        empty_closing = empty_data['closing_stock']
        
        # Calculate averages
        avg_opening = np.mean(empty_opening) if empty_opening else 0
        avg_closing = np.mean(empty_closing) if empty_closing else 0
        
        # Calculate change
        stock_change = avg_closing - avg_opening
        stock_change_pct = (stock_change / avg_opening * 100) if avg_opening else 0
        
        # Add to analysis
        analysis['empty_cylinders'] = {
            'avg_opening_stock': round(avg_opening, 2),
            'avg_closing_stock': round(avg_closing, 2),
            'stock_change': round(stock_change, 2),
            'stock_change_percent': round(stock_change_pct, 2)
        }
        
        # Add receipts and returns analysis
        if 'receipts' in empty_data and 'returns' in empty_data:
            receipts = empty_data['receipts']
            returns = empty_data['returns']
            
            avg_receipts = np.mean(receipts) if receipts else 0
            avg_returns = np.mean(returns) if returns else 0
            total_receipts = sum(receipts) if receipts else 0
            total_returns = sum(returns) if returns else 0
            
            analysis['empty_cylinders'].update({
                'avg_receipts': round(avg_receipts, 2),
                'avg_returns': round(avg_returns, 2),
                'total_receipts': round(total_receipts, 2),
                'total_returns': round(total_returns, 2)
            })
    
    # Calculate overall summary if both filled and empty data are available
    if 'filled_cylinders' in analysis and 'empty_cylinders' in analysis:
        filled_change = analysis['filled_cylinders']['stock_change']
        empty_change = analysis['empty_cylinders']['stock_change']
        
        # Add summary metrics
        analysis['summary'] = {
            'net_inventory_change': round(filled_change + empty_change, 2),
            'refill_efficiency': round(
                analysis['filled_cylinders'].get('total_issues', 0) / 
                analysis['empty_cylinders'].get('total_returns', 1), 2
            ) if analysis['empty_cylinders'].get('total_returns', 0) > 0 else 0
        }
    
    return analysis
