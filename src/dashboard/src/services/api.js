import axios from 'axios';

// API base URL - this should be replaced with the actual API URL in production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://API_GATEWAY_URL_HERE/dev';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Handle global errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log errors to console in development
    if (process.env.NODE_ENV !== 'production') {
      console.error('API Error:', error);
    }
    
    // Customize error message based on status
    if (error.response) {
      // Server responded with non-2xx status
      if (error.response.status === 401) {
        // Handle authentication error
        console.error('Authentication error');
      } else if (error.response.status === 403) {
        // Handle authorization error
        console.error('Authorization error');
      } else if (error.response.status === 404) {
        // Handle not found error
        console.error('Resource not found');
      } else if (error.response.status >= 500) {
        // Handle server error
        console.error('Server error');
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network error - no response received');
    } else {
      // Something happened in setting up the request
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// API service functions
export const fetchDocuments = async (limit = 10) => {
  const response = await api.get(`/documents?limit=${limit}`);
  return response.data.documents;
};

export const fetchRecentDocuments = async (limit = 5) => {
  const response = await api.get(`/documents?limit=${limit}`);
  return response.data.documents;
};

export const fetchDocumentById = async (id) => {
  const response = await api.get(`/documents/${id}`);
  return response.data;
};

export const searchDocuments = async (query, limit = 20) => {
  const response = await api.get(`/documents?q=${encodeURIComponent(query)}&limit=${limit}`);
  return response.data.documents;
};

export const fetchDocumentStatistics = async () => {
  const response = await api.get('/statistics');
  return response.data;
};

export const fetchCylinderInventory = async (month = '', year = '') => {
  let url = '/cylinder-inventory';
  const params = [];
  
  if (month) params.push(`month=${encodeURIComponent(month)}`);
  if (year) params.push(`year=${encodeURIComponent(year)}`);
  
  if (params.length > 0) {
    url += `?${params.join('&')}`;
  }
  
  const response = await api.get(url);
  return response.data.inventory_data;
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

// Function to get signed URL for direct S3 upload
export const getSignedUploadUrl = async (fileName, fileType) => {
  const response = await api.get(`/upload-url?fileName=${encodeURIComponent(fileName)}&fileType=${encodeURIComponent(fileType)}`);
  return response.data;
};

// Function to upload directly to S3 using signed URL
export const uploadToS3 = async (signedUrl, file) => {
  const response = await axios.put(signedUrl, file, {
    headers: {
      'Content-Type': file.type,
    },
  });
  return response;
};

export default {
  fetchDocuments,
  fetchRecentDocuments,
  fetchDocumentById,
  searchDocuments,
  fetchDocumentStatistics,
  fetchCylinderInventory,
  uploadDocument,
  getSignedUploadUrl,
  uploadToS3,
};
