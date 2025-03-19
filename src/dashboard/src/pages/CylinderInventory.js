import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Divider,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { fetchCylinderInventory } from '../services/api';

const months = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

const CylinderInventory = () => {
  const [inventoryData, setInventoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [month, setMonth] = useState('');
  const [year, setYear] = useState('');
  const [yearOptions, setYearOptions] = useState([]);
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    loadInventoryData();
  }, []);

  const loadInventoryData = async (selectedMonth = '', selectedYear = '') => {
    try {
      setLoading(true);
      const data = await fetchCylinderInventory(selectedMonth, selectedYear);
      setInventoryData(data);
      
      // Extract unique years for filter
      const years = [...new Set(data.map(item => item.year))].filter(Boolean).sort();
      setYearOptions(years);
      
      // Prepare chart data
      prepareChartData(data);
      
      setError(null);
    } catch (err) {
      console.error('Error fetching cylinder inventory data:', err);
      setError('Failed to load inventory data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = () => {
    loadInventoryData(month, year);
  };

  const handleReset = () => {
    setMonth('');
    setYear('');
    loadInventoryData();
  };

  const prepareChartData = (data) => {
    // Group data by date
    const groupedData = data.reduce((acc, item) => {
      const date = `${item.date}-${item.month}-${item.year}`;
      if (!acc[date]) {
        acc[date] = {
          date,
          openingStock: parseFloat(item.opening_stock) || 0,
          closingStock: parseFloat(item.closing_stock) || 0,
          receipt: parseFloat(item.receipt) || 0,
        };
      }
      return acc;
    }, {});

    // Convert to array and sort by date
    const chartData = Object.values(groupedData).sort((a, b) => {
      const dateA = a.date.split('-');
      const dateB = b.date.split('-');
      if (dateA[2] !== dateB[2]) return dateA[2] - dateB[2];
      const monthIndexA = months.indexOf(dateA[1]);
      const monthIndexB = months.indexOf(dateB[1]);
      if (monthIndexA !== monthIndexB) return monthIndexA - monthIndexB;
      return dateA[0] - dateB[0];
    });

    setChartData(chartData.slice(0, 30)); // Limit to 30 points for better visualization
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Cylinder Inventory
      </Typography>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth>
              <InputLabel id="month-label">Month</InputLabel>
              <Select
                labelId="month-label"
                value={month}
                label="Month"
                onChange={(e) => setMonth(e.target.value)}
              >
                <MenuItem value="">All Months</MenuItem>
                {months.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth>
              <InputLabel id="year-label">Year</InputLabel>
              <Select
                labelId="year-label"
                value={year}
                label="Year"
                onChange={(e) => setYear(e.target.value)}
              >
                <MenuItem value="">All Years</MenuItem>
                {yearOptions.map((y) => (
                  <MenuItem key={y} value={y}>
                    {y}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              onClick={handleFilter}
            >
              Apply Filter
            </Button>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Button
              fullWidth
              variant="outlined"
              onClick={handleReset}
            >
              Reset
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {loading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : (
        <>
          {/* Charts */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Cylinder Stock Trends
            </Typography>
            <Box sx={{ height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="openingStock"
                    name="Opening Stock"
                    stroke="#8884d8"
                    activeDot={{ r: 8 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="closingStock"
                    name="Closing Stock"
                    stroke="#82ca9d"
                  />
                  <Line
                    type="monotone"
                    dataKey="receipt"
                    name="Receipt"
                    stroke="#ff7300"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Paper>

          {/* Inventory Table */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Cylinder Inventory Records
              {month && ` - ${month}`}
              {year && ` ${year}`}
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            {inventoryData.length === 0 ? (
              <Alert severity="info">
                No inventory data found for the selected filters.
              </Alert>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell>Month/Year</TableCell>
                      <TableCell align="right">Opening Stock</TableCell>
                      <TableCell align="right">Receipt</TableCell>
                      <TableCell align="right">Total Stock</TableCell>
                      <TableCell align="right">Closing Stock</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {inventoryData.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell>{item.date}</TableCell>
                        <TableCell>{`${item.month} ${item.year}`}</TableCell>
                        <TableCell align="right">{item.opening_stock}</TableCell>
                        <TableCell align="right">{item.receipt}</TableCell>
                        <TableCell align="right">{item.total_stock}</TableCell>
                        <TableCell align="right">{item.closing_stock}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </>
      )}
    </Box>
  );
};

export default CylinderInventory;
