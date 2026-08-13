<template>
  <section class="finance-tab-panel monthly-report" :aria-busy="loading">
    <AppSectionHeader
      title="Reporte mensual"
      description="Consulta tus ingresos, gastos y presupuesto para el mes seleccionado."
    >
      <template #actions>
        <label class="finance-budget-month">
          <span>Mes</span>
          <input
            :value="month"
            class="finance-input"
            type="month"
            @input="$emit('month-change', $event.target.value)"
          />
        </label>
      </template>
    </AppSectionHeader>

    <div v-if="loading && !report" class="finance-skeleton-grid" aria-label="Cargando reporte mensual">
      <article v-for="index in 4" :key="index" class="finance-skeleton">
        <span class="finance-skeleton__line finance-skeleton__line--title"></span>
        <span class="finance-skeleton__line"></span>
      </article>
    </div>
    <template v-else-if="report">
      <div class="monthly-report__kpis" aria-label="Resumen mensual">
        <article v-for="metric in metrics" :key="metric.key" class="finance-kpi">
          <span>{{ metric.label }}</span>
          <strong :class="metric.amountClass">{{ metric.value }}</strong>
          <small :class="metric.comparisonClass">{{ comparisonText(metric.comparison) }}</small>
        </article>
      </div>

      <MonthlyTrendsSection
        :trends="trends"
        :loading="trendsLoading"
        :error="trendsError"
        @retry="$emit('retry-trends')"
      />

      <section class="monthly-report__section">
        <AppSectionHeader title="Gastos por categor&#237;a" heading-id="report-spending-title" />
        <AppEmptyState
          v-if="!report.spending_by_category.categories.length"
          title="No hay gastos registrados en este mes."
          compact
        />
        <ol v-else class="finance-spending-list__items">
          <li
            v-for="category in report.spending_by_category.categories"
            :key="category.category_id"
            class="finance-spending-item"
          >
            <div class="finance-spending-item__header">
              <strong>{{ category.category_name }}</strong>
              <strong>{{ formatCurrencyCop(category.amount) }}</strong>
            </div>
            <small>{{ movementLabel(category.transaction_count) }} &middot; {{ percentage(category.share_percentage) }}</small>
            <div
              class="finance-spending-item__bar"
              role="progressbar"
              :aria-valuenow="category.share_percentage"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <span :style="{ width: `${category.share_percentage}%` }"></span>
            </div>
          </li>
        </ol>
      </section>

      <section class="monthly-report__section">
        <AppSectionHeader title="Presupuestos del mes">
          <template #actions>
            <RouterLink :to="{ name: 'finances-budgets' }" class="app-button app-button--secondary">
              Ver presupuestos
            </RouterLink>
          </template>
        </AppSectionHeader>
        <AppEmptyState
          v-if="!report.monthly_budgets.budgets.length"
          title="No tienes presupuestos para este mes."
          compact
        />
        <template v-else>
          <div class="finance-budget-summary">
            <div><span>Presupuestado</span><strong>{{ formatCurrencyCop(report.monthly_budgets.total_budget_amount) }}</strong></div>
            <div><span>Gastado en categor&#237;as presupuestadas</span><strong>{{ formatCurrencyCop(report.monthly_budgets.total_spent_amount) }}</strong></div>
            <div><span>Disponible</span><strong>{{ formatCurrencyCop(report.monthly_budgets.total_remaining_amount) }}</strong></div>
            <div><span>Excedido</span><strong class="transaction-amount--expense">{{ formatCurrencyCop(report.monthly_budgets.total_over_budget_amount) }}</strong></div>
          </div>
          <ul class="monthly-report__budgets">
            <li v-for="budget in report.monthly_budgets.budgets.slice(0, 5)" :key="budget.budget_id">
              <div>
                <strong>{{ budget.category_name }}</strong>
                <small>Gastado {{ formatCurrencyCop(budget.spent_amount) }} de {{ formatCurrencyCop(budget.budget_amount) }}</small>
              </div>
              <AppStatusBadge :label="budgetStatusLabel(budget)" :tone="budgetStatusTone(budget)" />
            </li>
          </ul>
        </template>
      </section>
    </template>
    <div v-else-if="error" class="monthly-report__error" role="alert">
      <p>{{ error }}</p>
      <Button type="button" label="Reintentar" icon="pi pi-refresh" severity="secondary" variant="outlined" @click="$emit('retry')" />
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

import AppEmptyState from '../../../components/ui/AppEmptyState.vue'
import AppSectionHeader from '../../../components/ui/AppSectionHeader.vue'
import AppStatusBadge from '../../../components/ui/AppStatusBadge.vue'
import MonthlyTrendsSection from './MonthlyTrendsSection.vue'
import { formatCurrencyCop } from '../../../utils/format'

const props = defineProps({
  report: { type: Object, default: null },
  loading: Boolean,
  error: { type: String, default: '' },
  month: { type: String, default: '' },
  trends: { type: Object, default: null },
  trendsLoading: Boolean,
  trendsError: { type: String, default: '' },
})

defineEmits(['month-change', 'retry', 'retry-trends'])

const metrics = computed(() => {
  if (!props.report) return []
  const { current, comparisons } = props.report
  return [
    metric('income', 'Ingresos', current.total_income, comparisons.income, 'transaction-amount--income'),
    metric('expenses', 'Gastos', current.total_expenses, comparisons.expenses, 'transaction-amount--expense'),
    metric('net', 'Balance neto', current.net, comparisons.net, current.net >= 0 ? 'transaction-amount--income' : 'transaction-amount--expense'),
    { key: 'transactions', label: 'Movimientos', value: String(current.transaction_count), amountClass: '', comparison: null, comparisonClass: 'monthly-report__comparison--neutral' },
  ]
})

function metric(key, label, amount, comparison, amountClass) {
  return {
    key,
    label,
    value: formatCurrencyCop(amount),
    amountClass,
    comparison,
    comparisonClass: comparisonClass(key, comparison),
  }
}

function comparisonText(comparison) {
  if (!comparison) return 'Movimientos registrados en este mes'
  if (comparison.percentage_change === null) return 'Sin base comparable'
  const sign = comparison.absolute_change > 0 ? '+' : ''
  return `${sign}${formatCurrencyCop(comparison.absolute_change)} \u00b7 ${sign}${comparison.percentage_change.toFixed(2)}%`
}

function comparisonClass(key, comparison) {
  if (!comparison || comparison.absolute_change === 0 || comparison.percentage_change === null) {
    return 'monthly-report__comparison--neutral'
  }
  const favorable = key === 'expenses' ? comparison.absolute_change < 0 : comparison.absolute_change > 0
  return favorable ? 'monthly-report__comparison--success' : 'monthly-report__comparison--danger'
}

function percentage(value) { return `${Number(value).toFixed(2)}%` }
function movementLabel(count) { return `${count} ${count === 1 ? 'movimiento' : 'movimientos'}` }
function budgetStatusLabel(budget) {
  if (budget.exceeded) return 'Excedido'
  if (Number(budget.usage_percentage) === 100) return 'L\u00edmite alcanzado'
  if (Number(budget.usage_percentage) >= 80) return 'Cerca del l\u00edmite'
  return 'En curso'
}
function budgetStatusTone(budget) {
  if (budget.exceeded) return 'danger'
  if (Number(budget.usage_percentage) >= 80) return 'warning'
  return 'success'
}
</script>

<style scoped>
.monthly-report,
.monthly-report__section { display: grid; gap: 1rem; }
.monthly-report__kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .85rem; }
.monthly-report__budgets { display: grid; gap: .6rem; padding: 0; margin: 0; list-style: none; }
.monthly-report__budgets li { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .8rem; border: 1px solid var(--app-border); border-radius: .7rem; }
.monthly-report__budgets small { display: block; margin-top: .2rem; color: var(--app-text-muted); }
.monthly-report__error { display: flex; align-items: center; gap: 1rem; color: var(--app-text-muted); }
.monthly-report__comparison--neutral { color: var(--app-text-muted); }
.monthly-report__comparison--success { color: var(--app-success); }
.monthly-report__comparison--danger { color: var(--app-danger); }
@media (max-width: 54rem) { .monthly-report__kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 34rem) {
  .monthly-report__kpis { grid-template-columns: 1fr; }
  .monthly-report__budgets li,
  .monthly-report__error { align-items: flex-start; flex-direction: column; }
}
</style>
