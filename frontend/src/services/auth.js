import { api, authApi } from './api'

export async function login(payload) {
  const { data } = await authApi.post('/auth/login', payload)
  return data
}

export async function register(payload) {
  const { data } = await authApi.post('/auth/register', payload)
  return data
}

export async function refresh() {
  const { data } = await authApi.post('/auth/refresh')
  return data
}

export async function logout() {
  await authApi.post('/auth/logout')
}

export async function me() {
  const { data } = await api.get('/users/me')
  return data
}
