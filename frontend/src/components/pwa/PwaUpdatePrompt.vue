<template>
  <aside v-if="hasUpdate" class="pwa-prompt pwa-prompt--update" role="status">
    <div><strong>Hay una nueva versión disponible.</strong></div>
    <div class="pwa-prompt__actions">
      <Button type="button" label="Después" severity="secondary" variant="text" class="app-button app-button--compact" @click="dismissUpdate" />
      <Button type="button" label="Actualizar ahora" icon="pi pi-refresh" class="app-button app-button--compact" @click="updateNow" />
    </div>
  </aside>
</template>

<script setup>
import { usePwa } from '../../composables/usePwa'

const { hasUpdate, dismissUpdate, updateNow } = usePwa()
</script>
