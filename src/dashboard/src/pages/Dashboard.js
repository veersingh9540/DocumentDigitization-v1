import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  Button,
  Card,
  CardContent,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Divider
} from '@mui/material';
import { 
  Description as DocumentIcon,
  Receipt as InvoiceIcon,
  Assignment as ReportIcon,
  InsertDriveFile as FileIcon,
  FilePresent as GenericIcon
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import { Link as RouterLink } from 'react-router-dom';

import { fetchDocumentStatistics, fetchRecentDocuments } from '../services/api';

// Document icon mapper
const getDocumentIcon = (docType) => {
  switch(docType) {
    case 'invoice':
      return <InvoiceIcon />;
    case 'report':
      return <ReportIcon />;
    case 'contract':
      return <DocumentIcon />;
    default:
      return <GenericIcon />;
  }
};

const Dashboard = () => {
  const [statistics, setStatistics] = useState(null);
  const [recentDocuments, setRecentDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, documentsData] = await Promise.all([
          fetchDocumentStatistics(),
          fetchRecentDocuments(5)
        ]);
        
        setStatistics(statsData);
        setRecentDocuments(documentsData);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Prepare chart data
  const chartData = statistics?.daily_counts?.map(item => ({
    date: format(new Date(item.date), 'MMM dd'),
    documents: item.count
  })) || [];

  // Prepare document type data for pie chart
  const documentTypeData = statistics?.by_type ? 
    Object.entries(statistics.by_type).map(([type, count]) => ({
      name: type.charAt(0).toUpperCase() + type.slice(1),
      value: count
    })) : [];

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>

      {loading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Paper sx={{ p: 3, mb: 3, backgroundColor: '#fff9f9' }}>
          <Typography color="error">{error}</Typography>
          <Button 
            variant="outlined" 
            color="primary" 
            sx={{ mt: 2 }}
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {/* Stats cards */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Total Documents
              </Typography>
              <Typography component="p" variant="h3">
                {statistics?.total_documents || 0}
              </Typography>
              <Typography color="text.secondary" sx={{ flex: 1 }}>
                Documents processed
              </Typography>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Recent Documents
              </Typography>
              <Typography component="p" variant="h3">
                {statistics?.daily_counts?.reduce((sum, item) => sum + item.count, 0) || 0}
              </Typography>
              <Typography color="text.secondary" sx={{ flex: 1 }}>
                Processed in the last 7 days
              </Typography>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Document Types
              </Typography>
              <Typography component="p" variant="h3">
                {documentTypeData.length || 0}
              </Typography>
              <Typography color="text.secondary" sx={{ flex: 1 }}>
                Different document types
              </Typography>
            </Paper>
          </Grid>

          {/* Charts */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Documents Processed (Last 7 Days)
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="documents" name="Documents" fill="#1976d2" />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </Grid>

          {/* Recent documents */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Recent Documents
              </Typography>
              <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
                {recentDocuments.length > 0 ? (
                  recentDocuments.map((doc, index) => (
                    <React.Fragment key={doc.document_id}>
                      <ListItem 
                        alignItems="flex-start"
                        button
                        component={RouterLink}
                        to={`/documents/${doc.document_id}`}
                      >
                        <ListItemAvatar>
                          <Avatar>
                            {getDocumentIcon(doc.document_type)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={doc.document_id}
                          secondary={
                            <>
                              <Typography
                                sx={{ display: 'inline' }}
                                component="span"
                                variant="body2"
                                color="text.primary"
                              >
                                {doc.document_type.charAt(0).toUpperCase() + doc.document_type.slice(1)}
                              </Typography>
                              {" — "}
                              {new Date(doc.created_at).toLocaleDateString()}
                            </>
                          }
                        />
                      </ListItem>
                      {index < recentDocuments.length - 1 && <Divider variant="inset" component="li" />}
                    </React.Fragment>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText
                      primary="No documents found"
                      secondary="Upload some documents to get started"
                    />
                  </ListItem>
                )}
              </List>
              <Box mt={2} display="flex" justifyContent="flex-end">
                <Button 
                  component={RouterLink} 
                  to="/documents" 
                  color="primary"
                >
                  View all documents
                </Button>
              </Box>
            </Paper>
          </Grid>
          
          {/* Document types distribution */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography component="h2" variant="h6" color="primary" gutterBottom>
                Document Types Distribution
              </Typography>
              <Grid container spacing={2}>
                {documentTypeData.map((type) => (
                  <Grid item xs={6} sm={4} md={3} lg={2} key={type.name}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box display="flex" alignItems="center" mb={1}>
                          <Avatar sx={{ bgcolor: 'primary.main', mr: 1 }}>
                            {getDocumentIcon(type.name.toLowerCase())}
                          </Avatar>
                          <Typography variant="h6" component="div">
                            {type.name}
                          </Typography>
                        </Box>
                        <Typography variant="h4" component="div" align="center">
                          {type.value}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" align="center">
                          documents
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default Dashboard;
