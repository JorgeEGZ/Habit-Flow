<template>
  <div class="app-shell">
    <aside class="app-shell__sidebar">
      <SidebarNav />
    </aside>

    <div class="app-shell__main">
      <header class="app-shell__topbar">
        <div>
          <p class="app-shell__eyebrow">HabitFlow</p>
          <h2 class="app-shell__title">{{ pageTitle }}</h2>
        </div>
        <Button
          class="app-shell__logout"
          severity="secondary"
          variant="outlined"
          icon="pi pi-sign-out"
          label="Cerrar sesión"
          @click="handleLogout"
        />
      </header>

      <main class="app-shell__content">
        <router-view />
      </main>
    </div>

    <BottomNav class="app-shell__bottom-nav" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SidebarNav from '../components/layout/SidebarNav.vue'
import BottomNav from '../components/layout/BottomNav.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const pageTitle = computed(() => route.meta.title || 'HabitFlow')

async function handleLogout() {
  await authStore.logout()
  await router.push({ name: 'login' })
}
</script>
