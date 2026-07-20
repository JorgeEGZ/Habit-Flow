<template>
  <section class="feature-placeholder">
    <Card>
      <template #title>{{ title }}</template>
      <template #content>
        <p class="feature-placeholder__text">{{ description }}</p>
        <div class="feature-placeholder__panel">
          <i :class="icon" aria-hidden="true" />
          <div>
            <strong>{{ actionTitle }}</strong>
            <p>{{ actionText }}</p>
          </div>
        </div>
      </template>
    </Card>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  actionTitle: {
    type: String,
    required: true,
  },
  actionText: {
    type: String,
    required: true,
  },
  icon: {
    type: String,
    default: 'pi pi-clock',
  },
})
</script>

