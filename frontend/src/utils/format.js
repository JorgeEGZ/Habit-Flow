export function formatCurrencyCop(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value || 0)
}

function parseDateOnly(value) {
  if (typeof value !== 'string') {
    return null
  }

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) {
    return null
  }

  const [, year, month, day] = match
  return new Date(Number(year), Number(month) - 1, Number(day))
}

export function formatDateShort(value) {
  if (!value) {
    return '-'
  }

  const date = parseDateOnly(value) ?? new Date(value)

  return new Intl.DateTimeFormat('es-CO', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(date)
}

export function getLocalDateString(value = new Date()) {
  if (typeof value === 'string' && parseDateOnly(value)) {
    return value
  }

  const date = value instanceof Date ? value : new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
