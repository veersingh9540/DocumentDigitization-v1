import json
import os
import logging
import sys
import traceback

# Add the current directory to the path so we can import db_helper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_helper

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main Lambda handler function for dashboard API.
    
    Args:
        event (dict): API Gateway event
        context (object): Lambda context
        
    Returns:
        dict: API response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Set CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }
    
    # Handle OPTIONS request (preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({})
        }
    
    try:
        # Parse path parameters
        path = event.get('path', '')
        if 'resource' in event:
            path = event['resource']  # Use API Gateway resource if available
        
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Setup database tables if needed
        db_helper.create_tables()
        
        # Route to appropriate handler based on path
        if path.startswith('/api/documents') or path == '/documents/{document_id}':
            return get_documents(path, query_params, event, headers)
        elif path.startswith('/api/cylinder-logs') or path == '/cylinder-logs':
            return get_cylinder_logs(path, query_params, headers)
        elif path.startswith('/api/stats') or path.startswith('/stats'):
            return get_stats(path, query_params, headers)
        elif path == '/api/health' or path == '/health':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'status': 'healthy',
                    'message': 'Dashboard API is running'
                })
            }
        else:
            # Default response for unknown paths
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'Path {path} not found'
                })
            }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }

def get_documents(path, query_params, event, headers):
    """
    Handle document-related API requests.
    
    Args:
        path (str): API path
        query_params (dict): Query parameters
        event (dict): API Gateway event
        headers (dict): HTTP headers
        
    Returns:
        dict: API response
    """
    # Extract document ID if present in path
    document_id = None
    
    # Check if we have a path parameter
    if 'pathParameters' in event and event['pathParameters']:
        document_id = event['pathParameters'].get('document_id')
    
    # If not found in path parameters, try to extract from the path itself
    if not document_id:
        path_parts = path.split('/')
        document_id = path_parts[-1] if len(path_parts) > 2 and path_parts[-1] != 'documents' else None
    
    if document_id and document_id != '{document_id}':
        # Get a specific document
        document = db_helper.get_document_by_id(document_id)
        
        if document:
            # Truncate extracted_text for the response if it's too large
            if 'extracted_text' in document and len(document['extracted_text']) > 1000:
                document['extracted_text'] = document['extracted_text'][:1000] + '...'
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(document)
            }
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'Document with ID {document_id} not found'
                })
            }
    else:
        # Get list of documents with pagination
        limit = int(query_params.get('limit', 10))
        offset = int(query_params.get('offset', 0))
        
        # TODO: Implement proper pagination for documents
        # For now, use some mock data along with any real data we might have
        
        # Here you would typically fetch documents from the database
        documents = []
        total = 0
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'documents': documents,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'next_offset': offset + limit if offset + limit < total else None
                }
            })
        }

def get_cylinder_logs(path, query_params, headers):
    """
    Handle cylinder logs API requests.
    
    Args:
        path (str): API path
        query_params (dict): Query parameters
        headers (dict): HTTP headers
        
    Returns:
        dict: API response
    """
    # Extract month_year from query parameters
    month_year = query_params.get('month_year')
    limit = int(query_params.get('limit', 10))
    offset = int(query_params.get('offset', 0))
    
    # Get cylinder logs from database
    logs = db_helper.get_cylinder_logs(month_year, limit, offset)
    
    # Calculate total count (in a real implementation, this would be a separate query)
    total = len(logs) + offset  # This is just an approximation
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'logs': logs,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'next_offset': offset + limit if offset + limit < total else None
            }
        })
    }

def get_stats(path, query_params, headers):
    """
    Handle statistics API requests.
    
    Args:
        path (str): API path
        query_params (dict): Query parameters
        headers (dict): HTTP headers
        
    Returns:
        dict: API response
    """
    # Extract date range from query parameters
    start_date = query_params.get('start_date')
    end_date = query_params.get('end_date')
    
    # Extract specific stat type if provided
    path_parts = path.split('/')
    stat_type = path_parts[-1] if len(path_parts) > 2 else None
    
    if stat_type and stat_type not in ['stats', '{proxy+}']:
        # Handle specific stat type
        if stat_type == 'monthly':
            # Get monthly statistics
            stats = db_helper.get_monthly_stats(start_date, end_date)
            
            # Prepare data for chart visualization
            months = []
            filled_data = []
            empty_data = []
            
            for stat in stats:
                months.append(stat['month_year'])
                
                filled_stats = stat.get('filled_cylinder_stats', {})
                empty_stats = stat.get('empty_cylinder_stats', {})
                
                filled_data.append({
                    'month': stat['month_year'],
                    'opening_stock': filled_stats.get('avg_opening_stock', 0),
                    'closing_stock': filled_stats.get('avg_closing_stock', 0),
                    'receipts': filled_stats.get('avg_receipts', 0),
                    'issues': filled_stats.get('avg_issues', 0)
                })
                
                empty_data.append({
                    'month': stat['month_year'],
                    'opening_stock': empty_stats.get('avg_opening_stock', 0),
                    'closing_stock': empty_stats.get('avg_closing_stock', 0),
                    'receipts': empty_stats.get('avg_receipts', 0),
                    'returns': empty_stats.get('avg_returns', 0)
                })
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'months': months,
                    'filled_cylinders': filled_data,
                    'empty_cylinders': empty_data
                })
            }
            
        elif stat_type == 'summary':
            # Get an overall summary of statistics
            stats = db_helper.get_monthly_stats(start_date, end_date)
            
            # Calculate summary metrics
            total_documents = len(stats)
            total_transactions = sum(stat.get('total_transactions', 0) for stat in stats)
            
            # If no stats available, use mock data
            if total_documents == 0:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'total_documents': 3,
                        'total_transactions': 93,
                        'filled_cylinders': {
                            'avg_opening_stock': 210.5,
                            'avg_closing_stock': 192.3,
                            'avg_receipts': 157.8,
                            'avg_issues': 175.9
                        },
                        'empty_cylinders': {
                            'avg_opening_stock': 185.7,
                            'avg_closing_stock': 310.3,
                            'avg_receipts': 198.2,
                            'avg_returns': 74.1
                        }
                    })
                }
            
            # Calculate averages for filled cylinders
            avg_filled_opening = sum(stat.get('filled_cylinder_stats', {}).get('avg_opening_stock', 0) for stat in stats) / total_documents if total_documents else 0
            avg_filled_closing = sum(stat.get('filled_cylinder_stats', {}).get('avg_closing_stock', 0) for stat in stats) / total_documents if total_documents else 0
            avg_filled_receipts = sum(stat.get('filled_cylinder_stats', {}).get('avg_receipts', 0) for stat in stats) / total_documents if total_documents else 0
            avg_filled_issues = sum(stat.get('filled_cylinder_stats', {}).get('avg_issues', 0) for stat in stats) / total_documents if total_documents else 0
            
            # Calculate averages for empty cylinders
            avg_empty_opening = sum(stat.get('empty_cylinder_stats', {}).get('avg_opening_stock', 0) for stat in stats) / total_documents if total_documents else 0
            avg_empty_closing = sum(stat.get('empty_cylinder_stats', {}).get('avg_closing_stock', 0) for stat in stats) / total_documents if total_documents else 0
            avg_empty_receipts = sum(stat.get('empty_cylinder_stats', {}).get('avg_receipts', 0) for stat in stats) / total_documents if total_documents else 0
            avg_empty_returns = sum(stat.get('empty_cylinder_stats', {}).get('avg_returns', 0) for stat in stats) / total_documents if total_documents else 0
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'total_documents': total_documents,
                    'total_transactions': total_transactions,
                    'filled_cylinders': {
                        'avg_opening_stock': round(avg_filled_opening, 2),
                        'avg_closing_stock': round(avg_filled_closing, 2),
                        'avg_receipts': round(avg_filled_receipts, 2),
                        'avg_issues': round(avg_filled_issues, 2)
                    },
                    'empty_cylinders': {
                        'avg_opening_stock': round(avg_empty_opening, 2),
                        'avg_closing_stock': round(avg_empty_closing, 2),
                        'avg_receipts': round(avg_empty_receipts, 2),
                        'avg_returns': round(avg_empty_returns, 2)
                    }
                })
            }
        
        else:
            # Unknown stat type
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'Stat type {stat_type} not found'
                })
            }
    
    else:
        # Get all statistics
        monthly_stats = db_helper.get_monthly_stats(start_date, end_date)
        
        # If no stats available, use mock data
        if not monthly_stats:
            # Generate mock data
            mock_data = [
                {
                    'month_year': 'Jan 2016',
                    'start_date': '2016-01-01',
                    'end_date': '2016-01-31',
                    'filled_cylinders': {
                        'opening_stock': 210,
                        'closing_stock': 112,
                        'receipts': 150,
                        'issues': 248,
                        'net_change': -98
                    },
                    'empty_cylinders': {
                        'opening_stock': 180,
                        'closing_stock': 278,
                        'receipts': 200,
                        'returns': 102,
                        'net_change': 98
                    },
                    'transactions': 31
                },
                {
                    'month_year': 'Feb 2016',
                    'start_date': '2016-02-01',
                    'end_date': '2016-02-29',
                    'filled_cylinders': {
                        'opening_stock': 112,
                        'closing_stock': 355,
                        'receipts': 300,
                        'issues': 57,
                        'net_change': 243
                    },
                    'empty_cylinders': {
                        'opening_stock': 278,
                        'closing_stock': 149,
                        'receipts': 120,
                        'returns': 249,
                        'net_change': -129
                    },
                    'transactions': 29
                },
                {
                    'month_year': 'Mar 2016',
                    'start_date': '2016-03-01',
                    'end_date': '2016-03-31',
                    'filled_cylinders': {
                        'opening_stock': 355,
                        'closing_stock': 110,
                        'receipts': 23,
                        'issues': 268,
                        'net_change': -245
                    },
                    'empty_cylinders': {
                        'opening_stock': 149,
                        'closing_stock': 504,
                        'receipts': 274,
                        'returns': 19,
                        'net_change': 355
                    },
                    'transactions': 31
                }
            ]
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'stats': mock_data
                })
            }
        
        # Process stats for dashboard display
        processed_stats = []
        
        for stat in monthly_stats:
            filled_stats = stat.get('filled_cylinder_stats', {})
            empty_stats = stat.get('empty_cylinder_stats', {})
            
            # Calculate net change in inventory
            filled_change = filled_stats.get('avg_closing_stock', 0) - filled_stats.get('avg_opening_stock', 0)
            empty_change = empty_stats.get('avg_closing_stock', 0) - empty_stats.get('avg_opening_stock', 0)
            
            processed_stats.append({
                'month_year': stat['month_year'],
                'start_date': stat.get('start_date'),
                'end_date': stat.get('end_date'),
                'filled_cylinders': {
                    'opening_stock': filled_stats.get('avg_opening_stock', 0),
                    'closing_stock': filled_stats.get('avg_closing_stock', 0),
                    'receipts': filled_stats.get('avg_receipts', 0),
                    'issues': filled_stats.get('avg_issues', 0),
                    'net_change': filled_change
                },
                'empty_cylinders': {
                    'opening_stock': empty_stats.get('avg_opening_stock', 0),
                    'closing_stock': empty_stats.get('avg_closing_stock', 0),
                    'receipts': empty_stats.get('avg_receipts', 0),
                    'returns': empty_stats.get('avg_returns', 0),
                    'net_change': empty_change
                },
                'transactions': stat.get('total_transactions', 0)
            })
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'stats': processed_stats
            })
        }
