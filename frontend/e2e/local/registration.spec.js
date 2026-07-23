import { registerLocalUser } from '../helpers/auth.js'
import { isLocalTarget } from '../helpers/environment.js'
import { expect, test } from '../fixtures/app-test.js'

test.skip(!isLocalTarget(), 'Las pruebas de escritura solo se ejecutan localmente.')

test('registra una cuenta local y abre el tablero', async ({ page }) => {
  await registerLocalUser(page)
  await expect(page.getByText('Visión general')).toBeVisible()
})
