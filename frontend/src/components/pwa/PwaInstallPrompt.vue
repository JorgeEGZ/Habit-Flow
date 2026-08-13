<template>
  <aside v-if="canInstall && !isDismissed" class="pwa-prompt" aria-label="Instalar HabitFlow">
    <div>
      <strong>Instala HabitFlow</strong>
      <p>Accede más rápido desde tu pantalla de inicio.</p>
    </div>
    <div class="pwa-prompt__actions">
      <Button type="button" label="Ahora no" severity="secondary" variant="text" class="app-button app-button--compact" @click="dismiss" />
      <Button type="button" label="Instalar" icon="pi pi-download" class="app-button app-button--compact" @click="install" />
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'

import { usePwa } from '../../composables/usePwa'

const { canInstall, promptInstall } = usePwa()
const isDismissed = ref(false)

function dismiss() {
  isDismissed.value = true
}

async function install() {
  await promptInstall()
}
</script>
