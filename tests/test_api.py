import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
import boto3

os.environ['AWS_REGION'] = 'us-east-1'
boto3.setup_default_session(region_name='us-east-1')
# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/lambda/dashboard_api'))

# Import API handler
from index import (
    lambda_handler,
    get_document,
    get_recent_documents,
    get_cylinder_inventory,
    build_response
)

class TestAPI(unittest.TestCase):
    """Test cases for dashboard API module"""
    
    def setUp(self):
        """Set up test environment"""
        # Set up test data
        self.test_document = {
            'metadata': {
                'document_id': 'test-doc-123',
                'document_type': 'cylinder_inventory',
                'page_count': 3,
                'status': 'processed'
            },
            'fields': {
                'title': 'Test Document'
            },
            'inventory_data': [
                {
                    'date': '01/01/16',
                    'month': 'Jan',
                    'year': '2016',
                    'opening_stock': '210',
                    'receipt': '--',
                    'total_stock': '210',
                    'closing_stock': '108'
                }
            ]
        }
        
        self.test_documents = [
            {
                'document_id': 'test-doc-123',
                'document_type': 'cylinder_inventory',
                'status': 'processed',
                'created_at': '2023-01-01T12:00:00'
            },
            {
                'document_id': 'test-doc-456',
                'document_type': 'invoice',
                'status': 'processed',
                'created_at': '2023-01-02T12:00:00'
            }
        ]
        
        self.test_inventory_data = [
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
    
    def test_build_response(self):
        """Test building API response"""
        # Test success response
        response = build_response(200, {'message': 'Success'})
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['message'], 'Success')
        
        # Test error response
        response = build_response(404, {'error': 'Not found'})
        self.assertEqual(response['statusCode'], 404)
        self.assertEqual(json.loads(response['body'])['error'], 'Not found')
        
        # Test CORS headers
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
    
    @patch('index.get_db_credentials')
    @patch('index.DatabaseConnector')
    def test_get_document(self, mock_db_connector, mock_get_credentials):
        """Test getting a single document"""
        # Set up mocks
        mock_db = MagicMock()
        mock_db.get_document_by_id.return_value = self.test_document
        mock_db_connector.return_value = mock_db
        
        # Call the function
        response = get_document(mock_db, 'test-doc-123')
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['metadata']['document_id'], 'test-doc-123')
        
        # Test document not found
        mock_db.get_document_by_id.return_value = None
        response = get_document(mock_db, 'non-existent-doc')
        self.assertEqual(response['statusCode'], 404)
    
    @patch('index.get_db_credentials')
    @patch('index.DatabaseConnector')
    def test_get_recent_documents(self, mock_db_connector, mock_get_credentials):
        """Test getting recent documents"""
        # Set up mocks
        mock_db = MagicMock()
        mock_db.get_recent_documents.return_value = self.test_documents
        mock_db_connector.return_value = mock_db
        
        # Call the function
        response = get_recent_documents(mock_db)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(len(body['documents']), 2)
        self.assertEqual(body['documents'][0]['document_id'], 'test-doc-123')
    
    @patch('index.get_db_credentials')
    @patch('index.DatabaseConnector')
    def test_get_cylinder_inventory(self, mock_db_connector, mock_get_credentials):
        """Test getting cylinder inventory data"""
        # Set up mocks
        mock_db = MagicMock()
        mock_db.get_cylinder_inventory_data.return_value = self.test_inventory_data
        mock_db_connector.return_value = mock_db
        
        # Call the function
        response = get_cylinder_inventory(mock_db, 'Jan', '2016')
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(len(body['inventory_data']), 2)
        self.assertEqual(body['inventory_data'][0]['date'], '01/01/16')
        self.assertEqual(body['inventory_data'][0]['month'], 'Jan')
        self.assertEqual(body['inventory_data'][0]['year'], '2016')
    
    @patch('index.get_db_credentials')
    @patch('index.DatabaseConnector')
    def test_lambda_handler(self, mock_db_connector, mock_get_credentials):
        """Test lambda handler with different routes"""
        # Set up mocks
        mock_db = MagicMock()
        mock_db.get_recent_documents.return_value = self.test_documents
        mock_db.get_document_by_id.return_value = self.test_document
        mock_db.get_cylinder_inventory_data.return_value = self.test_inventory_data
        mock_db_connector.return_value = mock_db
        
        # Test get documents route
        event = {
            'httpMethod': 'GET',
            'path': '/documents',
            'queryStringParameters': None,
            'pathParameters': None
        }
        response = lambda_handler(event, None)
        self.assertEqual(response['statusCode'], 200)
        
        # Test get document route
        event = {
            'httpMethod': 'GET',
            'path': '/documents/{document_id}',
            'queryStringParameters': None,
            'pathParameters': {'document_id': 'test-doc-123'}
        }
        response = lambda_handler(event, None)
        self.assertEqual(response['statusCode'], 200)
        
        # Test get cylinder inventory route
        event = {
            'httpMethod': 'GET',
            'path': '/cylinder-inventory',
            'queryStringParameters': {'month': 'Jan', 'year': '2016'},
            'pathParameters': None
        }
        response = lambda_handler(event, None)
        self.assertEqual(response['statusCode'], 200)
        
        # Test route not found
        event = {
            'httpMethod': 'GET',
            'path': '/invalid-route',
            'queryStringParameters': None,
            'pathParameters': None
        }
        response = lambda_handler(event, None)
        self.assertEqual(response['statusCode'], 404)

if __name__ == '__main__':
    unittest.main()
