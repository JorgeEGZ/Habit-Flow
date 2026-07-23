import { authenticate } from '../helpers/auth.js'
import { expect, test } from '../fixtures/app-test.js'

test('@readonly navega por los módulos autenticados', async ({ page }) => {
  await authenticate(page)

  const routes = [
    ['/dashboard', 'Tablero'],
    ['/profile', 'Mi perfil'],
    ['/habits/today', 'Hábitos'],
    ['/habits/manage', 'Hábitos'],
    ['/savings/goals', 'Ahorros'],
    ['/finances/movements', 'Finanzas'],
    ['/finances/budgets', 'Finanzas'],
    ['/finances/recurring', 'Finanzas'],
    ['/finances/accounts', 'Finanzas'],
    ['/finances/categories', 'Finanzas'],
  ]

  for (const [path, heading] of routes) {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  }
})
