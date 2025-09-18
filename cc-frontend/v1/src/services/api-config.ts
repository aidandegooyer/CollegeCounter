import axios from 'axios';
import { getAuth } from 'firebase/auth';

// Use Vite's import.meta.env for environment variables in frontend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.collegecounter.org/v1';

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
