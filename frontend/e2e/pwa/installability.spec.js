import { expect, test } from '@playwright/test'

const requiredIcons = [
  ['/icons/icon-192.png', 192],
  ['/icons/icon-512.png', 512],
  ['/icons/icon-maskable-512.png', 512],
]

function pngSize(buffer) {
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  }
}

test('expone el manifiesto y los iconos instalables', async ({ page, request }) => {
  const manifestResponse = await request.get('/manifest.webmanifest')
  expect(manifestResponse.ok()).toBe(true)
  const manifest = await manifestResponse.json()
  expect(manifest).toMatchObject({
    id: '/',
    name: 'HabitFlow',
    short_name: 'HabitFlow',
    lang: 'es-CO',
    start_url: '/dashboard',
    scope: '/',
    display: 'standalone',
    background_color: '#0a1017',
    theme_color: '#101823',
  })

  for (const [path, size] of requiredIcons) {
    const response = await request.get(path)
    expect(response.ok()).toBe(true)
    expect(pngSize(Buffer.from(await response.body()))).toEqual({ width: size, height: size })
  }

  await page.goto('/login')
  await expect(page.getByRole('heading', { name: /Iniciar sesi.n/ })).toBeVisible()
})

test('registra el service worker y entrega el fallback sin conexión', async ({ page, context }) => {
  const serviceWorker = context.waitForEvent('serviceworker')
  await page.goto('/login')
  await serviceWorker
  await page.reload()
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true)

  const cacheKeys = await page.evaluate(async () => {
    const names = await caches.keys()
    const entries = await Promise.all(names.map(async (name) => {
      const cache = await caches.open(name)
      return (await cache.keys()).map((request) => request.url)
    }))
    return entries.flat()
  })
  expect(cacheKeys.some((url) => new URL(url).pathname.startsWith('/api/'))).toBe(false)

  await context.setOffline(true)
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Sin conexión' })).toBeVisible()
  await context.setOffline(false)
})

test('conserva deep links y el diseño móvil sin desbordamiento', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: /Iniciar sesi.n/ })).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
