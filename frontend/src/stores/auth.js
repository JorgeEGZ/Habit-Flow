import { defineStore } from 'pinia'

import * as authService from '../services/auth'
import { clearSession, getStoredSession, saveSession } from '../utils/session'
import { getApiErrorMessage } from '../utils/errors'

function normalizeTokenPair(tokens) {
  if (!tokens?.access_token || !tokens?.refresh_token) {
    throw new Error('Respuesta de autenticación inválida.')
  }

  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
  }
}

function normalizeUser(user) {
  if (!user?.id || !user?.email) {
    throw new Error('Respuesta de usuario inválida.')
  }

  return user
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: '',
    refreshToken: '',
    isReady: false,
    loading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.user),
  },
  actions: {
    restoreSession() {
      const session = getStoredSession()
      this.accessToken = session.accessToken
      this.user = session.user
    },
    persistSession() {
      saveSession({
        accessToken: this.accessToken,
        user: this.user,
      })
    },
    clearAuth() {
      this.user = null
      this.accessToken = ''
      this.refreshToken = ''
      this.error = ''
      clearSession()
    },
    async initialize() {
      if (this.isReady) {
        return
      }

      this.restoreSession()

      if (!this.accessToken || !this.user) {
        this.clearAuth()
        this.isReady = true
        return
      }

      this.isReady = true
    },
    async login(payload) {
      this.loading = true
      this.error = ''

      try {
        const tokens = normalizeTokenPair(await authService.login(payload))
        this.accessToken = tokens.access_token
        this.refreshToken = tokens.refresh_token
        this.persistSession()
        this.user = normalizeUser(await authService.me())
        this.persistSession()
        return this.user
      } catch (error) {
        this.clearAuth()
        this.error = getApiErrorMessage(error, 'No fue posible iniciar sesión.')
        throw error
      } finally {
        this.loading = false
        this.isReady = true
      }
    },
    async register(payload) {
      this.loading = true
      this.error = ''

      try {
        await authService.register(payload)
        return await this.login({
          email: payload.email,
          password: payload.password,
        })
      } catch (error) {
        if (!this.error) {
          this.error = getApiErrorMessage(error, 'No fue posible registrar la cuenta.')
        }
        throw error
      } finally {
        this.loading = false
      }
    },
    async logout() {
      try {
        if (this.refreshToken) {
          await authService.logout(this.refreshToken)
        }
      } finally {
        this.clearAuth()
        this.isReady = true
      }
    },
  },
})
