import { defineStore } from 'pinia'

import * as financesService from '../services/finances'
import { getApiErrorMessage } from '../utils/errors'

export const useFinancesStore = defineStore('finances', {
  state: () => ({
    accounts: [],
    categories: [],
    transactions: [],
    recurring: [],
    loading: false,
    loadingTransactions: false,
    loadingRecurring: false,
    loadingSpendingByCategory: false,
    loadingMonthlyBudgets: false,
    loadingUpcomingRecurring: false,
    submitting: false,
    error: '',
    spendingByCategory: null,
    spendingByCategoryError: '',
    monthlyBudgets: null,
    monthlyBudgetsError: '',
    budgetedCategoryIdsByMonth: {},
    upcomingRecurring: null,
    upcomingRecurringError: '',
  }),
  actions: {
    async fetchAccounts() {
      this.loading = true
      this.error = ''
      try {
        this.accounts = await financesService.listAccounts()
        return this.accounts
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar las cuentas.')
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCategories() {
      this.loading = true
      this.error = ''
      try {
        this.categories = await financesService.listCategories()
        return this.categories
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar las categorías.')
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchTransactions(params = {}) {
      this.loadingTransactions = true
      this.error = ''
      try {
        this.transactions = await financesService.listTransactions(params)
        return this.transactions
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar los movimientos.')
        throw error
      } finally {
        this.loadingTransactions = false
      }
    },

    async fetchSpendingByCategory(month) {
      this.loadingSpendingByCategory = true
      this.spendingByCategoryError = ''
      this.spendingByCategory = null

      try {
        this.spendingByCategory = await financesService.getSpendingByCategory(month)
        return this.spendingByCategory
      } catch (error) {
        this.spendingByCategoryError = getApiErrorMessage(
          error,
          'No fue posible cargar los gastos por categoría.',
        )
        throw error
      } finally {
        this.loadingSpendingByCategory = false
      }
    },

    async fetchMonthlyBudgets(month) {
      this.loadingMonthlyBudgets = true
      this.monthlyBudgetsError = ''
      this.monthlyBudgets = null

      try {
        this.monthlyBudgets = await financesService.getMonthlyBudgets(month)
        this.budgetedCategoryIdsByMonth[this.monthlyBudgets.month] = this.monthlyBudgets.budgets.map(
          (budget) => budget.category_id,
        )
        return this.monthlyBudgets
      } catch (error) {
        this.monthlyBudgetsError = 'No fue posible cargar los presupuestos.'
        throw error
      } finally {
        this.loadingMonthlyBudgets = false
      }
    },

    async fetchBudgetedCategoryIds(month) {
      const summary = await financesService.getMonthlyBudgets(month)
      this.budgetedCategoryIdsByMonth[summary.month] = summary.budgets.map(
        (budget) => budget.category_id,
      )
      return this.budgetedCategoryIdsByMonth[summary.month]
    },

    async fetchUpcomingRecurring(days = 30) {
      const windowDays = Number(days) === 7 ? 7 : 30
      this.loadingUpcomingRecurring = true
      this.upcomingRecurringError = ''
      this.upcomingRecurring = null

      try {
        this.upcomingRecurring = await financesService.getUpcomingRecurring(windowDays)
        return this.upcomingRecurring
      } catch (error) {
        this.upcomingRecurringError = 'No fue posible cargar los próximos movimientos.'
        throw error
      } finally {
        this.loadingUpcomingRecurring = false
      }
    },

    async fetchRecurring() {
      this.loadingRecurring = true
      this.error = ''
      try {
        this.recurring = await financesService.listRecurringTransactions()
        return this.recurring
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible cargar las reglas recurrentes.')
        throw error
      } finally {
        this.loadingRecurring = false
      }
    },

    async createAccount(payload) {
      this.submitting = true
      this.error = ''
      try {
        const account = await financesService.createAccount(payload)
        await this.fetchAccounts()
        return account
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear la cuenta.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateAccount(accountId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const account = await financesService.updateAccount(accountId, payload)
        await this.fetchAccounts()
        return account
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar la cuenta.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteAccount(accountId) {
      this.submitting = true
      this.error = ''
      try {
        await financesService.deleteAccount(accountId)
        await this.fetchAccounts()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar la cuenta.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async createCategory(payload) {
      this.submitting = true
      this.error = ''
      try {
        const category = await financesService.createCategory(payload)
        await this.fetchCategories()
        return category
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear la categoría.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateCategory(categoryId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const category = await financesService.updateCategory(categoryId, payload)
        await this.fetchCategories()
        return category
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar la categoría.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteCategory(categoryId) {
      this.submitting = true
      this.error = ''
      try {
        await financesService.deleteCategory(categoryId)
        await this.fetchCategories()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar la categoría.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async createTransaction(payload) {
      this.submitting = true
      this.error = ''
      try {
        const transaction = await financesService.createTransaction(payload)
        await this.fetchTransactions()
        return transaction
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear el movimiento.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async createMonthlyBudget(payload) {
      this.submitting = true
      this.error = ''
      try {
        const budget = await financesService.createMonthlyBudget(payload)
        await this.fetchMonthlyBudgets(payload.month)
        return budget
      } catch (error) {
        this.error = monthlyBudgetErrorMessage(error, 'No fue posible guardar el presupuesto.')
        throw new Error(this.error)
      } finally {
        this.submitting = false
      }
    },

    async updateMonthlyBudget(budgetId, payload, month) {
      this.submitting = true
      this.error = ''
      try {
        const budget = await financesService.updateMonthlyBudget(budgetId, payload)
        await this.fetchMonthlyBudgets(month)
        return budget
      } catch (error) {
        this.error = monthlyBudgetErrorMessage(error, 'No fue posible guardar el presupuesto.')
        throw new Error(this.error)
      } finally {
        this.submitting = false
      }
    },

    async deleteMonthlyBudget(budgetId, month) {
      this.submitting = true
      this.error = ''
      try {
        await financesService.deleteMonthlyBudget(budgetId)
        await this.fetchMonthlyBudgets(month)
      } catch (error) {
        this.error = monthlyBudgetErrorMessage(error, 'No fue posible eliminar el presupuesto.')
        throw new Error(this.error)
      } finally {
        this.submitting = false
      }
    },

    async updateTransaction(transactionId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const transaction = await financesService.updateTransaction(transactionId, payload)
        await this.fetchTransactions()
        return transaction
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar el movimiento.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteTransaction(transactionId) {
      this.submitting = true
      this.error = ''
      try {
        await financesService.deleteTransaction(transactionId)
        await this.fetchTransactions()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar el movimiento.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async createRecurring(payload) {
      this.submitting = true
      this.error = ''
      try {
        const rule = await financesService.createRecurringTransaction(payload)
        await this.fetchRecurring()
        return rule
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible crear la regla recurrente.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async updateRecurring(recurringId, payload) {
      this.submitting = true
      this.error = ''
      try {
        const rule = await financesService.updateRecurringTransaction(recurringId, payload)
        await this.fetchRecurring()
        return rule
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible actualizar la regla recurrente.')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async deleteRecurring(recurringId) {
      this.submitting = true
      this.error = ''
      try {
        await financesService.deleteRecurringTransaction(recurringId)
        await this.fetchRecurring()
      } catch (error) {
        this.error = getApiErrorMessage(error, 'No fue posible eliminar la regla recurrente.')
        throw error
      } finally {
        this.submitting = false
      }
    },
  },
})

function monthlyBudgetErrorMessage(error, fallback) {
  const code = error?.response?.data?.error?.code
  const messages = {
    monthly_budget_already_exists: 'Ya existe un presupuesto para esta categoría en este mes.',
    budget_requires_expense_category: 'Solo puedes crear presupuestos para categorías de gasto.',
    monthly_budget_not_found: 'El presupuesto no existe o ya fue eliminado.',
  }

  return messages[code] ?? fallback
}
