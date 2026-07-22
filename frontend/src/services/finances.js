import { api } from './api'

export async function listAccounts() {
  const { data } = await api.get('/finances/accounts')
  return data
}

export async function createAccount(payload) {
  const { data } = await api.post('/finances/accounts', payload)
  return data
}

export async function updateAccount(accountId, payload) {
  const { data } = await api.patch(`/finances/accounts/${accountId}`, payload)
  return data
}

export async function deleteAccount(accountId) {
  await api.delete(`/finances/accounts/${accountId}`)
}

export async function listCategories() {
  const { data } = await api.get('/finances/categories')
  return data
}

export async function createCategory(payload) {
  const { data } = await api.post('/finances/categories', payload)
  return data
}

export async function updateCategory(categoryId, payload) {
  const { data } = await api.patch(`/finances/categories/${categoryId}`, payload)
  return data
}

export async function deleteCategory(categoryId) {
  await api.delete(`/finances/categories/${categoryId}`)
}

export async function listTransactions(params = {}) {
  const { data } = await api.get('/finances/transactions', { params })
  return data
}

export async function getSpendingByCategory(month) {
  const { data } = await api.get('/finances/insights/spending-by-category', {
    params: month ? { month } : undefined,
  })
  return data
}

export async function getUpcomingRecurring(days = 30) {
  const { data } = await api.get('/finances/insights/upcoming-recurring', {
    params: { days },
  })
  return data
}

export async function getTransaction(transactionId) {
  const { data } = await api.get(`/finances/transactions/${transactionId}`)
  return data
}

export async function createTransaction(payload) {
  const { data } = await api.post('/finances/transactions', payload)
  return data
}

export async function updateTransaction(transactionId, payload) {
  const { data } = await api.patch(`/finances/transactions/${transactionId}`, payload)
  return data
}

export async function deleteTransaction(transactionId) {
  await api.delete(`/finances/transactions/${transactionId}`)
}

export async function listRecurringTransactions() {
  const { data } = await api.get('/finances/recurring')
  return data
}

export async function createRecurringTransaction(payload) {
  const { data } = await api.post('/finances/recurring', payload)
  return data
}

export async function updateRecurringTransaction(recurringId, payload) {
  const { data } = await api.patch(`/finances/recurring/${recurringId}`, payload)
  return data
}

export async function deleteRecurringTransaction(recurringId) {
  await api.delete(`/finances/recurring/${recurringId}`)
}
