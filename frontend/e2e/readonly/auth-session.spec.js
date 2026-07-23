import { authenticate, login, logout, registerLocalUser } from '../helpers/auth.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test('@readonly muestra el inicio de sesión y protege el tablero anónimo', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible()

  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login\?redirect=(?:%2F|\/)dashboard/)
})

test('@readonly restaura la sesión después de recargar y permite cerrar sesión', async ({ page }) => {
  if (isLocalTarget()) {
    const user = await registerLocalUser(page)
    await logout(page)
    await login(page, user)
  } else {
    await authenticate(page)
  }

  await page.reload()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Tablero', exact: true })).toBeVisible()

  await logout(page)
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login\?redirect=(?:%2F|\/)dashboard/)
})
