import { defineStore } from 'pinia'

import * as dashboardService from '../services/dashboard'
import { getApiErrorMessage } from '../utils/errors'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    summary: null,
    habits: null,
    savings: null,
    finances: null,
    loading: false,
    error: '',
  }),
  actions: {
    async fetchSummary() {
      this.loading = true
      this.error = ''
      try {
        const data = await dashboardService.getSummary()
        this.summary = data
        this.habits = data.habits
        this.savings = data.savings
        this.finances = data.finances
        return data
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar el tablero.')
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchHabits() {
      this.loading = true
      this.error = ''
      try {
        this.habits = await dashboardService.getHabits()
        return this.habits
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar los hábitos.')
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchSavings() {
      this.loading = true
      this.error = ''
      try {
        this.savings = await dashboardService.getSavings()
        return this.savings
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar los ahorros.')
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchFinances() {
      this.loading = true
      this.error = ''
      try {
        this.finances = await dashboardService.getFinances()
        if (this.summary) {
          this.summary = {
            ...this.summary,
            finances: this.finances,
          }
        }
        return this.finances
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar las finanzas.')
        throw error
      } finally {
        this.loading = false
      }
    },
  },
})
