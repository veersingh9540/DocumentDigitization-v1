import re
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process_cylinder_logs(extracted_text, table_data):
    """
    Process cylinder logs data extracted from the PDF.
    
    Args:
        extracted_text (str): Raw text extracted from the document
        table_data (list): Tables extracted from the document
        
    Returns:
        dict: Structured cylinder log data
    """
    logger.info("Processing cylinder logs data")
    
    # Try to identify the date and month from the document header
    month_year = extract_month_year(extracted_text)
    
    # Process the table data if available
    if table_data and len(table_data) > 0:
        return process_cylinder_tables(table_data, month_year)
    else:
        # If table extraction failed, try to parse from raw text
        return process_cylinder_text(extracted_text, month_year)

def extract_month_year(text):
    """
    Extract month and year information from the text.
    
    Args:
        text (str): Extracted text from the document
        
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
    
    # If no match, look for date pattern
    date_pattern = r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"
    match = re.search(date_pattern, text)
    
    if match:
        # Try to convert numeric month to text
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

def process_cylinder_tables(tables, month_year):
    """
    Process cylinder logs from extracted tables.
    
    Args:
        tables (list): Tables extracted from the document
        month_year (str): Month and year
        
    Returns:
        dict: Structured cylinder log data
    """
    logger.info(f"Processing {len(tables)} tables from cylinder logs")
    
    # Find the largest table (likely the main data table)
    main_table = None
    max_cells = 0
    
    for table in tables:
        cells_count = sum(len(row) for row in table)
        if cells_count > max_cells:
            max_cells = cells_count
            main_table = table
    
    if not main_table:
        logger.warning("No valid table found in the document")
        return {"error": "No valid table found", "month_year": month_year}
    
    # Convert the table to a DataFrame
    df = pd.DataFrame(main_table)
    
    # Try to identify if the table has headers
    # In this case, we'll assume the first row is headers if it contains 
    # column names like "Date", "Opening Stock", etc.
    header_row = None
    for i, row in enumerate(main_table[:3]):  # Check first 3 rows for headers
        row_text = " ".join(str(cell) for cell in row)
        if re.search(r"Date|Opening|Stock|Receipt|Issue", row_text, re.IGNORECASE):
            header_row = i
            break
    
    # If headers found, use them
    if header_row is not None:
        headers = main_table[header_row]
        data_rows = main_table[header_row + 1:]
        df = pd.DataFrame(data_rows, columns=headers)
    
    # Clean the dataframe
    df = clean_cylinder_dataframe(df)
    
    # Extract filled and empty cylinder data
    filled_cylinders, empty_cylinders = extract_cylinder_data(df)
    
    # Analyze trends
    analysis = analyze_cylinder_trends({
        "month_year": month_year,
        "filled_cylinders": filled_cylinders,
        "empty_cylinders": empty_cylinders
    })
    
    return {
        "month_year": month_year,
        "filled_cylinders": filled_cylinders,
        "empty_cylinders": empty_cylinders,
        "analysis": analysis["analysis"] if "analysis" in analysis else {}
    }

def clean_cylinder_dataframe(df):
    """
    Clean and prepare the cylinder log dataframe.
    
    Args:
        df (DataFrame): Raw dataframe from table extraction
        
    Returns:
        DataFrame: Cleaned dataframe
    """
    # Replace empty or whitespace-only cells with NaN
    df = df.applymap(lambda x: None if x is None or (isinstance(x, str) and x.strip() == '') else x)
    
    # Try to detect date column
    date_col = None
    for col in df.columns[:3]:  # Usually date is in the first few columns
        if df[col].astype(str).str.contains(r'\d{1,2}[/\-]\d{1,2}|\d{1,2}[\s]*[\|/][\s]*\d{1,2}').any():
            date_col = col
            break
    
    # If a date column is found, parse dates
    if date_col:
        df[date_col] = df[date_col].astype(str)
        # Mark rows that likely contain data (have a date)
        df['has_date'] = df[date_col].str.contains(r'\d{1,2}[/\-]\d{1,2}|\d{1,2}[\s]*[\|/][\s]*\d{1,2}')
        # Filter out rows without dates
        df = df[df['has_date'] == True].drop('has_date', axis=1)
    
    # Convert numeric columns to float where possible
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except:
            pass
    
    return df

def extract_cylinder_data(df):
    """
    Extract filled and empty cylinder data from the dataframe.
    
    Args:
        df (DataFrame): Processed dataframe
        
    Returns:
        tuple: (filled_cylinders_data, empty_cylinders_data)
    """
    # Try to identify sections for filled and empty cylinders
    # This depends on the specific format of your cylinder logs
    
    # For this example, we'll assume the dataframe contains both filled and empty data
    # We'll extract key metrics like openings, receipts, issues, etc.
    
    # Extract metrics for filled cylinders
    filled_data = {
        "opening_stock": get_numeric_column(df, 1, "opening"),
        "receipts": get_numeric_column(df, 2, "receipt"),
        "issues": get_numeric_column(df, [5, 6, 7], "issue"),
        "closing_stock": get_numeric_column(df, [12, 13], "closing") 
    }
    
    # Extract metrics for empty cylinders
    empty_data = {
        "opening_stock": get_numeric_column(df, [14, 15], "opening", offset=13),
        "receipts": get_numeric_column(df, [15, 16], "receipt", offset=13),
        "returns": get_numeric_column(df, [18, 19], "return", offset=13),
        "closing_stock": get_numeric_column(df, [19, 20], "closing", offset=13)
    }
    
    return filled_data, empty_data

def get_numeric_column(df, cols, keyword, offset=0):
    """
    Extract numeric data from specific columns or by keyword search.
    
    Args:
        df (DataFrame): DataFrame to search
        cols (int or list): Column index or list of column indices to check
        keyword (str): Keyword to search for in column headers
        offset (int): Offset for column indices (for right side of table)
        
    Returns:
        list: List of numeric values
    """
    # Convert single column to list
    if not isinstance(cols, list):
        cols = [cols]
    
    # Try each column
    for col_idx in cols:
        if col_idx < len(df.columns):
            # Try to get numeric values
            try:
                values = pd.to_numeric(df.iloc[:, col_idx], errors='coerce')
                values = values.dropna().tolist()
                if values and len(values) > 0:
                    return values
            except:
                pass
    
    # If direct column access fails, try keyword search in headers
    for i, col_name in enumerate(df.columns):
        if isinstance(col_name, str) and keyword.lower() in col_name.lower():
            try:
                values = pd.to_numeric(df.iloc[:, i], errors='coerce')
                values = values.dropna().tolist()
                if values and len(values) > 0:
                    return values
            except:
                pass
    
    # Return empty list if no valid column found
    return []

def process_cylinder_text(text, month_year):
    """
    Process cylinder logs from raw text when table extraction fails.
    
    Args:
        text (str): Raw text extracted from the document
        month_year (str): Month and year
        
    Returns:
        dict: Structured cylinder log data
    """
    logger.info("Processing cylinder logs from raw text")
    
    # This is a fallback method when table extraction fails
    # It attempts to parse the raw text to extract cylinder data
    
    # Look for date patterns to identify rows
    date_pattern = r'(\d{1,2})[/\|](\d{1,2})[/\|](\d{2,4})'
    date_matches = list(re.finditer(date_pattern, text))
    
    if not date_matches:
        logger.warning("No date patterns found in raw text")
        return {"error": "Failed to extract data from text", "month_year": month_year}
    
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
    
    # Attempt to extract patterns for each section of the document
    for i, match in enumerate(date_matches):
        line_start = match.start()
        line_end = date_matches[i+1].start() if i < len(date_matches) - 1 else len(text)
        line_text = text[line_start:line_end]
        
        # Try to find values for each field
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
    
    # If we couldn't extract much data, return what we have
    return {
        "month_year": month_year,
        "filled_cylinders": filled_data,
        "empty_cylinders": empty_data,
        "note": "Data extracted from raw text, may be less accurate than table extraction"
    }

def analyze_cylinder_trends(data):
    """
    Analyze trends in cylinder data.
    
    Args:
        data (dict): Structured cylinder log data
        
    Returns:
        dict: Analysis results
    """
    results = {
        "month_year": data.get("month_year", "Unknown"),
        "analysis": {}
    }
    
    filled = data.get("filled_cylinders", {})
    empty = data.get("empty_cylinders", {})
    
    # Calculate basic statistics for filled cylinders
    if filled.get("opening_stock") and filled.get("closing_stock"):
        opening_avg = np.mean(filled["opening_stock"]) if filled["opening_stock"] else 0
        closing_avg = np.mean(filled["closing_stock"]) if filled["closing_stock"] else 0
        stock_change = closing_avg - opening_avg
        
        results["analysis"]["filled_cylinders"] = {
            "avg_opening_stock": round(opening_avg, 2),
            "avg_closing_stock": round(closing_avg, 2),
            "stock_change": round(stock_change, 2),
            "stock_change_percent": round((stock_change / opening_avg * 100), 2) if opening_avg else 0
        }
    
    # Calculate basic statistics for empty cylinders
    if empty.get("opening_stock") and empty.get("closing_stock"):
        opening_avg = np.mean(empty["opening_stock"]) if empty["opening_stock"] else 0
        closing_avg = np.mean(empty["closing_stock"]) if empty["closing_stock"] else 0
        stock_change = closing_avg - opening_avg
        
        results["analysis"]["empty_cylinders"] = {
            "avg_opening_stock": round(opening_avg, 2),
            "avg_closing_stock": round(closing_avg, 2),
            "stock_change": round(stock_change, 2),
            "stock_change_percent": round((stock_change / opening_avg * 100), 2) if opening_avg else 0
        }
    
    # Add summary statistics
    if "filled_cylinders" in results["analysis"] and "empty_cylinders" in results["analysis"]:
        filled_change = results["analysis"]["filled_cylinders"]["stock_change"]
        empty_change = results["analysis"]["empty_cylinders"]["stock_change"]
        
        results["analysis"]["summary"] = {
            "net_inventory_change": round(filled_change + empty_change, 2),
            "refill_to_return_ratio": round(abs(filled_change / empty_change), 2) if empty_change else 0
        }
    
    return results
