import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/lambda/document_processor'))

import unittest
from unittest.mock import patch, MagicMock
import textract_helper

class TestTextractHelper(unittest.TestCase):
    
    @patch('boto3.client')
    def test_process_document_jpg(self, mock_boto3_client):
        # Mock the Textract response
        mock_textract = MagicMock()
        mock_textract.analyze_document.return_value = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Test Line 1'},
                {'BlockType': 'LINE', 'Text': 'Test Line 2'}
            ]
        }
        mock_boto3_client.return_value = mock_textract
        
        # Create a temporary test file
        test_file = 'test_document.jpg'
        with open(test_file, 'w') as f:
            f.write('dummy content')
        
        try:
            # Call the function
            with patch('textract_helper.extract_text_and_tables', return_value=('Sample text', [])):
                raw_text, table_data = textract_helper.process_document(test_file)
                
                # Assert Textract was called with correct parameters
                mock_textract.analyze_document.assert_called_once()
                
                # Assert the function returned expected values
                self.assertEqual(raw_text, 'Sample text')
                self.assertEqual(table_data, [])
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
