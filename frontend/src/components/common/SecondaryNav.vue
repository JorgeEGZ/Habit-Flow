<template>
  <nav class="secondary-nav" :aria-label="ariaLabel">
    <RouterLink
      v-for="item in items"
      :key="item.key || item.routeName || item.path || item.label"
      :to="getTarget(item)"
      class="secondary-nav__link"
      :class="{ 'secondary-nav__link--active': item.active }"
      :aria-current="item.active ? 'page' : undefined"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<script setup>
defineProps({
  ariaLabel: {
    type: String,
    default: 'Navegación secundaria',
  },
  items: {
    type: Array,
    required: true,
  },
})

function getTarget(item) {
  if (item.to) {
    return item.to
  }

  if (item.routeName) {
    return { name: item.routeName }
  }

  return item.path
}
</script>

<style scoped>
.secondary-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  width: 100%;
  min-width: 0;
  padding: 0.35rem;
  border: 1px solid var(--app-border);
  border-radius: 0.9rem;
  background: rgba(16, 24, 35, 0.7);
}

.secondary-nav__link {
  display: inline-flex;
  flex: 1 1 auto;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 2.6rem;
  padding: 0.6rem 0.85rem;
  border: 1px solid transparent;
  border-radius: 0.65rem;
  color: var(--app-text-muted);
  font-weight: 600;
  line-height: 1.25;
  text-align: center;
  overflow-wrap: anywhere;
}

.secondary-nav__link:hover,
.secondary-nav__link:focus-visible {
  border-color: var(--app-border-strong);
  color: var(--app-text);
  outline: none;
}

.secondary-nav__link--active {
  border-color: rgba(85, 126, 230, 0.4);
  background: var(--app-accent-soft);
  color: var(--app-text);
}

@media (max-width: 48rem) {
  .secondary-nav__link {
    flex-basis: calc(50% - 0.45rem);
  }
}
</style>
