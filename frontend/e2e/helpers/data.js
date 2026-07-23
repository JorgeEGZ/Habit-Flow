export function uniqueSuffix() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

export function createLocalUser() {
  const suffix = uniqueSuffix()
  return {
    fullName: 'E2E ' + suffix,
    email: 'habitflow.e2e.' + suffix + '@example.com',
    password: 'SmokePass123!',
  }
}

export function todayDateOnly() {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return year + '-' + month + '-' + day
}

export function currentMonth() {
  return todayDateOnly().slice(0, 7)
}
