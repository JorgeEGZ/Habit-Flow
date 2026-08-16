import { stat } from 'node:fs/promises'

import { authenticate } from '../helpers/auth.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

function hasPath(url, path) {
  return new URL(url).pathname.endsWith(path)
}

function reportResponseFor(month) {
  return (response) => (
    hasPath(response.url(), '/finances/reports/monthly')
    && new URL(response.url()).searchParams.get('month') === month
    && response.status() === 200
  )
}

function trendsResponseFor(month) {
  return (response) => (
    hasPath(response.url(), '/finances/reports/monthly-trends')
    && new URL(response.url()).searchParams.get('month') === month
    && response.status() === 200
  )
}

async function openReports(page) {
  const defaultReport = page.waitForResponse((response) => (
    hasPath(response.url(), '/finances/reports/monthly')
    && !new URL(response.url()).searchParams.has('month')
    && response.status() === 200
  ))
  const defaultTrends = page.waitForResponse((response) => (
    hasPath(response.url(), '/finances/reports/monthly-trends')
    && response.status() === 200
  ))

  await page.goto('/finances/reports')
  const reportResponse = await defaultReport
  const report = await reportResponse.json()
  const trendsResponse = await defaultTrends

  expect(new URL(trendsResponse.url()).searchParams.get('month')).toBe(report.month)
  await expect(page.getByRole('heading', { name: 'Reporte mensual', level: 2 })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Mes' })).toHaveValue(report.month)
  return report.month
}

test('sincroniza el mes del reporte, mantiene semantica accesible y exporta el libro', async ({ page }) => {
  await authenticate(page)
  await openReports(page)

  const monthInput = page.getByRole('textbox', { name: 'Mes' })
  const reportResponse = page.waitForResponse(reportResponseFor('2030-01'))
  const trendsResponse = page.waitForResponse(trendsResponseFor('2030-01'))
  await monthInput.fill('2030-01')
  await reportResponse
  await trendsResponse

  await expect(monthInput).toHaveValue('2030-01')
  await expect(page.getByRole('heading', { name: 'Lectura del mes', level: 3 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Tendencia de 6 meses', level: 3 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Gastos por categor\u00eda', level: 3 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Presupuestos del mes', level: 3 })).toBeVisible()
  await expect(page.getByText('No hay movimientos registrados para el mes seleccionado. Registra ingresos y gastos para obtener una lectura financiera.')).toBeVisible()
  await expect(page.getByText('no_activity', { exact: true })).toHaveCount(0)
  await expect(page.locator('[aria-labelledby="monthly-report-title"]')).toHaveAttribute('aria-busy', 'false')
  await expect(page.locator('[aria-labelledby="monthly-trends-title"]')).toHaveAttribute('aria-busy', 'false')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Exportar Excel' }).click(),
  ])
  expect(download.suggestedFilename()).toBe('habitflow-monthly-report-2030-01.xlsx')
  const downloadPath = await download.path()
  expect(downloadPath).not.toBeNull()
  expect((await stat(downloadPath)).size).toBeGreaterThan(0)

  for (const viewport of [{ width: 360, height: 800 }, { width: 390, height: 844 }, { width: 430, height: 932 }]) {
    await page.setViewportSize(viewport)
    expect(await page.locator('html').evaluate((element) => element.scrollWidth)).toBeLessThanOrEqual(viewport.width)
    for (const locator of [
      monthInput,
      page.getByRole('button', { name: 'Exportar Excel' }),
      page.locator('.monthly-report__kpis'),
      page.locator('.monthly-insights'),
      page.locator('.monthly-trends'),
    ]) {
      const box = await locator.boundingBox()
      expect(box).not.toBeNull()
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width)
    }
  }
})

test('muestra errores controlados de reporte, tendencias y exportacion con reintentos', async ({ page }) => {
  await authenticate(page)

  let abortReport = true
  await page.route(
    (url) => hasPath(url.toString(), '/finances/reports/monthly'),
    async (route) => {
      if (abortReport) {
        abortReport = false
        await route.abort('failed')
        return
      }
      await route.continue()
    },
  )
  await page.goto('/finances/reports')
  await expect(page.getByRole('alert')).toContainText('No fue posible cargar el reporte mensual.')
  await page.getByRole('button', { name: 'Reintentar' }).click()
  await expect(page.getByRole('heading', { name: 'Reporte mensual', level: 2 })).toBeVisible()
  await expect(page.getByText('No hay movimientos registrados para el mes seleccionado. Registra ingresos y gastos para obtener una lectura financiera.')).toBeVisible()

  let abortTrends = true
  await page.route(
    (url) => hasPath(url.toString(), '/finances/reports/monthly-trends'),
    async (route) => {
      if (abortTrends) {
        abortTrends = false
        await route.abort('failed')
        return
      }
      await route.continue()
    },
  )
  const reportMonth = await page.getByRole('textbox', { name: 'Mes' }).inputValue()
  const reportResponse = page.waitForResponse(reportResponseFor('2030-01'))
  await page.getByRole('textbox', { name: 'Mes' }).fill('2030-01')
  await reportResponse
  await expect(page.getByText('No fue posible cargar las tendencias mensuales.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Gastos por categor\u00eda', level: 3 })).toBeVisible()
  await page.getByRole('button', { name: 'Reintentar' }).click()
  await expect(page.locator('[aria-labelledby="monthly-trends-title"]')).toHaveAttribute('aria-busy', 'false')
  expect(reportMonth).toMatch(/^\d{4}-\d{2}$/)

  let abortExport = true
  await page.route(
    (url) => hasPath(url.toString(), '/finances/reports/monthly.xlsx'),
    async (route) => {
      if (abortExport) {
        abortExport = false
        await route.abort('failed')
        return
      }
      await route.continue()
    },
  )
  const exportButton = page.getByRole('button', { name: 'Exportar Excel' })
  await exportButton.click()
  await expect(page.getByRole('alert')).toContainText('No fue posible exportar el reporte mensual.')
  await expect(exportButton).toBeEnabled()
})

test('mantiene el mes mas reciente cuando una respuesta anterior termina despues', async ({ page }) => {
  await authenticate(page)
  await openReports(page)

  let releaseJanuary
  const januaryRelease = new Promise((resolve) => { releaseJanuary = resolve })
  await page.route(
    (url) => (
      hasPath(url.toString(), '/finances/reports/monthly')
      && new URL(url).searchParams.get('month') === '2026-01'
    ),
    async (route) => {
      await januaryRelease
      await route.continue()
    },
  )

  const monthInput = page.getByRole('textbox', { name: 'Mes' })
  const januaryRequest = page.waitForRequest((request) => (
    hasPath(request.url(), '/finances/reports/monthly')
    && new URL(request.url()).searchParams.get('month') === '2026-01'
  ))
  const januaryResponse = page.waitForResponse(reportResponseFor('2026-01'))
  await monthInput.fill('2026-01')
  await januaryRequest

  const februaryReport = page.waitForResponse(reportResponseFor('2026-02'))
  const februaryTrends = page.waitForResponse(trendsResponseFor('2026-02'))
  await monthInput.fill('2026-02')
  await februaryReport
  await februaryTrends

  releaseJanuary()
  await januaryResponse
  await expect(monthInput).toHaveValue('2026-02')
  await expect(page.getByText('No hay movimientos registrados para el mes seleccionado. Registra ingresos y gastos para obtener una lectura financiera.')).toBeVisible()
  await expect(page.getByLabel('Cargando reporte mensual')).toHaveCount(0)
})
