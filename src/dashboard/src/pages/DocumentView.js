import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Divider,
  Chip,
  Card,
  CardContent,
  CardHeader,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Skeleton,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Description as DocumentIcon,
  Receipt as InvoiceIcon,
  Assignment as ReportIcon,
  FileCopy as ContractIcon,
  Download as DownloadIcon,
  InsertDriveFile as UnknownIcon,
} from '@mui/icons-material';
import { fetchDocumentById } from '../services/api';

// Document icon mapper
const getDocumentIcon = (docType) => {
  switch(docType) {
    case 'invoice':
      return <InvoiceIcon fontSize="large" />;
    case 'report':
      return <ReportIcon fontSize="large" />;
    case 'contract':
      return <ContractIcon fontSize="large" />;
    default:
      return <UnknownIcon fontSize="large" />;
  }
};

// Document type color mapper
const getDocumentColor = (docType) => {
  switch(docType) {
    case 'invoice':
      return 'primary';
    case 'report':
      return 'success';
    case 'contract':
      return 'secondary';
    default:
      return 'default';
  }
};

const DocumentView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        setLoading(true);
        const data = await fetchDocumentById(id);
        setDocument(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching document:', err);
        setError('Failed to load document. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchDocument();
    }
  }, [id]);

  const handleDownload = () => {
    // In a real app, this would download the document from S3
    // This is a placeholder implementation
    if (document && document.metadata) {
      const s3Url = `https://${document.metadata.processed_bucket}.s3.amazonaws.com/${document.metadata.processed_key}`;
      window.open(s3Url, '_blank');
    }
  };

  if (loading) {
    return (
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <IconButton onClick={() => navigate(-1)}>
            <BackIcon />
          </IconButton>
          <Skeleton variant="text" width={300} height={40} />
        </Box>
        <Paper sx={{ p: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Skeleton variant="rectangular" height={200} />
            </Grid>
            <Grid item xs={12} md={8}>
              <Skeleton variant="text" height={40} />
              <Skeleton variant="text" />
              <Skeleton variant="text" />
              <Skeleton variant="text" width="60%" />
            </Grid>
          </Grid>
        </Paper>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <IconButton onClick={() => navigate(-1)}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            Document Details
          </Typography>
        </Box>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button variant="contained" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </Box>
    );
  }

  if (!document) {
    return (
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <IconButton onClick={() => navigate(-1)}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            Document Not Found
          </Typography>
        </Box>
        <Alert severity="warning" sx={{ mb: 3 }}>
          The document you are looking for does not exist or has been removed.
        </Alert>
        <Button variant="contained" onClick={() => navigate('/documents')}>
          View All Documents
        </Button>
      </Box>
    );
  }

  const { metadata, fields } = document;

  return (
    <Box>
      <Box display="flex" alignItems="center" mb={3}>
        <IconButton onClick={() => navigate(-1)} sx={{ mr: 1 }}>
          <BackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          Document Details
        </Typography>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4} md={3}>
            <Box display="flex" flexDirection="column" alignItems="center">
              {getDocumentIcon(metadata.document_type)}
              <Chip
                label={metadata.document_type.charAt(0).toUpperCase() + metadata.document_type.slice(1)}
                color={getDocumentColor(metadata.document_type)}
                sx={{ mt: 1 }}
              />
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownload}
                sx={{ mt: 2 }}
              >
                Download
              </Button>
            </Box>
          </Grid>
          <Grid item xs={12} sm={8} md={9}>
            <Typography variant="h5" gutterBottom>
              {metadata.document_id}
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body1">
                  {metadata.status.charAt(0).toUpperCase() + metadata.status.slice(1)}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Processed Date
                </Typography>
                <Typography variant="body1">
                  {new Date(metadata.created_at).toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Page Count
                </Typography>
                <Typography variant="body1">
                  {metadata.page_count}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Document ID
                </Typography>
                <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
                  {metadata.document_id}
                </Typography>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </Paper>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardHeader title="Extracted Fields" />
        <Divider />
        <CardContent>
          {Object.keys(fields).length === 0 ? (
            <Typography variant="body1" color="text.secondary" align="center">
              No fields were extracted from this document
            </Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Field</TableCell>
                    <TableCell>Value</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(fields).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>
                        <Typography variant="subtitle2">
                          {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                        </Typography>
                      </TableCell>
                      <TableCell>{value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardHeader title="Document Metadata" />
        <Divider />
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Property</TableCell>
                  <TableCell>Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Original Bucket</TableCell>
                  <TableCell>{metadata.original_bucket}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Original Key</TableCell>
                  <TableCell>{metadata.original_key}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Processed Bucket</TableCell>
                  <TableCell>{metadata.processed_bucket}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Processed Key</TableCell>
                  <TableCell>{metadata.processed_key}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default DocumentView;
