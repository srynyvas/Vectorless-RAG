import axios from 'axios';

const client = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
});

// Add auth token from localStorage
client.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('pageindex_api_key') || 'pageindex-secret-key';
  config.headers.Authorization = `Bearer ${apiKey}`;
  return config;
});

// Error interceptor
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication failed. Check your API key.');
    }
    return Promise.reject(error);
  }
);

export default client;
