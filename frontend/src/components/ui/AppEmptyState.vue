<template>
  <div class="app-empty-state" :class="{ 'app-empty-state--compact': compact }">
    <i v-if="icon" :class="icon" aria-hidden="true"></i>
    <div>
      <strong v-if="title">{{ title }}</strong>
      <p v-if="message">{{ message }}</p>
      <slot />
    </div>
    <div v-if="$slots.action" class="app-empty-state__action"><slot name="action" /></div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '' },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-empty-state { display: flex; align-items: flex-start; gap: 0.8rem; padding: 1.15rem; border: 1px dashed var(--app-border-strong); border-radius: 0.8rem; color: var(--app-text-muted); }
.app-empty-state > i { margin-top: 0.1rem; color: var(--app-accent); font-size: 1.1rem; }
.app-empty-state strong { display: block; color: var(--app-text); }
.app-empty-state p { margin: 0.25rem 0 0; }
.app-empty-state__action { margin-left: auto; align-self: center; }
.app-empty-state--compact { padding: 0.8rem 1rem; }
@media (max-width: 36rem) { .app-empty-state { flex-wrap: wrap; } .app-empty-state__action { width: 100%; margin-left: 0; } }
</style>
