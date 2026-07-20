import { defineStore } from 'pinia'

import * as habitsService from '../services/habits'
import { getApiErrorMessage } from '../utils/errors'

export const useHabitsStore = defineStore('habits', {
  state: () => ({
    items: [],
    streaks: {},
    todayLogs: {},
    loading: false,
    submitting: false,
    error: '',
  }),
  actions: {
    async fetchStreaks() {
      const streakEntries = await Promise.all(
        this.items.map(async (habit) => [habit.id, await habitsService.getHabitStreak(habit.id)]),
      )
      this.streaks = Object.fromEntries(streakEntries)
      return this.streaks
    },

    async fetchHabits() {
      this.loading = true
      this.error = ''
      try {
        this.items = await habitsService.listHabits()
        await this.fetchStreaks()
        return this.items
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar los hábitos.')
        throw error
      } finally {
        this.loading = false
      }
    },

    async createHabit(payload) {
      this.submitting = true
      this.error = ''
      try {
        const habit = await habitsService.createHabit(payload)
        await this.fetchHabits()
        return habit
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear el hábito.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateHabit(habitId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const habit = await habitsService.updateHabit(habitId, payload)
        await this.fetchHabits()
        return habit
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar el hábito.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteHabit(habitId) {
      this.submitting = true
      this.error = ''
      try {
        await habitsService.deleteHabit(habitId)
        const nextTodayLogs = { ...this.todayLogs }
        delete nextTodayLogs[habitId]
        this.todayLogs = nextTodayLogs
        await this.fetchHabits()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar el hábito.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async logHabit(habitId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const log = await habitsService.logHabit(habitId, payload)
        this.todayLogs = {
          ...this.todayLogs,
          [habitId]: log,
        }
        await this.fetchHabits()
        return log
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible registrar el progreso.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteHabitLog(habitId, loggedOn) {
      this.submitting = true
      this.error = ''
      try {
        await habitsService.deleteHabitLog(habitId, loggedOn)
        const nextTodayLogs = { ...this.todayLogs }
        delete nextTodayLogs[habitId]
        this.todayLogs = nextTodayLogs
        await this.fetchHabits()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar el registro.')
        throw error
      } finally {
        this.submitting = false
      }
    },
  },
})
