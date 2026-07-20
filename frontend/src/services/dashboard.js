import { api } from './api'

export async function getSummary() {
  const { data } = await api.get('/dashboard/summary')
  return data
}

export async function getHabits() {
  const { data } = await api.get('/dashboard/habits')
  return data
}

export async function getSavings() {
  const { data } = await api.get('/dashboard/savings')
  return data
}

export async function getFinances() {
  const { data } = await api.get('/dashboard/finances')
  return data
}

