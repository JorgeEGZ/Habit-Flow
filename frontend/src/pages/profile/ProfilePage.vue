<template>
  <section class="profile-page page-stack">
    <header class="profile-page__header">
      <div>
        <p class="profile-page__eyebrow">Cuenta</p>
        <h1>Mi perfil</h1>
        <p>Administra tu información personal y la seguridad de tu cuenta.</p>
      </div>
    </header>

    <div class="profile-grid">
      <Card class="profile-card">
        <template #title>Información personal</template>
        <template #subtitle>Actualiza el nombre que usamos para identificarte.</template>
        <template #content>
          <form class="profile-form" @submit.prevent="handleProfileSubmit">
            <label class="form-field">
              <span>Nombre completo</span>
              <InputText
                v-model="profileForm.fullName"
                maxlength="120"
                autocomplete="name"
                :disabled="authStore.profileLoading"
              />
            </label>

            <label class="form-field">
              <span>Correo electrónico</span>
              <InputText
                :model-value="authStore.user?.email || ''"
                type="email"
                autocomplete="email"
                readonly
                aria-describedby="profile-email-help"
              />
              <small id="profile-email-help" class="form-helper">El correo no se puede cambiar.</small>
            </label>

            <p v-if="profileError" class="form-error" role="alert">{{ profileError }}</p>
            <p v-if="profileSuccess" class="form-success" role="status">{{ profileSuccess }}</p>

            <div class="profile-form__actions">
              <Button
                type="submit"
                label="Guardar cambios"
                icon="pi pi-check"
                :loading="authStore.profileLoading"
              />
            </div>
          </form>
        </template>
      </Card>

      <Card class="profile-card">
        <template #title>Seguridad</template>
        <template #subtitle>Cambia tu contraseña y vuelve a iniciar sesión de forma segura.</template>
        <template #content>
          <form class="profile-form" @submit.prevent="handlePasswordSubmit">
            <label class="form-field">
              <span>Contraseña actual</span>
              <Password
                v-model="passwordForm.currentPassword"
                :feedback="false"
                toggle-mask
                autocomplete="current-password"
                :disabled="authStore.passwordLoading"
              />
            </label>

            <label class="form-field">
              <span>Nueva contraseña</span>
              <Password
                v-model="passwordForm.newPassword"
                :feedback="false"
                toggle-mask
                autocomplete="new-password"
                :disabled="authStore.passwordLoading"
              />
            </label>

            <label class="form-field">
              <span>Confirmar nueva contraseña</span>
              <Password
                v-model="passwordForm.confirmPassword"
                :feedback="false"
                toggle-mask
                autocomplete="new-password"
                :disabled="authStore.passwordLoading"
              />
            </label>

            <p v-if="passwordError" class="form-error" role="alert">{{ passwordError }}</p>

            <div class="profile-form__actions">
              <Button
                type="submit"
                label="Actualizar contraseña"
                icon="pi pi-lock"
                :loading="authStore.passwordLoading"
              />
            </div>
          </form>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const profileForm = reactive({ fullName: '' })
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')

watch(
  () => authStore.user?.full_name,
  (fullName) => {
    profileForm.fullName = fullName || ''
  },
  { immediate: true }
)

async function handleProfileSubmit() {
  profileError.value = ''
  profileSuccess.value = ''

  const fullName = profileForm.fullName.trim()
  if (fullName.length > 120) {
    profileError.value = 'El nombre completo no puede superar los 120 caracteres.'
    return
  }

  try {
    await authStore.updateProfile({ full_name: fullName || null })
    profileSuccess.value = 'Perfil actualizado.'
  } catch {
    profileError.value = authStore.error || 'No fue posible actualizar el perfil.'
  }
}

function validatePasswordForm() {
  if (!passwordForm.currentPassword) {
    return 'Ingresa tu contraseña actual.'
  }
  if (!passwordForm.newPassword) {
    return 'Ingresa una nueva contraseña.'
  }
  if (passwordForm.newPassword.length < 8) {
    return 'La nueva contraseña debe tener al menos 8 caracteres.'
  }
  if (passwordForm.newPassword.length > 128) {
    return 'La nueva contraseña no puede superar los 128 caracteres.'
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    return 'Las contraseñas nuevas no coinciden.'
  }
  return ''
}

async function handlePasswordSubmit() {
  passwordError.value = validatePasswordForm()
  if (passwordError.value) {
    return
  }

  try {
    await authStore.changePassword({
      current_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
    })
    await router.replace({ name: 'login', query: { passwordChanged: '1' } })
  } catch {
    passwordError.value = authStore.error || 'No fue posible actualizar la contraseña.'
  }
}
</script>
