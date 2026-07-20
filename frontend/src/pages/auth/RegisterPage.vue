<template>
  <AuthLayout
    title="Crear cuenta"
    subtitle="Registra tu cuenta para empezar a seguir tus hábitos y finanzas."
  >
    <form class="auth-form" @submit.prevent="handleSubmit">
      <label class="form-field">
        <span>Nombre completo</span>
        <InputText v-model="form.fullName" autocomplete="name" />
      </label>

      <label class="form-field">
        <span>Correo electrónico</span>
        <InputText v-model="form.email" type="email" autocomplete="email" />
      </label>

      <label class="form-field">
        <span>Contraseña</span>
        <Password
          v-model="form.password"
          toggle-mask
          input-class="auth-password"
          autocomplete="new-password"
        />
      </label>

      <p v-if="error" class="form-error">{{ error }}</p>

      <Button
        type="submit"
        label="Registrar"
        icon="pi pi-user-plus"
        class="auth-form__submit"
        :loading="authStore.loading"
      />

      <p class="auth-form__switch">
        ¿Ya tienes cuenta?
        <RouterLink to="/login">Inicia sesión</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

import AuthLayout from '../../layouts/AuthLayout.vue'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const form = reactive({
  fullName: '',
  email: '',
  password: '',
})

const error = computed(() => authStore.error)

async function handleSubmit() {
  try {
    await authStore.register({
      full_name: form.fullName || null,
      email: form.email,
      password: form.password,
    })

    await router.replace('/dashboard')
  } catch {
    return
  }
}
</script>
