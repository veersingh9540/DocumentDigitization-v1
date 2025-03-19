import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Divider,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { fetchDocumentStatistics } from '../services/api';

// Chart colors
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#4CAF50', '#F44336'];

const Analytics = () => {
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await fetchDocumentStatistics();
        setStatistics(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching analytics data:', err);
        setError('Failed to load analytics data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Analytics
        </Typography>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!statistics) {
    return (
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Analytics
        </Typography>
        <Alert severity="info">No analytics data available. Upload some documents to see analytics.</Alert>
      </Box>
    );
  }

  // Prepare data for charts
  const typeData = Object.entries(statistics.by_type || {}).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value
  }));

  const dailyData = statistics.daily_counts?.map(item => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    count: item.count
  })) || [];

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Analytics
      </Typography>

      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h3" component="div" align="center">
                {statistics.total_documents || 0}
              </Typography>
              <Typography color="text.secondary" align="center">
                Total Documents
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h3" component="div" align="center">
                {Object.keys(statistics.by_type || {}).length}
              </Typography>
              <Typography color="text.secondary" align="center">
                Document Types
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h3" component="div" align="center">
                {statistics.daily_counts?.reduce((sum, item) => sum + item.count, 0) || 0}
              </Typography>
              <Typography color="text.secondary" align="center">
                Last 7 Days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Document Types Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Documents by Type
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {typeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value} documents`, 'Count']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Daily Counts Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Documents Processed (Last 7 Days)
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip formatter={(value) => [`${value} documents`, 'Count']} />
                <Legend />
                <Bar dataKey="count" name="Documents" fill="#1976d2" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Document Type Distribution Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Document Type Distribution
            </Typography>
            <Divider sx={{ mb: 2 }} />
            {typeData.length > 0 ? (
              <Grid container spacing={2}>
                {typeData.map((type, index) => (
                  <Grid item xs={12} sm={6} md={3} key={type.name}>
                    <Card variant="outlined" sx={{ bgcolor: `${COLORS[index % COLORS.length]}10` }}>
                      <CardContent>
                        <Typography variant="h6" component="div" gutterBottom>
                          {type.name}
                        </Typography>
                        <Box display="flex" alignItems="center">
                          <Box
                            sx={{
                              width: 16,
                              height: 16,
                              borderRadius: '50%',
                              bgcolor: COLORS[index % COLORS.length],
                              mr: 1,
                            }}
                          />
                          <Typography variant="h4">{type.value}</Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          {((type.value / statistics.total_documents) * 100).toFixed(1)}% of total
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography variant="body1" color="text.secondary" align="center">
                No document type data available
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Analytics;
