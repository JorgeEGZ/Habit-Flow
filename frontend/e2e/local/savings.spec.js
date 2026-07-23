import { authenticate } from '../helpers/auth.js'
import { uniqueSuffix } from '../helpers/data.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('crea una meta de ahorro y registra un aporte', async ({ page }) => {
  const goalName = 'Meta E2E ' + uniqueSuffix()
  await authenticate(page)

  await page.goto('/savings/goals')
  await page.getByRole('button', { name: 'Nueva meta' }).click()
  const goalDialog = page.getByRole('dialog', { name: 'Crear meta' })
  await goalDialog.getByLabel('Nombre').fill(goalName)
  await goalDialog.getByLabel('Meta monetaria').fill('100000')
  await goalDialog.getByRole('button', { name: 'Crear meta' }).click()
  await expect(page.getByText(goalName, { exact: true })).toBeVisible()

  const goalCard = page.locator('article').filter({ hasText: goalName })
  await goalCard.getByRole('button', { name: 'Ver detalle' }).click()
  await expect(page.getByRole('heading', { name: goalName, exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Registrar aporte' }).click()
  const contributionDialog = page.getByRole('dialog', { name: 'Registrar aporte' })
  await contributionDialog.getByLabel('Monto').fill('25000')
  await contributionDialog.getByRole('button', { name: 'Guardar aporte' }).click()
  await expect(page.getByRole('listitem').getByText('25.000', { exact: false })).toBeVisible()
})
