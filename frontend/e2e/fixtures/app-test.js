import { expect, test as base } from '@playwright/test'

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const pageErrors = []
    const serverErrors = []

    page.on('pageerror', (error) => {
      pageErrors.push(error.message)
    })
    page.on('response', (response) => {
      if (response.status() >= 500 && response.url().includes('/api/v1/')) {
        serverErrors.push(response.status() + ' ' + response.url())
      }
    })

    await use(page)

    if (testInfo.status === testInfo.expectedStatus) {
      expect(pageErrors, 'La página no debe generar errores no controlados.').toEqual([])
      expect(serverErrors, 'La API no debe responder con errores 5xx.').toEqual([])
    }
  },
})

export { expect }
