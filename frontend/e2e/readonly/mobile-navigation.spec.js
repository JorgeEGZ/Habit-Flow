import { authenticate } from '../helpers/auth.js'
import { expect, test } from '../fixtures/app-test.js'

test('@readonly mantiene la navegación móvil sin desbordamiento horizontal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await authenticate(page)

  await expect(page.getByRole('navigation', { name: 'Navegación principal móvil' })).toBeVisible()

  for (const path of ['/dashboard', '/habits/today', '/savings/goals', '/finances/movements']) {
    await page.goto(path)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
})
