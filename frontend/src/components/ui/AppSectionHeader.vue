<template>
  <header class="app-section-header">
    <slot v-if="custom" />
    <div v-else class="app-section-header__content">
      <p v-if="$slots.eyebrow" class="app-section-header__eyebrow"><slot name="eyebrow" /></p>
      <component :is="`h${headingLevel}`" :id="headingId" class="app-section-header__title">{{ title }}</component>
      <p v-if="description" class="app-section-header__description">{{ description }}</p>
      <slot />
    </div>
    <div v-if="$slots.actions" class="app-section-header__actions"><slot name="actions" /></div>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  headingLevel: { type: Number, default: 2, validator: (value) => [1, 2, 3].includes(value) },
  headingId: { type: String, default: '' },
  custom: { type: Boolean, default: false },
})
</script>

<style scoped>
.app-section-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.app-section-header__content { min-width: 0; }
.app-section-header__eyebrow { margin: 0 0 0.35rem; color: var(--app-text-muted); font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.app-section-header__title { margin: 0; color: var(--app-text); }
.app-section-header__description { margin: 0.45rem 0 0; color: var(--app-text-muted); }
.app-section-header__actions { display: flex; flex: 0 0 auto; flex-wrap: wrap; justify-content: flex-end; gap: 0.55rem; }
@media (max-width: 48rem) { .app-section-header { flex-direction: column; } .app-section-header__actions { width: 100%; justify-content: flex-start; } }
</style>
