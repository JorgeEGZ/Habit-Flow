import axios from 'axios'

import { clearSession, getAccessToken } from '../utils/session'

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const csrfHeaderName = 'X-CSRF-Protection'
const csrfHeaderValue = '1'

let refreshHandler = null
let refreshPromise = null
let authInvalidDispatched = false

export const authApi = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    [csrfHeaderName]: csrfHeaderValue,
  },
})

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function configureAuthRefresh(handler) {
  refreshHandler = handler
}

export async function requestAccessTokenRefresh() {
  if (!refreshHandler) {
    throw new Error('El cliente de autenticación no está configurado.')
  }

  if (!refreshPromise) {
    refreshPromise = Promise.resolve(refreshHandler())
      .then((tokens) => {
        authInvalidDispatched = false
        return tokens
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

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

    if (status !== 401 || isAuthEndpoint || originalRequest?._retry) {
      throw error
    }

    originalRequest._retry = true

    try {
      await requestAccessTokenRefresh()
      return api(originalRequest)
    } catch {
      clearSession()
      if (!authInvalidDispatched && typeof window !== 'undefined') {
        authInvalidDispatched = true
        window.dispatchEvent(new CustomEvent('habitflow:auth-invalid'))
      }
      throw error
    }
  }
)
