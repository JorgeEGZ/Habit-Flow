import { api } from './api'

export async function listGoals() {
  const { data } = await api.get('/savings/goals')
  return data
}

export async function exportGoals(format) {
  const { data } = await api.get(`/savings/exports/goals.${format}`, {
    responseType: 'blob',
  })
  return data
}

export async function createGoal(payload) {
  const { data } = await api.post('/savings/goals', payload)
  return data
}

export async function getGoal(goalId) {
  const { data } = await api.get(`/savings/goals/${goalId}`)
  return data
}

export async function updateGoal(goalId, payload) {
  const { data } = await api.patch(`/savings/goals/${goalId}`, payload)
  return data
}

export async function deleteGoal(goalId) {
  await api.delete(`/savings/goals/${goalId}`)
}

export async function listContributions(goalId) {
  const { data } = await api.get(`/savings/goals/${goalId}/contributions`)
  return data
}

export async function addContribution(goalId, payload) {
  const { data } = await api.post(`/savings/goals/${goalId}/contributions`, payload)
  return data
}

export async function updateContribution(goalId, contributionId, payload) {
  const { data } = await api.patch(
    `/savings/goals/${goalId}/contributions/${contributionId}`,
    payload,
  )
  return data
}

export async function deleteContribution(goalId, contributionId) {
  await api.delete(`/savings/goals/${goalId}/contributions/${contributionId}`)
}

export async function exportGoalContributions(goalId, format) {
  const { data } = await api.get(`/savings/exports/goals/${goalId}/contributions.${format}`, {
    responseType: 'blob',
  })
  return data
}

export async function getGoalProgress(goalId) {
  const { data } = await api.get(`/savings/goals/${goalId}/progress`)
  return data
}
