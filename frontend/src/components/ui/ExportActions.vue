<template>
  <div class="app-export-actions" :class="{ 'app-export-actions--compact': compact }">
    <Button type="button" :label="csvLabel" icon="pi pi-download" severity="secondary" variant="outlined" class="app-button app-button--secondary" :class="{ 'app-button--compact': compact }" :loading="loadingFormat === 'csv'" :disabled="disabled || Boolean(loadingFormat)" @click="$emit('export', 'csv')" />
    <Button type="button" :label="xlsxLabel" icon="pi pi-file-excel" severity="secondary" variant="outlined" class="app-button app-button--secondary" :class="{ 'app-button--compact': compact }" :loading="loadingFormat === 'xlsx'" :disabled="disabled || Boolean(loadingFormat)" @click="$emit('export', 'xlsx')" />
  </div>
</template>

<script setup>
import Button from 'primevue/button'

defineProps({
  loadingFormat: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  csvLabel: { type: String, default: 'Exportar CSV' },
  xlsxLabel: { type: String, default: 'Exportar Excel' },
})

defineEmits(['export'])
</script>

<style scoped>
.app-export-actions { display: flex; flex-wrap: wrap; gap: 0.55rem; }
.app-export-actions--compact { gap: 0.4rem; }
</style>
