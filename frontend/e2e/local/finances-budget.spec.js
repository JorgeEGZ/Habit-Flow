import { authenticate } from '../helpers/auth.js'
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
  await dialog.getByLabel('Cuenta').selectOption({ label: accountName })
  await dialog.getByRole('button', { name: 'Gasto' }).click()
  await dialog.getByLabel('Categoría').selectOption({ label: categoryName })
  await dialog.getByLabel('Descripción').fill('Movimiento E2E')
  await dialog.getByRole('button', { name: 'Crear movimiento' }).click()
  await expect(page.getByText('Movimiento E2E', { exact: true })).toBeVisible()

  await page.goto('/finances/budgets')
  await page.getByRole('button', { name: 'Nuevo presupuesto' }).click()
  dialog = page.getByRole('dialog', { name: 'Nuevo presupuesto' })
  await dialog.getByLabel('Mes').fill(currentMonth())
  await dialog.getByLabel('Categoría').selectOption({ label: categoryName })
  await dialog.getByLabel('Presupuesto').fill('50000')
  await dialog.getByRole('button', { name: 'Crear presupuesto' }).click()
  await expect(page.getByText(categoryName, { exact: true })).toBeVisible()

  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Presupuestos del mes' })).toBeVisible()
})
