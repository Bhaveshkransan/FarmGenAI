/**
 * Enterprise API Configuration & Endpoints
 */

export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || '/api/v1',
  WS_URL: import.meta.env.VITE_WS_URL || '/api/v1/ws',
  TIMEOUT: 15000,
  RETRY_ATTEMPTS: 2
};

export const ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout'
  },
  NEGOTIATION: {
    BASE: '/negotiations',
    ACCEPT: (id) => `/negotiations/${id}/accept`,
    REJECT: (id) => `/negotiations/${id}/reject`,
    INTERVENE: (id) => `/negotiations/${id}/intervene`,
    FEEDBACK: (id) => `/negotiations/${id}/feedback`
  },
  MARKET: {
    PRICES: '/market/prices',
    TRENDS: '/market/trends'
  }
};
