<template>
  <section class="dashboard-page page-stack">
    <header class="dashboard-workspace-header">
      <div>
        <p class="dashboard-workspace-header__eyebrow">Visi&oacute;n general</p>
        <h1>Tablero</h1>
        <p>Consulta el estado de tus h&aacute;bitos, ahorros y finanzas en un solo lugar.</p>
      </div>
    </header>

    <div v-if="dashboardStore.loading && !dashboardStore.summary" class="dashboard-loading" aria-label="Cargando tablero">
      <div v-for="index in 4" :key="index" class="dashboard-loading__card">
        <span class="dashboard-loading__label"></span>
        <strong class="dashboard-loading__value"></strong>
      </div>
    </div>

    <p v-else-if="dashboardStore.error" class="dashboard-page__alert">
      {{ dashboardStore.error }}
    </p>

    <template v-else>
      <section class="dashboard-kpi-band" aria-label="Indicadores principales">
        <article class="dashboard-kpi dashboard-kpi--balance">
          <span>Balance mensual</span>
          <strong :class="balanceClass(summary.finances.monthly_balance)">
            {{ formatSignedCurrency(summary.finances.monthly_balance) }}
          </strong>
          <small>Ingresos menos gastos del mes actual</small>
        </article>
        <article class="dashboard-kpi">
          <span>Ingresos del mes</span>
          <strong class="dashboard-kpi__income">{{ formatCurrencyCop(summary.finances.monthly_income) }}</strong>
        </article>
        <article class="dashboard-kpi">
          <span>Gastos del mes</span>
          <strong class="dashboard-kpi__expense">{{ formatCurrencyCop(summary.finances.monthly_expenses) }}</strong>
        </article>
        <article class="dashboard-kpi">
          <span>H&aacute;bitos completados hoy</span>
          <strong>{{ summary.habits.completed_today }} / {{ summary.habits.total_active_habits }}</strong>
        </article>
      </section>

      <section class="dashboard-grid dashboard-grid--balanced">
        <Card class="dashboard-panel dashboard-panel--primary">
          <template #content>
            <header class="dashboard-panel__header">
              <div>
                <p class="dashboard-panel__eyebrow">Seguimiento diario</p>
                <h2>H&aacute;bitos</h2>
              </div>
              <RouterLink :to="{ name: 'habits-today' }" class="dashboard-panel__action">
                Registrar h&aacute;bitos
              </RouterLink>
            </header>

            <div v-if="!summary.habits.total_active_habits" class="dashboard-empty">
              <span>A&uacute;n no tienes h&aacute;bitos para registrar.</span>
              <RouterLink :to="{ name: 'habits-today' }" class="dashboard-empty__action">
                Registrar h&aacute;bitos
              </RouterLink>
            </div>
            <template v-else>
              <p class="dashboard-copy">
                <strong>{{ summary.habits.completed_today }}</strong> de
                <strong>{{ summary.habits.total_active_habits }}</strong> h&aacute;bitos completados hoy.
              </p>

              <div class="dashboard-metric-group">
                <div class="dashboard-metric">
                  <span>Racha actual</span>
                  <template v-if="summary.habits.current_streak_summary">
                    <strong>{{ summary.habits.current_streak_summary.title }}</strong>
                    <small>{{ summary.habits.current_streak_summary.current }} d&iacute;as</small>
                  </template>
                  <strong v-else>Sin racha activa</strong>
                </div>
                <div class="dashboard-metric">
                  <span>Racha m&aacute;s larga</span>
                  <template v-if="summary.habits.longest_streak_summary">
                    <strong>{{ summary.habits.longest_streak_summary.title }}</strong>
                    <small>{{ summary.habits.longest_streak_summary.longest }} d&iacute;as</small>
                  </template>
                  <strong v-else>Sin historial</strong>
                </div>
              </div>
            </template>
          </template>
        </Card>

        <Card class="dashboard-panel dashboard-panel--secondary">
          <template #content>
            <header class="dashboard-panel__header">
              <div>
                <p class="dashboard-panel__eyebrow">Progreso de ahorro</p>
                <h2>Ahorros</h2>
              </div>
              <RouterLink :to="{ name: 'savings-goals' }" class="dashboard-panel__action">Ver metas</RouterLink>
            </header>

            <div v-if="!summary.savings.nearest_goal" class="dashboard-empty">
              <span>No hay metas activas con fecha objetivo.</span>
              <RouterLink :to="{ name: 'savings-goals' }" class="dashboard-empty__action">Ver metas</RouterLink>
            </div>
            <div v-else class="dashboard-goal">
              <div class="dashboard-goal__heading">
                <div>
                  <span>Meta m&aacute;s cercana</span>
                  <strong>{{ summary.savings.nearest_goal.name }}</strong>
                </div>
                <strong>{{ formatPercentage(summary.savings.nearest_goal.completion_percentage) }}</strong>
              </div>
              <div class="dashboard-progress" role="progressbar" :aria-valuenow="summary.savings.nearest_goal.completion_percentage" aria-valuemin="0" aria-valuemax="100">
                <span :style="{ width: `${summary.savings.nearest_goal.completion_percentage}%` }"></span>
              </div>
              <div class="dashboard-goal__details">
                <span>{{ formatCurrencyCop(summary.savings.nearest_goal.current_amount) }} de {{ formatCurrencyCop(summary.savings.nearest_goal.target_amount) }}</span>
                <span>Fecha objetivo: {{ formatDateShort(summary.savings.nearest_goal.target_date) }}</span>
              </div>
            </div>
          </template>
        </Card>
      </section>

      <section class="dashboard-columns">
        <Card class="dashboard-panel">
          <template #content>
            <header class="dashboard-panel__header">
              <div>
                <p class="dashboard-panel__eyebrow">Finanzas</p>
                <h2>Balances de cuentas</h2>
              </div>
              <RouterLink :to="{ name: 'finances-movements' }" class="dashboard-panel__action">Ver movimientos</RouterLink>
            </header>

            <ul v-if="summary.finances.account_balances.length" class="dashboard-list">
              <li v-for="account in summary.finances.account_balances" :key="account.account_id">
                <span>
                  {{ account.name }}
                  <small>Saldo actual</small>
                </span>
                <strong>{{ formatCurrencyCop(account.current_balance) }}</strong>
              </li>
            </ul>
            <div v-else class="dashboard-empty">
              <span>No hay cuentas registradas.</span>
              <RouterLink :to="{ name: 'finances-movements' }" class="dashboard-empty__action">Ver movimientos</RouterLink>
            </div>
          </template>
        </Card>

        <Card class="dashboard-panel">
          <template #content>
            <header class="dashboard-panel__header">
              <div>
                <p class="dashboard-panel__eyebrow">Finanzas</p>
                <h2>Movimientos recientes</h2>
              </div>
              <RouterLink :to="{ name: 'finances-movements' }" class="dashboard-panel__action">Ver movimientos</RouterLink>
            </header>

            <ul v-if="summary.finances.recent_transactions.length" class="dashboard-list">
              <li v-for="transaction in summary.finances.recent_transactions" :key="transaction.transaction_id">
                <span>
                  {{ transaction.description || transaction.category_name }}
                  <small>{{ transaction.account_name }} &middot; {{ formatDateShort(transaction.transaction_date) }}</small>
                </span>
                <strong :class="transactionAmountClass(transaction.type)">
                  {{ formatTransactionAmount(transaction) }}
                </strong>
              </li>
            </ul>
            <div v-else class="dashboard-empty">
              <span>No hay movimientos recientes.</span>
              <RouterLink :to="{ name: 'finances-movements' }" class="dashboard-empty__action">Ver movimientos</RouterLink>
            </div>
          </template>
        </Card>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'

import { useDashboardStore } from '../../stores/dashboard'
import { formatCurrencyCop, formatDateShort } from '../../utils/format'

const dashboardStore = useDashboardStore()

const emptySummary = {
  habits: {
    completed_today: 0,
    total_active_habits: 0,
    current_streak_summary: null,
    longest_streak_summary: null,
  },
  savings: {
    total_savings_contributed: 0,
    active_goals_count: 0,
    completed_goals_count: 0,
    nearest_goal: null,
    savings_progress_summary: {
      current_amount: 0,
      target_amount: 0,
      completion_percentage: 0,
    },
  },
  finances: {
    monthly_income: 0,
    monthly_expenses: 0,
    monthly_balance: 0,
    account_balances: [],
    recent_transactions: [],
  },
}

const summary = computed(() => dashboardStore.summary ?? emptySummary)

function formatPercentage(value) {
  return `${value ?? 0}%`
}

function formatSignedCurrency(value) {
  const amount = Number(value ?? 0)
  const sign = amount > 0 ? '+ ' : amount < 0 ? '- ' : ''
  return `${sign}${formatCurrencyCop(Math.abs(amount))}`
}

function formatTransactionAmount(transaction) {
  const sign = transaction.type === 'expense' ? '- ' : '+ '
  return `${sign}${formatCurrencyCop(transaction.amount)}`
}

function balanceClass(value) {
  if (value > 0) return 'dashboard-kpi__income'
  if (value < 0) return 'dashboard-kpi__expense'
  return ''
}

function transactionAmountClass(type) {
  return type === 'expense' ? 'dashboard-amount--expense' : 'dashboard-amount--income'
}

onMounted(async () => {
  if (!dashboardStore.summary) {
    try {
      await dashboardStore.fetchSummary()
    } catch {
      // The store exposes the request error for the dashboard alert.
    }
  }
})
</script>
