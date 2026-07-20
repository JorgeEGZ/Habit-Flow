<template>
  <AuthLayout
    title="Iniciar sesión"
    subtitle="Accede a tu cuenta para revisar hábitos, ahorros y finanzas."
  >
    <form class="auth-form" @submit.prevent="handleSubmit">
      <label class="form-field">
        <span>Correo electrónico</span>
        <InputText v-model="form.email" type="email" autocomplete="email" />
      </label>

      <label class="form-field">
        <span>Contraseña</span>
        <Password
          v-model="form.password"
          :feedback="false"
          toggle-mask
          input-class="auth-password"
          autocomplete="current-password"
        />
      </label>

      <p v-if="error" class="form-error">{{ error }}</p>

      <Button
        type="submit"
        label="Entrar"
        icon="pi pi-sign-in"
        class="auth-form__submit"
        :loading="authStore.loading"
      />

      <p class="auth-form__switch">
        ¿No tienes cuenta?
        <RouterLink to="/register">Regístrate</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AuthLayout from '../../layouts/AuthLayout.vue'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({
  email: '',
  password: '',
})

const error = computed(() => authStore.error)

async function handleSubmit() {
  try {
    await authStore.login({
      email: form.email,
      password: form.password,
    })

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch {
    return
  }
}
</script>
