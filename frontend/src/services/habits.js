import { api } from './api'

export async function listHabits() {
  const { data } = await api.get('/habits')
  return data
}

export async function createHabit(payload) {
  const { data } = await api.post('/habits', payload)
  return data
}

export async function getHabit(habitId) {
  const { data } = await api.get(`/habits/${habitId}`)
  return data
}

export async function updateHabit(habitId, payload) {
  const { data } = await api.patch(`/habits/${habitId}`, payload)
  return data
}

export async function deleteHabit(habitId) {
  await api.delete(`/habits/${habitId}`)
}

export async function getHabitStreak(habitId) {
  const { data } = await api.get(`/habits/${habitId}/streak`)
  return data
}

export async function logHabit(habitId, payload) {
  const { data } = await api.post(`/habits/${habitId}/logs`, payload)
  return data
}

export async function deleteHabitLog(habitId, loggedOn) {
  await api.delete(`/habits/${habitId}/logs/${loggedOn}`)
}
