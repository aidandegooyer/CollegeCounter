import axios from 'axios';
import { getAuth } from 'firebase/auth';

// base API URL
const API_BASE_URL = 'http://127.0.0.1:8000/v1';  // Adjust this according to your setup

export const api = axios.create({
  baseURL: API_BASE_URL
});

// Add an interceptor to attach the Firebase auth token to every request
api.interceptors.request.use(async (config) => {
  const auth = getAuth();
  const user = auth.currentUser;
  
  if (user) {
    try {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    } catch (error) {
      console.error('Error getting auth token', error);
    }
  }
  
  return config;
}, (error) => {
  return Promise.reject(error);
});
