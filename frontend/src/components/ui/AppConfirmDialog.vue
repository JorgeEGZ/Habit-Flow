<template>
  <Dialog
    :visible="visible"
    modal
    dismissableMask
    class="app-dialog app-confirm-dialog"
    :header="title"
    @update:visible="handleVisibilityChange"
  >
    <p class="app-confirm-dialog__message">{{ message }}</p>
    <template #footer>
      <Button type="button" :label="cancelLabel" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="loading" @click="handleCancel" />
      <Button type="button" :label="confirmLabel" icon="pi pi-trash" :severity="destructive ? 'danger' : undefined" :class="destructive ? 'app-button app-button--danger' : 'app-button app-button--primary'" :loading="loading" @click="$emit('confirm')" />
    </template>
  </Dialog>
</template>

<script setup>
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

const props = defineProps({
  visible: { type: Boolean, required: true },
  title: { type: String, required: true },
  message: { type: String, required: true },
  confirmLabel: { type: String, default: 'Confirmar' },
  cancelLabel: { type: String, default: 'Cancelar' },
  loading: { type: Boolean, default: false },
  destructive: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

function handleVisibilityChange(nextVisible) {
  emit('update:visible', nextVisible)
  if (!nextVisible) emit('cancel')
}

function handleCancel() {
  if (!props.visible) return
  emit('update:visible', false)
  emit('cancel')
}
</script>

<style scoped>
.app-confirm-dialog__message { margin: 0; color: var(--app-text-muted); line-height: 1.55; }
</style>
