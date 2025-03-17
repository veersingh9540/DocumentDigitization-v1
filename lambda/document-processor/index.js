// Lambda function for document processing
exports.handler = async (event) => {
    console.log('Processing document event:', JSON.stringify(event, null, 2));
    
    try {
      // Get S3 bucket name from environment variable
      const s3BucketName = process.env.S3_BUCKET || 'default-documents-bucket';
      
      // Example logic for document processing
      let response;
      
      if (event.Records && event.Records[0].s3) {
        // This is an S3 event trigger
        const s3Event = event.Records[0].s3;
        const bucketName = s3Event.bucket.name;
        const objectKey = s3Event.object.key;
        
        console.log(`Processing document from S3: ${bucketName}/${objectKey}`);
        
        // Here you would add your document processing logic
        // For example, extract text, analyze content, store in database, etc.
        
        response = {
          statusCode: 200,
          body: JSON.stringify({
            message: 'Document processed successfully',
            document: {
              bucket: bucketName,
              key: objectKey
            }
          })
        };
      } else {
        // This is a direct invocation
        response = {
          statusCode: 200,
          body: JSON.stringify({
            message: 'Document processor ready',
            timestamp: new Date().toISOString()
          })
        };
      }
      
      return response;
    } catch (error) {
      console.error('Error processing document:', error);
      
      return {
        statusCode: 500,
        body: JSON.stringify({
          message: 'Error processing document',
          error: error.message
        })
      };
    }
  };
