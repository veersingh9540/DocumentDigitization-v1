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
