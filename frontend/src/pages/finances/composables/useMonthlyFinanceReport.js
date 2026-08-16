import { computed, ref } from 'vue'

import * as financesService from '../../../services/finances'
import { downloadBlob } from '../../../utils/download'

export function useMonthlyFinanceReport(financesStore) {
  const selectedMonth = ref('')
  const reportLoadId = ref(0)
  const trendsLoadId = ref(0)
  const exporting = ref(false)
  const exportError = ref('')

  const visibleReport = computed(() => {
    const report = financesStore.monthlyReport
    return report && report.month === selectedMonth.value ? report : null
  })
  const visibleTrends = computed(() => {
    const trends = financesStore.monthlyTrends
    return trends && trends.anchor_month === selectedMonth.value ? trends : null
  })
  const reportLoading = computed(() => financesStore.loadingMonthlyReport)
  const reportError = computed(() => financesStore.monthlyReportError)
  const trendsLoading = computed(() => financesStore.loadingMonthlyTrends)
  const trendsError = computed(() => financesStore.monthlyTrendsError)

  async function loadTrends(month = selectedMonth.value) {
    const loadId = ++trendsLoadId.value
    const requestedMonth = month || undefined
    try {
      const trends = await financesStore.fetchMonthlyTrends(requestedMonth)
      if (loadId !== trendsLoadId.value || trends.anchor_month !== selectedMonth.value) {
        return null
      }
      return trends
    } catch {
      return null
    }
  }

  async function loadReport() {
    const loadId = ++reportLoadId.value
    const requestedMonth = selectedMonth.value || undefined
    try {
      const report = await financesStore.fetchMonthlyReport(requestedMonth)
      if (loadId !== reportLoadId.value) {
        return null
      }
      if (!selectedMonth.value) {
        selectedMonth.value = report.month
      }
      if (report.month !== selectedMonth.value) {
        return null
      }
      await loadTrends(report.month)
      return report
    } catch {
      return null
    }
  }

  function enterWorkspace() {
    return loadReport()
  }

  function changeMonth(month) {
    if (!month || month === selectedMonth.value) {
      return Promise.resolve(null)
    }
    selectedMonth.value = month
    exportError.value = ''
    return loadReport()
  }

  function retryReport() {
    return loadReport()
  }

  function retryTrends() {
    return loadTrends()
  }

  async function exportReport() {
    const month = selectedMonth.value
    if (!month) {
      return
    }

    exportError.value = ''
    exporting.value = true
    try {
      const blob = await financesService.exportMonthlyReport(month)
      downloadBlob(blob, `habitflow-monthly-report-${month}.xlsx`)
    } catch {
      exportError.value = 'No fue posible exportar el reporte mensual.'
    } finally {
      exporting.value = false
    }
  }

  return {
    selectedMonth,
    visibleReport,
    visibleTrends,
    reportLoading,
    reportError,
    trendsLoading,
    trendsError,
    exporting,
    exportError,
    enterWorkspace,
    changeMonth,
    retryReport,
    retryTrends,
    exportReport,
  }
}
