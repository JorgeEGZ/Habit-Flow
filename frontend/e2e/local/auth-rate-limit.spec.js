import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('muestra un mensaje seguro en español cuando el borde limita el inicio de sesión', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 429,
      contentType: 'text/html; charset=utf-8',
      body: '<html><body>rate limit</body></html>',
    })
  })

  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill('rate-limit@example.test')
  await page.getByLabel('Contraseña').fill('valid-password')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(
    page.getByText('Demasiados intentos. Espera un momento e inténtalo de nuevo.'),
  ).toBeVisible()
  await expect(page.getByText('rate limit', { exact: true })).toHaveCount(0)
})
