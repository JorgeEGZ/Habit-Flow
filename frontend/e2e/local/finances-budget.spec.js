import { authenticate } from '../helpers/auth.js'
import { readFile } from 'node:fs/promises'
import { currentMonth, uniqueSuffix } from '../helpers/data.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('crea movimientos reales y un presupuesto mensual local', async ({ page }) => {
  const suffix = uniqueSuffix()
  const accountName = 'Cuenta E2E ' + suffix
  const categoryName = 'Categoría E2E ' + suffix
  await authenticate(page)

  await page.goto('/finances/accounts')
  await page.getByRole('button', { name: 'Nueva cuenta' }).click()
  let dialog = page.getByRole('dialog', { name: 'Crear cuenta' })
  await dialog.getByLabel('Nombre').fill(accountName)
  await dialog.getByLabel('Saldo inicial').fill('0')
  await dialog.getByRole('button', { name: 'Crear cuenta' }).click()
  await expect(page.getByText(accountName, { exact: true })).toBeVisible()

  await page.goto('/finances/categories')
  await page.getByRole('button', { name: 'Nueva categoría' }).click()
  dialog = page.getByRole('dialog', { name: 'Crear categoría' })
  await dialog.getByLabel('Nombre').fill(categoryName)
  await dialog.getByRole('button', { name: 'Gasto' }).click()
  await dialog.getByRole('button', { name: 'Crear categoría' }).click()
  await expect(page.getByText(categoryName, { exact: true })).toBeVisible()

  await page.goto('/finances/movements')
  await page.getByRole('button', { name: 'Nuevo movimiento' }).click()
  dialog = page.getByRole('dialog', { name: 'Crear movimiento' })
  await dialog.getByLabel('Monto').fill('25000')
  await dialog.getByLabel('Cuenta').selectOption({ label: `${accountName} - Corriente` })
  await dialog.getByRole('button', { name: 'Gasto' }).click()
  await dialog.getByLabel('Categoría').selectOption({ label: categoryName })
  await dialog.getByLabel('Descripción').fill('Movimiento E2E')
  await dialog.getByRole('button', { name: 'Crear movimiento' }).click()
  await expect(page.getByText('Movimiento E2E', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Exportar CSV' }).click()
  dialog = page.getByRole('dialog', { name: 'Exportar movimientos' })
  const [csvDownload] = await Promise.all([
    page.waitForEvent('download'),
    dialog.getByRole('button', { name: 'Exportar CSV' }).click(),
  ])
  expect(csvDownload.suggestedFilename()).toMatch(/^habitflow-transactions-\d{4}-\d{2}-\d{2}-to-\d{4}-\d{2}-\d{2}\.csv$/)
  const csvPath = await csvDownload.path()
  expect(csvPath).not.toBeNull()
  const csv = await readFile(csvPath, 'utf8')
  expect(csv).toContain('transaction_date,type,amount')
  expect(csv).toContain('Movimiento E2E')

  await page.getByRole('button', { name: 'Exportar Excel' }).first().click()
  dialog = page.getByRole('dialog', { name: 'Exportar movimientos' })
  const [xlsxDownload] = await Promise.all([
    page.waitForEvent('download'),
    dialog.getByRole('button', { name: 'Exportar Excel' }).click(),
  ])
  expect(xlsxDownload.suggestedFilename()).toMatch(/^habitflow-transactions-\d{4}-\d{2}-\d{2}-to-\d{4}-\d{2}-\d{2}\.xlsx$/)

  await page.goto('/finances/budgets')
  await page.getByRole('button', { name: 'Nuevo presupuesto' }).click()
  dialog = page.getByRole('dialog', { name: 'Nuevo presupuesto' })
  await dialog.getByLabel('Mes').fill(currentMonth())
  await dialog.getByLabel('Categoría').selectOption({ label: categoryName })
  await dialog.getByRole('spinbutton', { name: 'Presupuesto' }).fill('50000')
  await dialog.getByRole('button', { name: 'Crear presupuesto' }).click()
  await expect(page.getByText(categoryName, { exact: true })).toBeVisible()

  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Presupuestos del mes' })).toBeVisible()
})
