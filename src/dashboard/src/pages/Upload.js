import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  AlertTitle,
  Stepper,
  Step,
  StepLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { getSignedUploadUrl, uploadToS3 } from '../services/api';

const Upload = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [activeStep, setActiveStep] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState({});
  const [error, setError] = useState(null);

  const steps = ['Select Files', 'Upload Files', 'Processing'];

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(acceptedFiles);
    setActiveStep(1);
  }, []);

  // Fixed the accept property to use the correct format
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff', '.tif'],
    },
    maxSize: 10485760, // 10MB
  });

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    setActiveStep(2);

    try {
      const newUploadStatus = { ...uploadStatus };
      
      // Upload each file
      for (const file of files) {
        try {
          newUploadStatus[file.name] = { status: 'uploading', progress: 0 };
          setUploadStatus({ ...newUploadStatus });

          console.log(`Requesting signed URL for ${file.name}`);
          // Get signed URL for S3 upload
          const signedUrlData = await getSignedUploadUrl(file.name, file.type);
          
          if (!signedUrlData || !signedUrlData.signedUrl) {
            throw new Error('Failed to get valid upload URL');
          }
          
          console.log(`Uploading ${file.name} to S3`);
          // Upload directly to S3
          await uploadToS3(signedUrlData.signedUrl, file);
          
          newUploadStatus[file.name] = { status: 'success' };
          setUploadStatus({ ...newUploadStatus });
          console.log(`Successfully uploaded ${file.name}`);
        } catch (fileError) {
          console.error('Error uploading file:', file.name, fileError);
          newUploadStatus[file.name] = { 
            status: 'error', 
            message: fileError.message || 'Upload failed' 
          };
          setUploadStatus({ ...newUploadStatus });
        }
      }

      // Check if all uploads were successful
      const allSuccess = Object.values(newUploadStatus).every(
        (status) => status.status === 'success'
      );

      if (allSuccess) {
        setActiveStep(3);
      } else {
        // Some uploads failed
        setError('Some files failed to upload. Please check the list below.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(`An error occurred during the upload process: ${err.message || 'Unknown error'}. Please try again.`);
    } finally {
      setUploading(false);
    }
  };

  const resetUpload = () => {
    setFiles([]);
    setActiveStep(0);
    setUploadStatus({});
    setError(null);
  };

  const renderFileList = () => {
    if (files.length === 0) {
      return (
        <Typography variant="body1" color="text.secondary" align="center">
          No files selected
        </Typography>
      );
    }

    return (
      <List>
        {files.map((file, index) => {
          const status = uploadStatus[file.name];
          const isUploading = status?.status === 'uploading';
          const isSuccess = status?.status === 'success';
          const isError = status?.status === 'error';

          return (
            <React.Fragment key={file.name}>
              <ListItem>
                <ListItemIcon>
                  {isSuccess ? (
                    <CheckIcon color="success" />
                  ) : isError ? (
                    <ErrorIcon color="error" />
                  ) : (
                    <FileIcon color="primary" />
                  )}
                </ListItemIcon>
                <ListItemText
                  primary={file.name}
                  secondary={
                    <>
                      {`${(file.size / 1024 / 1024).toFixed(2)} MB - ${file.type}`}
                      {isError && status.message && (
                        <Typography color="error" variant="caption" display="block">
                          Error: {status.message}
                        </Typography>
                      )}
                    </>
                  }
                />
                {isUploading && <CircularProgress size={24} />}
              </ListItem>
              {index < files.length - 1 && <Divider variant="inset" component="li" />}
            </React.Fragment>
          );
        })}
      </List>
    );
  };

  // Alternative approach: Direct upload to endpoint instead of S3 signed URL
  const handleDirectUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }

    setUploading(true);
    setError(null);
    setActiveStep(2);

    try {
      const newUploadStatus = { ...uploadStatus };
      let successCount = 0;
      
      // Create a FormData object
      const formData = new FormData();
      
      // Add each file to the FormData
      files.forEach(file => {
        formData.append('files', file);
        newUploadStatus[file.name] = { status: 'uploading', progress: 0 };
      });
      
      setUploadStatus({ ...newUploadStatus });
      
      // Make a single request with all files
      // This is a fallback in case the signed URL approach doesn't work
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Update status for each file
      files.forEach(file => {
        if (result.success && result.files && result.files[file.name]) {
          newUploadStatus[file.name] = { status: 'success' };
          successCount++;
        } else {
          newUploadStatus[file.name] = { 
            status: 'error', 
            message: (result.errors && result.errors[file.name]) || 'Upload failed'
          };
        }
      });
      
      setUploadStatus({ ...newUploadStatus });
      
      if (successCount === files.length) {
        setActiveStep(3);
      } else {
        setError('Some files failed to upload. Please check the list below.');
      }
    } catch (err) {
      console.error('Direct upload error:', err);
      setError(`Upload failed: ${err.message || 'Unknown error'}`);
      
      // Mark all files as failed
      const failedStatus = {};
      files.forEach(file => {
        failedStatus[file.name] = { status: 'error', message: err.message || 'Upload failed' };
      });
      setUploadStatus(failedStatus);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Upload Documents
      </Typography>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <AlertTitle>Error</AlertTitle>
          {error}
        </Alert>
      )}

      {activeStep === 0 && (
        <Paper
          {...getRootProps()}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'divider',
            backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
            cursor: 'pointer',
          }}
        >
          <input {...getInputProps()} />
          <UploadIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
          <Typography variant="h6" align="center" gutterBottom>
            {isDragActive
              ? 'Drop the files here...'
              : 'Drag and drop files here, or click to select files'}
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Supported file types: PDF, JPG, PNG, TIFF (max 10MB)
          </Typography>
        </Paper>
      )}

      {activeStep > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Selected Files
          </Typography>
          {renderFileList()}
        </Paper>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
        {activeStep > 0 && (
          <Button
            variant="outlined"
            onClick={resetUpload}
            sx={{ mr: 1 }}
            disabled={uploading}
          >
            Start Over
          </Button>
        )}

        {activeStep === 1 && (
          <Button
            variant="contained"
            color="primary"
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
            startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </Button>
        )}

        {activeStep === 3 && (
          <Button
            variant="contained"
            color="primary"
            onClick={() => navigate('/documents')}
          >
            View Documents
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default Upload;
