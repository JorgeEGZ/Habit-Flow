const SESSION_KEY = 'habitflow.session'

let accessToken = ''

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token || ''
}

export function clearSession() {
  accessToken = ''

  if (typeof window === 'undefined') {
    return
  }

  // Remove the pre-cookie session format during the public-release migration.
  window.localStorage.removeItem(SESSION_KEY)
}
