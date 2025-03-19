import React from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { SentimentDissatisfied as SadIcon } from '@mui/icons-material';

const NotFound = () => {
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="70vh"
    >
      <Paper
        sx={{
          p: 5,
          maxWidth: 500,
          textAlign: 'center',
        }}
      >
        <SadIcon sx={{ fontSize: 100, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Page Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          The page you are looking for doesn't exist or has been moved.
        </Typography>
        <Button
          component={RouterLink}
          to="/dashboard"
          variant="contained"
          size="large"
        >
          Back to Dashboard
        </Button>
      </Paper>
    </Box>
  );
};

export default NotFound;
