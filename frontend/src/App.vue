<template>
  <router-view v-if="canRenderRoute" />
  <main v-else class="app-startup" aria-live="polite">
    <div>
      <span class="app-startup__mark">H</span>
      <p>Cargando tu espacio...</p>
    </div>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const route = useRoute()

const canRenderRoute = computed(() => (
  route.matched.some((record) => record.meta.guestOnly)
  || authStore.isReady
))
</script>
