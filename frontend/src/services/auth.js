import { api, authApi } from './api'

export async function login(payload) {
  const { data } = await authApi.post('/auth/login', payload)
  return data
}

export async function register(payload) {
  const { data } = await authApi.post('/auth/register', payload)
  return data
}

export async function refresh(refreshToken) {
  const { data } = await authApi.post('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}

export async function logout(refreshToken) {
  await authApi.post('/auth/logout', {
    refresh_token: refreshToken,
  })
}

export async function me() {
  const { data } = await api.get('/users/me')
  return data
}

