import { defineStore } from 'pinia'

import * as savingsService from '../services/savings'
import { getApiErrorMessage } from '../utils/errors'

export const useSavingsStore = defineStore('savings', {
  state: () => ({
    items: [],
    contributionsByGoalId: {},
    progressByGoalId: {},
    loading: false,
    submitting: false,
    error: '',
  }),
  actions: {
    async fetchGoals() {
      this.loading = true
      this.error = ''
      try {
        this.items = await savingsService.listGoals()
        const progressEntries = await Promise.all(
          this.items.map(async (goal) => [goal.id, await savingsService.getGoalProgress(goal.id)]),
        )
        this.progressByGoalId = Object.fromEntries(progressEntries)
        return this.items
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar los ahorros.', { safeOnly: true })
        throw error
      } finally {
        this.loading = false
      }
    },

    async createGoal(payload) {
      this.submitting = true
      this.error = ''
      try {
        const goal = await savingsService.createGoal(payload)
        await this.fetchGoals()
        return goal
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear la meta.', { safeOnly: true })
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateGoal(goalId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const goal = await savingsService.updateGoal(goalId, payload)
        await this.fetchGoals()
        return goal
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar la meta.', { safeOnly: true })
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteGoal(goalId) {
      this.submitting = true
      this.error = ''
      try {
        await savingsService.deleteGoal(goalId)
        const nextContributions = { ...this.contributionsByGoalId }
        const nextProgress = { ...this.progressByGoalId }
        delete nextContributions[goalId]
        delete nextProgress[goalId]
        this.contributionsByGoalId = nextContributions
        this.progressByGoalId = nextProgress
        await this.fetchGoals()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar la meta.', { safeOnly: true })
        throw error
      } finally {
        this.submitting = false
      }
    },

    async fetchContributions(goalId) {
      this.loading = true
      this.error = ''
      try {
        const contributions = await savingsService.listContributions(goalId)
        this.contributionsByGoalId = {
          ...this.contributionsByGoalId,
          [goalId]: contributions,
        }
        return contributions
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar las contribuciones.', { safeOnly: true })
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchProgress(goalId) {
      this.loading = true
      this.error = ''
      try {
        const progress = await savingsService.getGoalProgress(goalId)
        this.progressByGoalId = {
          ...this.progressByGoalId,
          [goalId]: progress,
        }
        return progress
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar el progreso.', { safeOnly: true })
        throw error
      } finally {
        this.loading = false
      }
    },

    async addContribution(goalId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const contribution = await savingsService.addContribution(goalId, payload)
        await this.refreshContributionData(goalId)
        return contribution
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible registrar la contribución.', { safeOnly: true })
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateContribution(goalId, contributionId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const contribution = await savingsService.updateContribution(goalId, contributionId, payload)
        await this.refreshContributionData(goalId)
        return contribution
      } catch (error) {
        this.error = contributionErrorMessage(error, 'No fue posible guardar el aporte.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteContribution(goalId, contributionId) {
      this.submitting = true
      this.error = ''
      try {
        await savingsService.deleteContribution(goalId, contributionId)
        await this.refreshContributionData(goalId)
      } catch (error) {
        this.error = contributionErrorMessage(error, 'No fue posible eliminar el aporte.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async refreshContributionData(goalId) {
      await Promise.all([
        this.fetchGoals(),
        this.fetchContributions(goalId),
        this.fetchProgress(goalId),
      ])
    },
  },
})

function contributionErrorMessage(error, fallback) {
  if (error?.response?.data?.error?.code === 'saving_contribution_not_found') {
    return 'El aporte no existe o ya fue eliminado.'
  }

  return getApiErrorMessage(error, fallback, { safeOnly: true })
}
