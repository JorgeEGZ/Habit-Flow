import { defineConfig, devices } from '@playwright/test'

// The backend development CORS allowlist uses localhost by default.
const baseURL = process.env.BASE_URL || 'http://localhost:5173'
const hostname = new URL(baseURL).hostname
const isLocalTarget = hostname === 'localhost' || hostname === '127.0.0.1'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  outputDir: 'test-results',
  use: {
    baseURL,
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    navigationTimeout: 60_000,
    actionTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: isLocalTarget
    ? {
        command: 'npm run dev -- --host 127.0.0.1',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,
})
