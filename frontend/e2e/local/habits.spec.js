import { authenticate } from '../helpers/auth.js'
import { uniqueSuffix } from '../helpers/data.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('crea y registra un hábito diario de hecho o no hecho', async ({ page }) => {
  const title = 'Hábito E2E ' + uniqueSuffix()
  await authenticate(page)

  await page.goto('/habits/manage')
  await page.getByRole('button', { name: 'Nuevo hábito' }).click()
  const dialog = page.getByRole('dialog', { name: 'Crear hábito' })
  await dialog.getByLabel('Título').fill(title)
  await dialog.getByRole('button', { name: 'Crear hábito' }).click()
  await expect(page.getByText(title, { exact: true })).toBeVisible()

  await page.goto('/habits/today')
  const habitCard = page.locator('article').filter({ hasText: title })
  await habitCard.getByRole('button', { name: 'Marcar como hecho' }).click()
  await expect(habitCard.locator('.habit-daily-status', { hasText: 'Completado hoy' })).toBeVisible()

  await page.reload()
  await expect(page.locator('article').filter({ hasText: title }).locator('.habit-daily-status', { hasText: 'Completado hoy' })).toBeVisible()
})
