import { defineStore } from 'pinia'

import * as authService from '../services/auth'
import * as usersService from '../services/users'
import { configureAuthRefresh, requestAccessTokenRefresh } from '../services/api'
import { clearSession, setAccessToken } from '../utils/session'
import { getApiErrorMessage } from '../utils/errors'

let initializationPromise = null

function normalizeAccessTokenResponse(tokens) {
  if (!tokens?.access_token || !tokens?.token_type || !tokens?.expires_in) {
    throw new Error('Respuesta de autenticación inválida.')
  }

  return {
    access_token: tokens.access_token,
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
    isReady: false,
    loading: false,
    profileLoading: false,
    passwordLoading: false,
    error: '',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.user),
  },
  actions: {
    configureRefreshHandler() {
      configureAuthRefresh(() => this.refreshAccessToken())
    },
    async refreshAccessToken() {
      const tokens = normalizeAccessTokenResponse(await authService.refresh())
      this.accessToken = tokens.access_token
      setAccessToken(tokens.access_token)
      return tokens
    },
    clearAuth() {
      this.user = null
      this.accessToken = ''
      this.error = ''
      clearSession()
    },
    async initialize() {
      if (this.isReady) {
        return
      }
      if (initializationPromise) {
        return initializationPromise
      }

      initializationPromise = (async () => {
        this.configureRefreshHandler()
        // Access tokens and user data are no longer persisted. This also clears
        // the legacy localStorage session before trying the HttpOnly cookie.
        clearSession()

        try {
          await requestAccessTokenRefresh()
          this.user = normalizeUser(await usersService.getMe())
        } catch {
          // Missing cookies, 401/403 responses, CORS failures, and network
          // errors all degrade safely to an anonymous session.
          this.clearAuth()
        } finally {
          this.isReady = true
        }
      })()

      try {
        await initializationPromise
      } finally {
        initializationPromise = null
      }
    },
    async login(payload) {
      this.loading = true
      this.error = ''
      this.configureRefreshHandler()

      try {
        const tokens = normalizeAccessTokenResponse(await authService.login(payload))
        this.accessToken = tokens.access_token
        setAccessToken(tokens.access_token)
        this.user = normalizeUser(await usersService.getMe())
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
        await authService.logout()
      } finally {
        this.clearAuth()
        this.isReady = true
      }
    },
    async updateProfile(payload) {
      this.profileLoading = true
      this.error = ''

      try {
        this.user = normalizeUser(await usersService.updateMe(payload))
        return this.user
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar el perfil.', {
          safeOnly: true,
        })
        throw error
      } finally {
        this.profileLoading = false
      }
    },
    async changePassword(payload) {
      this.passwordLoading = true
      this.error = ''

      try {
        await usersService.changePassword(payload)

        // Password changes revoke all refresh tokens. Logout can therefore
        // fail remotely, but its finally block still clears the local state.
        try {
          await this.logout()
        } catch {
          // Local cleanup is guaranteed by logout().
        }
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar la contraseña.', {
          safeOnly: true,
        })
        throw error
      } finally {
        this.passwordLoading = false
      }
    },
  },
})
