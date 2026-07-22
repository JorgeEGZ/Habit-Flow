import { createApp } from 'vue'
import PrimeVue from 'primevue/config/config.esm.js'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import 'primeicons/primeicons.css'
import 'primevue/resources/primevue.min.css'
import 'primevue/resources/themes/lara-dark-blue/theme.css'
import './styles/theme.css'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(PrimeVue, {
  ripple: true,
})

app.component('Button', Button)
app.component('Card', Card)
app.component('Divider', Divider)
app.component('InputText', InputText)
app.component('Password', Password)

async function bootstrap() {
  const authStore = useAuthStore(pinia)
  window.addEventListener('habitflow:auth-invalid', async () => {
    authStore.clearAuth()
    await router.replace({ name: 'login' })
  })

  app.mount('#app')

  // Mount first so public routes never wait on a cross-origin refresh request.
  await authStore.initialize()

  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.guestOnly && authStore.isAuthenticated) {
    await router.replace({ name: 'dashboard' })
  }
}

bootstrap()
