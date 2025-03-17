// Lambda function for dashboard API
exports.handler = async (event) => {
    console.log('Dashboard API event:', JSON.stringify(event, null, 2));
    
    try {
      // Get environment variables
      const s3BucketName = process.env.S3_BUCKET || 'default-documents-bucket';
      const dbEndpoint = process.env.DB_ENDPOINT || 'localhost:5432';
      
      // Parse request path and method
      const path = event.path || '';
      const httpMethod = event.httpMethod || 'GET';
      const queryParams = event.queryStringParameters || {};
      
      // Handle different API endpoints
      let response;
      
      if (path.includes('/documents') && httpMethod === 'GET') {
        // Return a list of documents (mock data for demonstration)
        response = {
          statusCode: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          },
          body: JSON.stringify({
            documents: [
              { id: '001', name: 'Report-2023.pdf', status: 'processed', uploadDate: '2023-01-15' },
              { id: '002', name: 'Invoice-1234.pdf', status: 'processing', uploadDate: '2023-01-16' },
              { id: '003', name: 'Contract.docx', status: 'processed', uploadDate: '2023-01-17' }
            ],
            bucket: s3BucketName,
            timestamp: new Date().toISOString()
          })
        };
      } else if (path.includes('/stats') && httpMethod === 'GET') {
        // Return dashboard statistics (mock data for demonstration)
        response = {
          statusCode: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          },
          body: JSON.stringify({
            stats: {
              totalDocuments: 324,
              processedDocuments: 289,
              pendingDocuments: 35,
              averageProcessingTime: '45s'
            },
            database: dbEndpoint,
            timestamp: new Date().toISOString()
          })
        };
      } else {
        // Default response for root or unknown paths
        response = {
          statusCode: 200,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          },
          body: JSON.stringify({
            message: 'Dashboard API is running',
            endpoints: ['/documents', '/stats'],
            timestamp: new Date().toISOString()
          })
        };
      }
      
      return response;
    } catch (error) {
      console.error('Error in dashboard API:', error);
      
      return {
        statusCode: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify({
          message: 'Error processing request',
          error: error.message
        })
      };
    }
  };
