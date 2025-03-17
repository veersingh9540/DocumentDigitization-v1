#!/bin/bash

# Script to package Lambda functions

# Change to document processor directory
cd src/lambda/document_processor
pip install -r requirements.txt -t .
zip -r ../../../document_processor.zip .

# Change to dashboard API directory here


cd ../dashboard_api
pip install -r requirements.txt -t .
zip -r ../../../dashboard_api.zip .

echo "Lambda packages created successfully!"
