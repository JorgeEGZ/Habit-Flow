import axios from 'axios'

import { clearSession, getAccessToken } from '../utils/session'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const authApi = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/')

    if (status !== 401 || isAuthEndpoint) {
      throw error
    }

    clearSession()
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('habitflow:auth-invalid'))
    }
    throw error
  }
)
