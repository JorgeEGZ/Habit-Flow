import { authenticate } from '../helpers/auth.js'
import { uniqueSuffix } from '../helpers/data.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('gestiona y exporta el historial de aportes de una meta', async ({ page }) => {
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

  await page.getByRole('button', { name: 'Editar aporte' }).click()
  const editDialog = page.getByRole('dialog', { name: 'Editar aporte' })
  await editDialog.getByLabel('Monto').fill('30000')
  await editDialog.getByLabel('Nota').fill('Aporte corregido')
  await editDialog.getByRole('button', { name: 'Guardar cambios' }).click()
  await expect(page.getByText('Aporte actualizado.')).toBeVisible()
  await expect(page.getByRole('listitem').getByText('30.000', { exact: false })).toBeVisible()
  await expect(page.getByText('Aporte corregido', { exact: true })).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar CSV' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/^habitflow-savings-contributions-.*\.csv$/)

  const workbookDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar Excel' }).click()
  const workbookDownload = await workbookDownloadPromise
  expect(workbookDownload.suggestedFilename()).toMatch(/^habitflow-savings-contributions-.*\.xlsx$/)

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Eliminar aporte' }).click()
  await expect(page.getByText('Aporte eliminado.')).toBeVisible()
  await expect(page.getByText('Esta meta todavía no tiene contribuciones.')).toBeVisible()
})
