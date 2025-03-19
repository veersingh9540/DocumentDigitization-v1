import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add source directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/lambda/document_processor'))

import textract_helper

class TestTextractHelper(unittest.TestCase):
    
    @patch('boto3.client')
    def test_process_document_pdf(self, mock_boto3_client):
        # Mock the Textract client
        mock_textract = MagicMock()
        mock_boto3_client.return_value = mock_textract
        
        # Mock start_document_analysis response
        mock_textract.start_document_analysis.return_value = {
            'JobId': 'test-job-id'
        }
        
        # Mock get_document_analysis response
        mock_textract.get_document_analysis.return_value = {
            'JobStatus': 'SUCCEEDED',
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Test Line 1', 'Id': '1'},
                {'BlockType': 'LINE', 'Text': 'Test Line 2', 'Id': '2'}
            ]
        }
        
        # Create a temporary test file
        test_file = 'test_document.pdf'
        with open(test_file, 'w') as f:
            f.write('dummy content')
        
        try:
            # Patch the extract_text_and_tables function
            with patch('textract_helper.extract_text_and_tables', return_value=('Sample text', [['data']])):
                # Call the function
                raw_text, table_data = textract_helper.process_document(test_file)
                
                # Assert Textract was called correctly
                mock_textract.start_document_analysis.assert_called_once()
                
                # Assert the function returned expected values
                self.assertEqual(raw_text, 'Sample text')
                self.assertEqual(table_data, [['data']])
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
