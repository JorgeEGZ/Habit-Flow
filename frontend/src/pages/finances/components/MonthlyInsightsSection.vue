<template>
  <section class="monthly-insights" aria-labelledby="monthly-insights-title">
    <AppSectionHeader
      title="Lectura del mes"
      description="Observaciones basadas en tus movimientos reales y presupuestos del mes seleccionado."
      heading-id="monthly-insights-title"
      :heading-level="3"
    />

    <AppEmptyState
      v-if="!presentedInsights.length"
      title="No hay observaciones disponibles para este mes."
      compact
    />
    <div v-else class="monthly-insights__grid">
      <article v-for="insight in presentedInsights" :key="insight.key" class="monthly-insights__item">
        <div class="monthly-insights__heading">
          <i :class="insight.icon" aria-hidden="true"></i>
          <div>
            <h4>{{ insight.title }}</h4>
            <AppStatusBadge :label="insight.badgeLabel" :tone="insight.tone" />
          </div>
        </div>
        <p>{{ insight.message }}</p>
        <RouterLink
          v-if="insight.action"
          :to="insight.action.to"
          class="monthly-insights__action"
        >
          {{ insight.action.label }}
        </RouterLink>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

import AppEmptyState from '../../../components/ui/AppEmptyState.vue'
import AppSectionHeader from '../../../components/ui/AppSectionHeader.vue'
import AppStatusBadge from '../../../components/ui/AppStatusBadge.vue'
import { getMonthlyInsightPresentation } from '../reportInsightPresentation'

const props = defineProps({
  insights: { type: Array, default: () => [] },
})

const presentedInsights = computed(() => props.insights.map(getMonthlyInsightPresentation))
</script>

<style scoped>
.monthly-insights { display: grid; gap: 1rem; }
.monthly-insights__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
.monthly-insights__item { display: grid; align-content: start; gap: .75rem; min-width: 0; padding: 1rem; border: 1px solid var(--app-border); border-radius: .8rem; background: var(--app-surface-2); }
.monthly-insights__heading { display: flex; align-items: flex-start; gap: .7rem; }
.monthly-insights__heading > i { margin-top: .16rem; color: var(--app-accent); font-size: 1rem; }
.monthly-insights__heading > div { display: grid; gap: .42rem; min-width: 0; }
.monthly-insights__heading h4 { margin: 0; color: var(--app-text); font-size: .95rem; }
.monthly-insights__item p { margin: 0; color: var(--app-text-muted); line-height: 1.48; }
.monthly-insights__action { width: fit-content; color: var(--app-accent); font-size: .88rem; font-weight: 700; text-decoration: none; }
.monthly-insights__action:hover, .monthly-insights__action:focus-visible { color: var(--app-text); text-decoration: underline; }
@media (max-width: 42rem) { .monthly-insights__grid { grid-template-columns: 1fr; } }
</style>
