<template>
  <section class="monthly-insights" aria-labelledby="monthly-insights-title">
    <AppSectionHeader
      title="Lectura del mes"
      description="Observaciones basadas en tus movimientos reales y presupuestos del mes seleccionado."
      heading-id="monthly-insights-title"
    />

    <AppEmptyState
      v-if="!insights.length"
      title="No hay observaciones disponibles para este mes."
      compact
    />
    <div v-else class="monthly-insights__grid">
      <article v-for="insight in insights" :key="insight.code" class="monthly-insights__item">
        <div class="monthly-insights__heading">
          <i :class="iconFor(insight.code)" aria-hidden="true"></i>
          <div>
            <h3>{{ titleFor(insight.code) }}</h3>
            <AppStatusBadge :label="toneLabel(insight.tone)" :tone="insight.tone" />
          </div>
        </div>
        <p>{{ messageFor(insight) }}</p>
        <RouterLink
          v-if="actionFor(insight.code)"
          :to="actionFor(insight.code).to"
          class="monthly-insights__action"
        >
          {{ actionFor(insight.code).label }}
        </RouterLink>
      </article>
    </div>
  </section>
</template>

<script setup>
import AppEmptyState from '../../../components/ui/AppEmptyState.vue'
import AppSectionHeader from '../../../components/ui/AppSectionHeader.vue'
import AppStatusBadge from '../../../components/ui/AppStatusBadge.vue'
import { formatCurrencyCop } from '../../../utils/format'

defineProps({
  insights: { type: Array, default: () => [] },
})

const budgetCodes = new Set([
  'budget_exceeded',
  'budget_limit_reached',
  'budget_near_limit',
])

function titleFor(code) {
  return {
    no_activity: 'Sin movimientos',
    budget_exceeded: 'Presupuestos excedidos',
    budget_limit_reached: 'Límite de presupuesto',
    budget_near_limit: 'Presupuestos cerca del límite',
    negative_net: 'Balance neto negativo',
    positive_savings_rate: 'Ingreso restante',
    break_even: 'Balance del mes',
    no_income: 'Ingresos pendientes',
    expenses_increased: 'Gastos frente al mes anterior',
    expenses_decreased: 'Gastos frente al mes anterior',
    expenses_no_comparison: 'Comparación de gastos',
    top_spending_category: 'Mayor gasto del mes',
  }[code] || 'Resumen del mes'
}

function toneLabel(tone) {
  return {
    neutral: 'Resumen',
    info: 'Información',
    success: 'Evolución favorable',
    warning: 'Para revisar',
    danger: 'Requiere atención',
  }[tone] || 'Resumen'
}

function iconFor(code) {
  if (budgetCodes.has(code)) return 'pi pi-wallet'
  if (code === 'negative_net' || code === 'no_income') return 'pi pi-exclamation-triangle'
  if (code === 'expenses_increased') return 'pi pi-arrow-up-right'
  if (code === 'expenses_decreased') return 'pi pi-arrow-down-right'
  if (code === 'top_spending_category') return 'pi pi-tag'
  if (code === 'positive_savings_rate') return 'pi pi-chart-line'
  return 'pi pi-info-circle'
}

function actionFor(code) {
  if (code === 'no_activity') {
    return { to: { name: 'finances-movements' }, label: 'Ir a movimientos' }
  }
  if (budgetCodes.has(code)) {
    return { to: { name: 'finances-budgets' }, label: 'Ver presupuestos' }
  }
  return null
}

function messageFor(insight) {
  const values = insight.values || {}
  const count = Number(values.count || 0)
  const budgetLabel = `${count} ${count === 1 ? 'presupuesto' : 'presupuestos'}`
  const percentage = (value) => `${Number(value || 0).toFixed(2)}%`

  switch (insight.code) {
    case 'no_activity':
      return 'No hay movimientos registrados en este mes. Registra ingresos y gastos para obtener una lectura financiera.'
    case 'budget_exceeded':
      return `${budgetLabel} superaron el límite por un total de ${formatCurrencyCop(values.total_over_budget_amount || 0)}.`
    case 'budget_limit_reached':
      return `${budgetLabel} alcanzaron el límite del mes.`
    case 'budget_near_limit':
      return `${budgetLabel} están cerca del límite. La mayor utilización corresponde a ${values.category_name} con ${percentage(values.highest_usage_percentage)}.`
    case 'negative_net':
      return `Los gastos superaron los ingresos registrados por ${formatCurrencyCop(values.shortfall_amount || 0)}.`
    case 'positive_savings_rate':
      return `Después de los gastos quedó ${percentage(values.savings_rate)} de los ingresos registrados.`
    case 'break_even':
      return 'Los ingresos y gastos registrados terminaron con un balance neto de cero.'
    case 'no_income':
      return 'Hay gastos registrados, pero no ingresos para este mes.'
    case 'expenses_increased':
      return `Los gastos fueron ${percentage(values.percentage_change)} mayores que el mes anterior.`
    case 'expenses_decreased':
      return `Los gastos fueron ${percentage(Math.abs(Number(values.percentage_change || 0)))} menores que el mes anterior.`
    case 'expenses_no_comparison':
      return 'No hay una base de gastos del mes anterior para comparar.'
    case 'top_spending_category':
      return `${values.category_name} representó ${percentage(values.share_percentage)} de los gastos del mes.`
    default:
      return 'Consulta los detalles de tus movimientos para este mes.'
  }
}
</script>

<style scoped>
.monthly-insights { display: grid; gap: 1rem; }
.monthly-insights__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
.monthly-insights__item { display: grid; align-content: start; gap: .75rem; min-width: 0; padding: 1rem; border: 1px solid var(--app-border); border-radius: .8rem; background: var(--app-surface-2); }
.monthly-insights__heading { display: flex; align-items: flex-start; gap: .7rem; }
.monthly-insights__heading > i { margin-top: .16rem; color: var(--app-accent); font-size: 1rem; }
.monthly-insights__heading > div { display: grid; gap: .42rem; min-width: 0; }
.monthly-insights__heading h3 { margin: 0; color: var(--app-text); font-size: .95rem; }
.monthly-insights__item p { margin: 0; color: var(--app-text-muted); line-height: 1.48; }
.monthly-insights__action { width: fit-content; color: var(--app-accent); font-size: .88rem; font-weight: 700; text-decoration: none; }
.monthly-insights__action:hover, .monthly-insights__action:focus-visible { color: var(--app-text); text-decoration: underline; }
@media (max-width: 42rem) { .monthly-insights__grid { grid-template-columns: 1fr; } }
</style>
