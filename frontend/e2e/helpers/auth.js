import { expect } from '@playwright/test'

import { createLocalUser } from './data.js'
import {
  assertLocalWritableTarget,
  getRenderCredentials,
  isLocalTarget,
} from './environment.js'

export async function registerLocalUser(page, user = createLocalUser()) {
  assertLocalWritableTarget()

  await page.goto('/register')
  await page.getByRole('heading', { name: 'Crear cuenta' }).waitFor()
  await page.getByLabel('Nombre completo').fill(user.fullName)
  await page.getByLabel('Correo electrónico').fill(user.email)
  await page.getByLabel('Contraseña').fill(user.password)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Registrar' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Tablero', exact: true })).toBeVisible()

  return user
}

export async function login(page, user) {
  await page.goto('/login')
  await page.getByRole('heading', { name: 'Iniciar sesión' }).waitFor()
  await page.getByLabel('Correo electrónico').fill(user.email)
  await page.getByLabel('Contraseña').fill(user.password)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Tablero', exact: true })).toBeVisible()
}

export async function authenticate(page) {
  if (isLocalTarget()) {
    return registerLocalUser(page)
  }

  const user = getRenderCredentials()
  await login(page, user)
  return user
}

export async function logout(page) {
  await page.getByRole('button', { name: /Abrir menú de usuario de/ }).click()
  await page.getByRole('menuitem', { name: 'Cerrar sesión' }).click()
  await expect(page).toHaveURL(/\/login$/)
}
