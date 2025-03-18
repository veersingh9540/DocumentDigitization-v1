import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const CylinderDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState([]);
  const [monthlySummary, setMonthlySummary] = useState({
    months: [],
    filled_cylinders: [],
    empty_cylinders: []
  });
  const [summary, setSummary] = useState(null);
  const [dateRange, setDateRange] = useState({
    startDate: '2016-01-01',
    endDate: '2016-12-31'
  });

  // Fetch data on component mount and when date range changes
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch all stats
        const statsResponse = await fetch(`${API_URL}/stats?start_date=${dateRange.startDate}&end_date=${dateRange.endDate}`);
        
        if (!statsResponse.ok) {
          throw new Error(`Failed to fetch stats: ${statsResponse.statusText}`);
        }
        
        const statsData = await statsResponse.json();
        
        // Fetch monthly data for charts
        const monthlyResponse = await fetch(`${API_URL}/stats/monthly?start_date=${dateRange.startDate}&end_date=${dateRange.endDate}`);
        
        if (!monthlyResponse.ok) {
          throw new Error(`Failed to fetch monthly data: ${monthlyResponse.statusText}`);
        }
        
        const monthlyData = await monthlyResponse.json();
        
        // Fetch summary stats
        const summaryResponse = await fetch(`${API_URL}/stats/summary?start_date=${dateRange.startDate}&end_date=${dateRange.endDate}`);
        
        if (!summaryResponse.ok) {
          throw new Error(`Failed to fetch summary: ${summaryResponse.statusText}`);
        }
        
        const summaryData = await summaryResponse.json();
        
        setStats(statsData.stats || []);
        setMonthlySummary(monthlyData);
        setSummary(summaryData);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dateRange]);

  // Handler for date range changes
  const handleDateRangeChange = (e) => {
    const { name, value } = e.target;
    setDateRange(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Calculate color based on value (for trend indicators)
  const getTrendColor = (value) => {
    if (value > 0) return '#4caf50';
    if (value < 0) return '#f44336';
    return '#9e9e9e';
  };

  // Format dates for display
  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  };
  
  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading dashboard data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <div className="error-icon">❌</div>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Try Again</button>
      </div>
    );
  }

  return (
    <div className="cylinder-dashboard">
      <div className="dashboard-header">
        <h1>Cylinder Inventory Dashboard</h1>
        
        <div className="date-filters">
          <div className="date-filter">
            <label htmlFor="startDate">Start Date:</label>
            <input
              type="date"
              id="startDate"
              name="startDate"
              value={dateRange.startDate}
              onChange={handleDateRangeChange}
            />
          </div>
          
          <div className="date-filter">
            <label htmlFor="endDate">End Date:</label>
            <input
              type="date"
              id="endDate"
              name="endDate"
              value={dateRange.endDate}
              onChange={handleDateRangeChange}
            />
          </div>
        </div>
      </div>
      
      {summary && (
        <div className="summary-stats">
          <div className="stat-card">
            <h3>Documents Processed</h3>
            <div className="stat-value">{summary.total_documents}</div>
          </div>
          
          <div className="stat-card">
            <h3>Total Transactions</h3>
            <div className="stat-value">{summary.total_transactions}</div>
          </div>
          
          <div className="stat-card">
            <h3>Avg. Filled Cylinder Stock</h3>
            <div className="stat-value">{summary.filled_cylinders.avg_closing_stock}</div>
            <div 
              className="trend-indicator" 
              style={{ color: getTrendColor(summary.filled_cylinders.avg_closing_stock - summary.filled_cylinders.avg_opening_stock) }}
            >
              {summary.filled_cylinders.avg_closing_stock > summary.filled_cylinders.avg_opening_stock ? '↑' : 
               summary.filled_cylinders.avg_closing_stock < summary.filled_cylinders.avg_opening_stock ? '↓' : '→'}
            </div>
          </div>
          
          <div className="stat-card">
            <h3>Avg. Empty Cylinder Stock</h3>
            <div className="stat-value">{summary.empty_cylinders.avg_closing_stock}</div>
            <div 
              className="trend-indicator" 
              style={{ color: getTrendColor(summary.empty_cylinders.avg_closing_stock - summary.empty_cylinders.avg_opening_stock) }}
            >
              {summary.empty_cylinders.avg_closing_stock > summary.empty_cylinders.avg_opening_stock ? '↑' : 
               summary.empty_cylinders.avg_closing_stock < summary.empty_cylinders.avg_opening_stock ? '↓' : '→'}
            </div>
          </div>
        </div>
      )}
      
      <div className="chart-container">
        <div className="chart-wrapper">
          <h2>Filled Cylinders Trends</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={monthlySummary.filled_cylinders}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="opening_stock" stroke="#8884d8" name="Opening Stock" />
              <Line type="monotone" dataKey="closing_stock" stroke="#82ca9d" name="Closing Stock" />
              <Line type="monotone" dataKey="receipts" stroke="#ffc658" name="Receipts" />
              <Line type="monotone" dataKey="issues" stroke="#ff8042" name="Issues" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="chart-wrapper">
          <h2>Empty Cylinders Trends</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={monthlySummary.empty_cylinders}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="opening_stock" stroke="#8884d8" name="Opening Stock" />
              <Line type="monotone" dataKey="closing_stock" stroke="#82ca9d" name="Closing Stock" />
              <Line type="monotone" dataKey="receipts" stroke="#ffc658" name="Receipts" />
              <Line type="monotone" dataKey="returns" stroke="#ff8042" name="Returns" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div className="chart-container">
        <div className="chart-wrapper">
          <h2>Monthly Cylinder Transactions</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={monthlySummary.months.map((month, index) => {
              const filledData = monthlySummary.filled_cylinders[index] || {};
              const emptyData = monthlySummary.empty_cylinders[index] || {};
              
              return {
                month,
                filled_receipts: filledData.receipts || 0,
                filled_issues: filledData.issues || 0,
                empty_receipts: emptyData.receipts || 0,
                empty_returns: emptyData.returns || 0
              };
            })}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="filled_receipts" fill="#8884d8" name="Filled Receipts" />
              <Bar dataKey="filled_issues" fill="#82ca9d" name="Filled Issues" />
              <Bar dataKey="empty_receipts" fill="#ffc658" name="Empty Receipts" />
              <Bar dataKey="empty_returns" fill="#ff8042" name="Empty Returns" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        
        <div className="chart-wrapper">
          <h2>Net Stock Changes</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats.map(stat => {
              const filledChange = stat.filled_cylinders.net_change;
              const emptyChange = stat.empty_cylinders.net_change;
              
              return {
                month: stat.month_year,
                filled_change: filledChange,
                empty_change: emptyChange,
                net_change: filledChange + emptyChange
              };
            })}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="filled_change" fill="#8884d8" name="Filled Cylinders Change" />
              <Bar dataKey="empty_change" fill="#82ca9d" name="Empty Cylinders Change" />
              <Bar dataKey="net_change" fill="#ff8042" name="Net Change" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div className="data-table-container">
        <h2>Monthly Statistics</h2>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Period</th>
                <th colSpan="4">Filled Cylinders</th>
                <th colSpan="4">Empty Cylinders</th>
              </tr>
              <tr>
                <th></th>
                <th></th>
                <th>Opening</th>
                <th>Closing</th>
                <th>Receipts</th>
                <th>Issues</th>
                <th>Opening</th>
                <th>Closing</th>
                <th>Receipts</th>
                <th>Returns</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((stat, index) => (
                <tr key={index}>
                  <td>{stat.month_year}</td>
                  <td>{formatDate(stat.start_date)} - {formatDate(stat.end_date)}</td>
                  <td>{stat.filled_cylinders.opening_stock}</td>
                  <td>{stat.filled_cylinders.closing_stock}</td>
                  <td>{stat.filled_cylinders.receipts}</td>
                  <td>{stat.filled_cylinders.issues}</td>
                  <td>{stat.empty_cylinders.opening_stock}</td>
                  <td>{stat.empty_cylinders.closing_stock}</td>
                  <td>{stat.empty_cylinders.receipts}</td>
                  <td>{stat.empty_cylinders.returns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CylinderDashboard;
