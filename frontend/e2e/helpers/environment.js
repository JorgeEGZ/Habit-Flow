const defaultBaseUrl = 'http://localhost:5173'
const writableHostnames = new Set(['localhost', '127.0.0.1'])

export function getBaseUrl() {
  return process.env.BASE_URL || defaultBaseUrl
}

export function isLocalTarget() {
  return writableHostnames.has(new URL(getBaseUrl()).hostname)
}

export function assertLocalWritableTarget() {
  if (!isLocalTarget()) {
    throw new Error('Las pruebas que modifican datos solo pueden ejecutarse contra localhost o 127.0.0.1.')
  }
}

export function getRemoteCredentials() {
  const email = process.env.E2E_EMAIL
  const password = process.env.E2E_PASSWORD

  if (!email || !password) {
    throw new Error('E2E_EMAIL y E2E_PASSWORD son obligatorios para ejecutar pruebas remotas.')
  }

  return { email, password }
}
