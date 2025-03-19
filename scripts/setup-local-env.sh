#!/bin/bash

# Script to set up local development environment for document processing system
set -e

echo "Setting up local development environment for Document Processing System"
echo "----------------------------------------------------------------------"

# Check for required tools
echo "Checking for required tools..."
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting."; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "pip3 is required but not installed. Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting."; exit 1; }

echo "All required tools are installed."

# Create virtual environments for Lambda functions
echo "Creating Python virtual environments for Lambda functions..."

# Document processor Lambda
echo "Setting up document processor Lambda environment..."
cd src/lambda/document_processor
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
echo "Document processor Lambda environment setup complete."

# Dashboard API Lambda
echo "Setting up dashboard API Lambda environment..."
cd ../../lambda/dashboard_api
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
echo "Dashboard API Lambda environment setup complete."

# Return to project root
cd ../../../

# Set up local PostgreSQL database using Docker
echo "Setting up local PostgreSQL database with Docker..."
docker run --name doc-processing-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=documentdb -d -p 5432:5432 postgres:14

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
sleep 5

# Initialize database schema
echo "Initializing database schema..."
docker exec -i doc-processing-postgres psql -U postgres -d documentdb < scripts/init.sql
echo "Database schema initialized."

# Set up frontend
echo "Setting up frontend..."
cd src/dashboard
npm install
echo "Frontend setup complete."

# Create .env file for local development
echo "Creating .env file for local development..."
echo "REACT_APP_API_URL=http://localhost:3001" > .env.local
echo "Environment variables set up."

# Start local development server
echo "Starting React development server..."
npm start &

# Set up local API server for testing
cd ../..
echo "Setting up local API server for testing..."
cd tests
python3 -m venv venv
source venv/bin/activate
pip3 install flask flask-cors psycopg2-binary boto3 pytest pytest-mock
cd ..

# Create sample configuration for local testing
cat > .env.local << EOF
AWS_REGION=us-east-1
DB_HOST=localhost
DB_PORT=5432
DB_NAME=documentdb
DB_USER=postgres
DB_PASSWORD=postgres
UPLOAD_BUCKET=document-processing-documents-dev
EOF

echo "----------------------------------------------------------------------"
echo "Local development environment setup complete!"
echo "Frontend: http://localhost:3000"
echo "Local API: http://localhost:3001"
echo "PostgreSQL: localhost:5432 (User: postgres, Password: postgres, DB: documentdb)"
echo ""
echo "To start the local API server: python tests/mock_api_server.py"
echo "To run tests: cd tests && pytest"
echo "----------------------------------------------------------------------"
