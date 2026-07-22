<template>
  <div class="user-menu">
    <button
      type="button"
      class="user-menu__trigger"
      aria-haspopup="menu"
      aria-controls="user-menu-popup"
      :aria-expanded="menuOpen"
      :aria-label="`Abrir menú de usuario de ${displayName}`"
      @click="toggleMenu"
    >
      <span class="user-menu__avatar" aria-hidden="true">{{ initials }}</span>
      <span class="user-menu__identity">
        <strong>{{ displayName }}</strong>
        <small v-if="hasFullName">{{ authStore.user?.email }}</small>
      </span>
      <i class="pi pi-chevron-down" aria-hidden="true"></i>
    </button>

    <Menu
      id="user-menu-popup"
      ref="menu"
      :model="menuItems"
      :popup="true"
      class="user-menu__popup"
      @show="menuOpen = true"
      @hide="menuOpen = false"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Menu from 'primevue/menu'

import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const menu = ref(null)
const menuOpen = ref(false)

const fullName = computed(() => authStore.user?.full_name?.trim() || '')
const hasFullName = computed(() => Boolean(fullName.value))
const displayName = computed(() => fullName.value || authStore.user?.email || 'Mi cuenta')
const initials = computed(() => {
  if (!fullName.value) {
    return (authStore.user?.email?.[0] || 'U').toUpperCase()
  }

  return fullName.value
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
})

const menuItems = computed(() => [
  {
    label: 'Mi perfil',
    icon: 'pi pi-user',
    command: () => router.push({ name: 'profile' }),
  },
  {
    separator: true,
  },
  {
    label: 'Cerrar sesión',
    icon: 'pi pi-sign-out',
    command: handleLogout,
  },
])

function toggleMenu(event) {
  menu.value.toggle(event)
}

async function handleLogout() {
  try {
    await authStore.logout()
  } catch {
    // logout() clears local authentication state in its finally block.
  }
  await router.push({ name: 'login' })
}
</script>
