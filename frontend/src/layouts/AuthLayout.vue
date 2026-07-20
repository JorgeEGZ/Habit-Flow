<template>
  <main class="auth-layout">
    <section class="auth-layout__panel">
      <div class="auth-layout__brand">
        <div class="auth-layout__logo">H</div>
        <div>
          <p class="auth-layout__eyebrow">HabitFlow</p>
          <h1 class="auth-layout__title">{{ title }}</h1>
        </div>
      </div>
      <p class="auth-layout__subtitle">{{ subtitle }}</p>
      <slot />
    </section>
  </main>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    required: true,
  },
})
</script>

