<template>
  <span class="app-status-badge" :class="`app-status-badge--${tone}`">{{ label }}</span>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  tone: { type: String, default: 'neutral', validator: (value) => ['neutral', 'info', 'success', 'warning', 'danger'].includes(value) },
})
</script>

<style scoped>
.app-status-badge { display: inline-flex; align-items: center; width: fit-content; min-height: 1.65rem; padding: 0.18rem 0.55rem; border: 1px solid var(--app-border); border-radius: 999px; font-size: 0.76rem; font-weight: 700; line-height: 1.2; white-space: nowrap; }
.app-status-badge--neutral { background: rgba(148, 163, 184, 0.12); color: var(--app-text-muted); }
.app-status-badge--info { background: var(--app-accent-soft); border-color: rgba(85, 126, 230, 0.35); color: var(--app-text); }
.app-status-badge--success { background: rgba(74, 144, 108, 0.16); border-color: rgba(74, 144, 108, 0.4); color: #9ac8a7; }
.app-status-badge--warning { background: rgba(217, 154, 61, 0.15); border-color: rgba(217, 154, 61, 0.4); color: #efc47d; }
.app-status-badge--danger { background: rgba(202, 91, 91, 0.15); border-color: rgba(202, 91, 91, 0.42); color: #eea0a0; }
</style>
