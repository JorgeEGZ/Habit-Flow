import { defineStore } from 'pinia'

import * as habitsService from '../services/habits'
import { getApiErrorMessage } from '../utils/errors'

export const useHabitsStore = defineStore('habits', {
  state: () => ({
    items: [],
    streaks: {},
    todayLogs: {},
    progressByHabitId: {},
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

    async fetchProgress(asOf) {
      this.error = ''
      try {
        const progress = await habitsService.getHabitProgress(asOf)
        this.progressByHabitId = Object.fromEntries(
          progress.map((item) => [item.habit_id, item]),
        )
        this.todayLogs = Object.fromEntries(
          progress
            .filter((item) => item.log_for_date)
            .map((item) => [item.habit_id, item.log_for_date]),
        )
        return progress
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar el progreso de los hábitos.')
        throw error
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
        const nextProgress = { ...this.progressByHabitId }
        delete nextProgress[habitId]
        this.progressByHabitId = nextProgress
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
        await this.fetchHabits()
        await this.fetchProgress(payload.logged_on)
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
        await this.fetchHabits()
        await this.fetchProgress(loggedOn)
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar el registro.')
        throw error
      } finally {
        this.submitting = false
      }
    },
  },
})
