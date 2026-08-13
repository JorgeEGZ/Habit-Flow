<template>
  <Button
    :type="type"
    :icon="icon"
    :severity="tone === 'danger' ? 'danger' : 'secondary'"
    variant="outlined"
    class="app-button app-button--icon"
    :class="tone === 'danger' ? 'app-button--danger' : 'app-button--icon-secondary'"
    :aria-label="label"
    :disabled="disabled"
    :loading="loading"
    @click="$emit('click', $event)"
  />
</template>

<script setup>
import Button from 'primevue/button'

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  tone: { type: String, default: 'secondary', validator: (value) => ['secondary', 'danger'].includes(value) },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
})

defineEmits(['click'])
</script>
