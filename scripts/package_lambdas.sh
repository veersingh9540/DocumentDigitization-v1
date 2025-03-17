#!/bin/bash
# Script to package Lambda functions

# Clean up previous packages
rm -f document_processor.zip dashboard_api.zip

# Package document processor Lambda
echo "Packaging document processor Lambda..."
cd src/lambda/document_processor
pip install -r requirements.txt -t .
zip -r ../../../document_processor.zip .
cd ../../..

# Package dashboard API Lambda
echo "Packaging dashboard API Lambda..."
cd src/lambda/dashboard_api
pip install -r requirements.txt -t .
zip -r ../../../dashboard_api.zip .
cd ../../..

echo "Lambda functions packaged successfully!"
