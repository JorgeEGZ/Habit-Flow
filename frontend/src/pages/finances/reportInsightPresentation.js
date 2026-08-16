import { formatCurrencyCop } from '../../utils/format'

const budgetCodes = new Set([
  'budget_exceeded',
  'budget_limit_reached',
  'budget_near_limit',
])

const toneLabels = {
  neutral: 'Resumen',
  info: 'Información',
  success: 'Evolución favorable',
  warning: 'Para revisar',
  danger: 'Requiere atención',
}

export function getMonthlyInsightPresentation(insight) {
  const values = insight.values || {}
  const code = insight.code

  return {
    key: code,
    title: titleFor(code),
    message: messageFor(code, values),
    badgeLabel: toneLabels[insight.tone] || toneLabels.neutral,
    icon: iconFor(code),
    action: actionFor(code),
    tone: insight.tone,
  }
}

function titleFor(code) {
  return {
    no_activity: 'Sin movimientos',
    budget_exceeded: 'Presupuestos excedidos',
    budget_limit_reached: 'Límite de presupuesto',
    budget_near_limit: 'Presupuestos cerca del límite',
    negative_net: 'Balance neto negativo',
    positive_savings_rate: 'Ingreso restante',
    break_even: 'Balance del mes',
    no_income: 'Sin ingresos registrados',
    expenses_increased: 'Gastos frente al mes anterior',
    expenses_decreased: 'Gastos frente al mes anterior',
    expenses_no_comparison: 'Comparación de gastos',
    top_spending_category: 'Mayor gasto del mes',
  }[code] || 'Resumen del mes'
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

function messageFor(code, values) {
  const count = Number(values.count || 0)
  const budgetLabel = `${count} ${count === 1 ? 'presupuesto' : 'presupuestos'}`
  const percentage = (value) => `${Number(value || 0).toFixed(2)}%`

  switch (code) {
    case 'no_activity':
      return 'No hay movimientos registrados para el mes seleccionado. Registra ingresos y gastos para obtener una lectura financiera.'
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
