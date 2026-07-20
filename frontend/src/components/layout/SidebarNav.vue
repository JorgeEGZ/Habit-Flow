<template>
  <nav class="sidebar-nav" aria-label="Navegación principal">
    <div class="sidebar-nav__brand">
      <div class="sidebar-nav__logo">H</div>
      <div>
        <p class="sidebar-nav__eyebrow">HabitFlow</p>
        <h1 class="sidebar-nav__title">Tablero personal</h1>
      </div>
    </div>

    <div class="sidebar-nav__links">
      <RouterLink
        v-for="item in navigation"
        :key="item.routeName"
        :to="{ name: item.routeName }"
        class="sidebar-nav__link"
        :class="{ 'sidebar-nav__link--active': isActive(item) }"
      >
        <i :class="item.icon" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </div>
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
