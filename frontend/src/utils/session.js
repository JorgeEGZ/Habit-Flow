const SESSION_KEY = 'habitflow.session'

function readSession() {
  if (typeof window === 'undefined') {
    return {
      accessToken: '',
      user: null,
    }
  }

  const raw = window.localStorage.getItem(SESSION_KEY)
  if (!raw) {
    return {
      accessToken: '',
      user: null,
    }
  }

  try {
    const parsed = JSON.parse(raw)
    return {
      accessToken: parsed.accessToken ?? '',
      user: parsed.user ?? null,
    }
  } catch {
    return {
      accessToken: '',
      user: null,
    }
  }
}

function writeSession(session) {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function getStoredSession() {
  return readSession()
}

export function getAccessToken() {
  return readSession().accessToken
}

export function getRefreshToken() {
  return ''
}

export function saveSession(session) {
  writeSession(session)
}

export function clearSession() {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(SESSION_KEY)
}
