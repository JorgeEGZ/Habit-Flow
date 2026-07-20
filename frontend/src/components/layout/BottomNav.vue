<template>
  <nav class="bottom-nav" aria-label="Navegación principal móvil">
    <RouterLink
      v-for="item in navigation"
      :key="item.routeName"
      :to="{ name: item.routeName }"
      class="bottom-nav__link"
      :class="{ 'bottom-nav__link--active': isActive(item) }"
    >
      <i :class="item.icon" aria-hidden="true" />
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

import { primaryNavigation as navigation } from '../../utils/navigation'

const route = useRoute()

function isActive(item) {
  return route.meta.section === item.section
}
</script>
