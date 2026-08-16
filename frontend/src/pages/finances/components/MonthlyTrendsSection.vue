<template>
  <section class="monthly-trends" aria-labelledby="monthly-trends-title" :aria-busy="loading">
    <AppSectionHeader
      title="Tendencia de 6 meses"
      heading-id="monthly-trends-title"
      :heading-level="3"
      description="Evolución de tus movimientos reales hasta el mes seleccionado."
    />

    <div v-if="loading && !trends" class="finance-skeleton-grid" aria-label="Cargando tendencias mensuales">
      <article v-for="index in 6" :key="index" class="finance-skeleton">
        <span class="finance-skeleton__line finance-skeleton__line--title"></span>
        <span class="finance-skeleton__line"></span>
      </article>
    </div>
    <div v-else-if="error" class="monthly-trends__error" role="alert">
      <p>{{ error }}</p>
      <Button type="button" label="Reintentar" icon="pi pi-refresh" severity="secondary" variant="outlined" @click="$emit('retry')" />
    </div>
    <AppEmptyState
      v-else-if="!hasTransactions"
      title="No hay movimientos registrados en los últimos 6 meses."
      compact
    />
    <template v-else>
      <p class="monthly-trends__helper">La tasa de ahorro es el porcentaje de tus ingresos que queda después de los gastos.</p>
      <div class="monthly-trends__legend" aria-label="Leyenda">
        <span><i class="monthly-trends__marker monthly-trends__marker--income"></i>Ingresos</span>
        <span><i class="monthly-trends__marker monthly-trends__marker--expense"></i>Gastos</span>
      </div>
      <ol class="monthly-trends__list" aria-label="Tendencia financiera mensual">
        <li v-for="item in trends.months" :key="item.month" class="monthly-trends__item">
          <div class="monthly-trends__month">{{ monthLabel(item.month) }}</div>
          <div class="monthly-trends__metric">
            <span>Ingresos</span>
            <strong class="transaction-amount--income">{{ formatCurrencyCop(item.total_income) }}</strong>
            <div class="monthly-trends__bar monthly-trends__bar--income" aria-hidden="true"><span :style="{ width: barWidth(item.total_income) }"></span></div>
          </div>
          <div class="monthly-trends__metric">
            <span>Gastos</span>
            <strong class="transaction-amount--expense">{{ formatCurrencyCop(item.total_expenses) }}</strong>
            <div class="monthly-trends__bar monthly-trends__bar--expense" aria-hidden="true"><span :style="{ width: barWidth(item.total_expenses) }"></span></div>
          </div>
          <div class="monthly-trends__footer">
            <span>Balance neto</span>
            <strong :class="item.net < 0 ? 'transaction-amount--expense' : 'transaction-amount--income'">{{ formatCurrencyCop(item.net) }}</strong>
            <span>Tasa de ahorro</span>
            <strong :class="savingsRateClass(item.savings_rate)">{{ savingsRateLabel(item.savings_rate) }}</strong>
          </div>
        </li>
      </ol>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import Button from 'primevue/button'

import AppEmptyState from '../../../components/ui/AppEmptyState.vue'
import AppSectionHeader from '../../../components/ui/AppSectionHeader.vue'
import { formatCurrencyCop } from '../../../utils/format'

const props = defineProps({
  trends: { type: Object, default: null },
  loading: Boolean,
  error: { type: String, default: '' },
})

defineEmits(['retry'])

const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
const hasTransactions = computed(() => props.trends?.months?.some((item) => item.transaction_count > 0) ?? false)
const chartMaximum = computed(() => Math.max(
  0,
  ...(props.trends?.months?.flatMap((item) => [item.total_income, item.total_expenses]) ?? []),
))

function monthLabel(month) {
  const [year, monthNumber] = month.split('-')
  return `${monthNames[Number(monthNumber) - 1]} ${year}`
}

function barWidth(amount) {
  if (!chartMaximum.value) return '0%'
  return `${Math.max(0, Math.min((amount / chartMaximum.value) * 100, 100))}%`
}

function savingsRateLabel(rate) {
  return rate === null ? 'Sin ingresos' : `${Number(rate).toFixed(2)}%`
}

function savingsRateClass(rate) {
  if (rate === null) return 'monthly-trends__rate--neutral'
  return rate < 0 ? 'transaction-amount--expense' : 'transaction-amount--income'
}
</script>

<style scoped>
.monthly-trends { display: grid; gap: 1rem; }
.monthly-trends__helper { margin: 0; color: var(--app-text-muted); font-size: .9rem; }
.monthly-trends__legend { display: flex; flex-wrap: wrap; gap: 1rem; color: var(--app-text-muted); font-size: .86rem; }
.monthly-trends__legend span { display: inline-flex; align-items: center; gap: .4rem; }
.monthly-trends__marker { width: .7rem; height: .7rem; border-radius: 999px; }
.monthly-trends__marker--income, .monthly-trends__bar--income span { background: var(--app-success); }
.monthly-trends__marker--expense, .monthly-trends__bar--expense span { background: var(--app-danger); }
.monthly-trends__list { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: .7rem; padding: 0; margin: 0; list-style: none; }
.monthly-trends__item { display: grid; gap: .7rem; padding: .85rem; border: 1px solid var(--app-border); border-radius: .7rem; background: var(--app-surface-2); min-width: 0; }
.monthly-trends__month { color: var(--app-text); font-weight: 700; }
.monthly-trends__metric { display: grid; gap: .25rem; min-width: 0; }
.monthly-trends__metric > span, .monthly-trends__footer > span { color: var(--app-text-muted); font-size: .76rem; }
.monthly-trends__metric strong, .monthly-trends__footer strong { font-size: .86rem; overflow-wrap: anywhere; }
.monthly-trends__bar { height: .35rem; overflow: hidden; border-radius: 999px; background: var(--app-surface); }
.monthly-trends__bar span { display: block; height: 100%; border-radius: inherit; }
.monthly-trends__footer { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .25rem .45rem; padding-top: .65rem; border-top: 1px solid var(--app-border); }
.monthly-trends__rate--neutral { color: var(--app-text-muted); }
.monthly-trends__error { display: flex; align-items: center; gap: 1rem; color: var(--app-text-muted); }
@media (max-width: 70rem) { .monthly-trends__list { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 42rem) { .monthly-trends__list { grid-template-columns: 1fr; } .monthly-trends__item { grid-template-columns: minmax(5rem, .6fr) minmax(0, 1fr) minmax(0, 1fr); align-items: start; } .monthly-trends__month { grid-row: span 2; } .monthly-trends__footer { grid-column: 2 / -1; } }
@media (max-width: 28rem) { .monthly-trends__item { grid-template-columns: 1fr; } .monthly-trends__month, .monthly-trends__footer { grid-column: auto; grid-row: auto; } .monthly-trends__error { align-items: flex-start; flex-direction: column; } }
</style>
