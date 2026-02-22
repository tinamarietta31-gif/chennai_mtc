import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Search for routes between source and destination
 */
export const searchRoutes = async (source, destination, timeOfDay = 12) => {
  const response = await api.post('/search-route', {
    source,
    destination,
    time_of_day: timeOfDay,
  });
  return response.data;
};

/**
 * Get stop suggestions for autocomplete
 */
export const getStopSuggestions = async (query) => {
  const response = await api.get('/get-stop-suggestions', {
    params: { query },
  });
  return response.data.suggestions;
};

/**
 * Get all stops
 */
export const getAllStops = async (query = null) => {
  const response = await api.get('/get-stops', {
    params: query ? { query } : {},
  });
  return response.data;
};

/**
 * Get route map data for visualization
 */
export const getRouteMapData = async (routeNumber, source, destination) => {
  const response = await api.get(`/get-route-between-stops/${routeNumber}`, {
    params: { source, destination },
  });
  return response.data;
};

/**
 * Get full route coordinates
 */
export const getFullRouteMap = async (routeNumber) => {
  const response = await api.get(`/get-route-map/${routeNumber}`);
  return response.data;
};

/**
 * Predict travel time using ML model
 */
export const predictTravelTime = async (data) => {
  const response = await api.post('/predict-time', data);
  return response.data;
};

/**
 * Get system statistics
 */
export const getStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

/**
 * Health check
 */
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
