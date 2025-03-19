import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  InputAdornment,
  IconButton,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  Description as DocumentIcon,
  Receipt as InvoiceIcon,
  Assignment as ReportIcon,
  FileCopy as ContractIcon,
  InsertDriveFile as UnknownIcon,
} from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { fetchDocuments, searchDocuments } from '../services/api';

// Document icon mapper
const getDocumentIcon = (docType) => {
  switch(docType) {
    case 'invoice':
      return <InvoiceIcon />;
    case 'report':
      return <ReportIcon />;
    case 'contract':
      return <ContractIcon />;
    default:
      return <UnknownIcon />;
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

const Documents = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('date');

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await fetchDocuments(50);
      setDocuments(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching documents:', err);
      setError('Failed to load documents. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      return loadDocuments();
    }

    try {
      setLoading(true);
      const data = await searchDocuments(searchQuery);
      setDocuments(data);
      setError(null);
    } catch (err) {
      console.error('Error searching documents:', err);
      setError('Failed to search documents. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    loadDocuments();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Filter documents based on document type
  const filteredDocuments = documents.filter(doc => {
    if (filter === 'all') return true;
    return doc.document_type === filter;
  });

  // Sort documents
  const sortedDocuments = [...filteredDocuments].sort((a, b) => {
    if (sortBy === 'date') {
      return new Date(b.created_at) - new Date(a.created_at);
    } else if (sortBy === 'name') {
      return a.document_id.localeCompare(b.document_id);
    } else if (sortBy === 'type') {
      return a.document_type.localeCompare(b.document_type);
    }
    return 0;
  });

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Documents
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
                endAdornment: searchQuery && (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      aria-label="clear search"
                      onClick={handleClearSearch}
                    >
                      <ClearIcon />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Search'}
            </Button>
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <FormControl fullWidth>
              <InputLabel id="filter-label">Filter</InputLabel>
              <Select
                labelId="filter-label"
                value={filter}
                label="Filter"
                onChange={(e) => setFilter(e.target.value)}
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="invoice">Invoices</MenuItem>
                <MenuItem value="report">Reports</MenuItem>
                <MenuItem value="contract">Contracts</MenuItem>
                <MenuItem value="unknown">Unknown</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <FormControl fullWidth>
              <InputLabel id="sort-label">Sort By</InputLabel>
              <Select
                labelId="sort-label"
                value={sortBy}
                label="Sort By"
                onChange={(e) => setSortBy(e.target.value)}
              >
                <MenuItem value="date">Date (newest first)</MenuItem>
                <MenuItem value="name">Name (A-Z)</MenuItem>
                <MenuItem value="type">Document Type</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && !documents.length ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : !sortedDocuments.length ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No documents found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchQuery
              ? 'Try using different search terms or clear the search.'
              : 'Upload some documents to get started.'}
          </Typography>
          <Button
            component={RouterLink}
            to="/upload"
            variant="contained"
            color="primary"
            sx={{ mt: 2 }}
          >
            Upload Documents
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {sortedDocuments.map((doc) => (
            <Grid item xs={12} sm={6} md={4} key={doc.document_id}>
              <Card variant="outlined">
                <CardContent>
                  <Box display="flex" alignItems="center" mb={1}>
                    {getDocumentIcon(doc.document_type)}
                    <Typography variant="h6" component="div" ml={1}>
                      {doc.document_id.split('-')[0]}
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 1 }} />
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Chip
                      label={doc.document_type.charAt(0).toUpperCase() + doc.document_type.slice(1)}
                      color={getDocumentColor(doc.document_type)}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    component={RouterLink}
                    to={`/documents/${doc.document_id}`}
                    size="small"
                    color="primary"
                  >
                    View Details
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default Documents;
