import { computed, ref } from 'vue'

const deferredInstallPrompt = ref(null)
const isInstalled = ref(false)
const hasUpdate = ref(false)
const updateWorker = ref(null)
const isRegistered = ref(false)
let reloadedAfterUpdate = false
let updateRequested = false

function detectStandalone() {
  return window.matchMedia?.('(display-mode: standalone)').matches
    || window.navigator.standalone === true
}

function setupWindowListeners() {
  if (typeof window === 'undefined' || window.__habitflowPwaListeners) return

  window.__habitflowPwaListeners = true
  isInstalled.value = detectStandalone()
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    deferredInstallPrompt.value = event
  })
  window.addEventListener('appinstalled', () => {
    isInstalled.value = true
    deferredInstallPrompt.value = null
  })
}

export function usePwa() {
  setupWindowListeners()
  const canInstall = computed(() => Boolean(deferredInstallPrompt.value) && !isInstalled.value)

  async function promptInstall() {
    const prompt = deferredInstallPrompt.value
    if (!prompt) return false
    await prompt.prompt()
    await prompt.userChoice
    deferredInstallPrompt.value = null
    return true
  }

  return {
    canInstall,
    hasUpdate,
    promptInstall,
    updateNow: () => {
      updateRequested = true
      updateWorker.value?.postMessage({ type: 'SKIP_WAITING' })
    },
    dismissUpdate: () => { hasUpdate.value = false },
  }
}

export async function registerPwa() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator) || isRegistered.value) return

  isRegistered.value = true
  setupWindowListeners()
  const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' })

  if (registration.waiting) {
    updateWorker.value = registration.waiting
    hasUpdate.value = true
  }

  registration.addEventListener('updatefound', () => {
    const worker = registration.installing
    if (!worker) return
    worker.addEventListener('statechange', () => {
      if (worker.state === 'installed' && navigator.serviceWorker.controller) {
        updateWorker.value = worker
        hasUpdate.value = true
      }
    })
  })

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (updateRequested && !reloadedAfterUpdate) {
      reloadedAfterUpdate = true
      window.location.reload()
    }
  })
}
