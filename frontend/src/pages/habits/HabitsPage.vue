<template>
  <section class="page-stack habits-page">
    <header class="habits-workspace-header">
      <div>
        <p class="habits-workspace-header__eyebrow">Rutinas personales</p>
        <h1>{{ isDetailRoute ? selectedHabit?.title || 'Detalle del hábito' : 'Hábitos' }}</h1>
        <p v-if="isTodayRoute">Registra el progreso de tus hábitos de hoy.</p>
        <p v-else-if="isManageRoute">Administra la configuración y las rachas de tus hábitos.</p>
        <p v-else>{{ selectedHabit?.description || 'Revisa la configuración y las rachas de este hábito.' }}</p>
      </div>
      <Button v-if="isManageRoute" type="button" label="Nuevo hábito" icon="pi pi-plus" @click="openCreateHabitDialog" />
      <div v-else-if="isDetailRoute && selectedHabit" class="habits-header-actions">
        <Button type="button" label="Editar hábito" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="startEdit(selectedHabit)" />
        <Button type="button" icon="pi pi-trash" severity="danger" variant="outlined" aria-label="Eliminar hábito" :disabled="habitsStore.submitting" @click="handleDeleteHabit(selectedHabit)" />
      </div>
    </header>

    <SecondaryNav :items="habitNavigation" aria-label="Secciones de hábitos" />

    <p v-if="formError || habitsStore.error || dashboardStore.error" class="dashboard-page__alert habits-form-card__alert">
      {{ formError || habitsStore.error || dashboardStore.error }}
    </p>

    <section v-if="isTodayRoute" class="habits-daily-workspace" aria-labelledby="habits-today-title">
      <div class="habits-section-heading">
        <div>
          <p class="habits-workspace-header__eyebrow">Seguimiento diario</p>
          <h2 id="habits-today-title">Hoy</h2>
        </div>
        <span class="habits-daily-progress">{{ todayCompletedCount }} de {{ habits.length }} completados</span>
      </div>

      <section class="habits-summary" aria-label="Resumen de hoy">
        <article class="dashboard-stat">
          <span>Completados hoy</span>
          <strong>{{ todayCompletedCount }}</strong>
        </article>
        <article class="dashboard-stat">
          <span>Hábitos para hoy</span>
          <strong>{{ habits.length }}</strong>
        </article>
        <article class="dashboard-stat">
          <span>Racha destacada</span>
          <strong>{{ topCurrentStreak }}</strong>
        </article>
      </section>

      <div v-if="habitsStore.loading && !habits.length" class="habit-skeleton-grid">
        <article v-for="index in 4" :key="index" class="habit-skeleton">
          <span class="habit-skeleton__line habit-skeleton__line--title"></span>
          <span class="habit-skeleton__line"></span>
        </article>
      </div>
      <div v-else-if="!habits.length" class="dashboard-empty">
        No tienes hábitos creados todavía.
      </div>
      <div v-else class="habits-daily-list">
        <article v-for="habit in habits" :key="habit.id" class="habit-card habit-card--daily">
          <header class="habit-card__header">
            <div class="habit-card__heading">
              <h3>{{ habit.title }}</h3>
              <p v-if="habit.description">{{ habit.description }}</p>
            </div>
            <span class="habit-badge">{{ trackingModeLabel(habit.tracking_mode) }}</span>
          </header>

          <div class="habit-card__meta">
            <span v-if="habit.tracking_mode === 'numeric'">Meta: {{ habit.target_value }} {{ habit.unit }}</span>
            <span v-else>Hábito booleano</span>
            <span>Racha actual: {{ habitStreak(habit.id).current }}</span>
            <span class="habit-daily-status" :class="statusToneClass(getTodayStatus(habit).tone)">
              {{ getTodayStatus(habit).label }}
            </span>
          </div>

          <div class="habit-card__log">
            <div v-if="habit.tracking_mode === 'boolean'" class="habit-log-inline">
              <Button
                type="button"
                :label="isLoggedToday(habit) ? 'Actualizar registro de hoy' : 'Marcar hoy'"
                icon="pi pi-check"
                :loading="habitsStore.submitting"
                @click="handleBooleanLog(habit)"
              />
              <Button
                v-if="isLoggedToday(habit)"
                type="button"
                label="Borrar registro de hoy"
                icon="pi pi-times"
                severity="secondary"
                variant="outlined"
                :disabled="habitsStore.submitting"
                @click="handleDeleteLog(habit)"
              />
            </div>

            <form v-else class="habit-log-form" @submit.prevent="handleNumericLog(habit)">
              <div class="habit-inline-grid">
                <label class="habit-field">
                  <span>Valor de hoy</span>
                  <input v-model.number="getLogDraft(habit.id).loggedValue" class="habit-input" type="number" min="0" step="1" />
                </label>
                <label class="habit-field">
                  <span>Nota</span>
                  <InputText v-model="getLogDraft(habit.id).note" class="habit-input" autocomplete="off" placeholder="Opcional" />
                </label>
              </div>
              <div class="habit-log-inline">
                <Button type="submit" :label="isLoggedToday(habit) ? 'Actualizar progreso de hoy' : 'Guardar progreso de hoy'" icon="pi pi-save" :loading="habitsStore.submitting" />
                <Button v-if="isLoggedToday(habit)" type="button" label="Borrar registro de hoy" icon="pi pi-times" severity="secondary" variant="outlined" :disabled="habitsStore.submitting" @click="handleDeleteLog(habit)" />
              </div>
            </form>
          </div>

          <RouterLink class="habit-card__detail-link" :to="{ name: 'habit-detail', params: { habitId: habit.id } }">
            Ver detalle de racha
          </RouterLink>
        </article>
      </div>
    </section>

    <section v-else-if="isManageRoute" class="habits-management-workspace" aria-labelledby="habits-manage-title">
      <div class="habits-section-heading">
        <div>
          <p class="habits-workspace-header__eyebrow">Configuración</p>
          <h2 id="habits-manage-title">Mis hábitos</h2>
        </div>
        <span>{{ habits.length }} hábitos</span>
      </div>

      <div v-if="habitsStore.loading && !habits.length" class="habit-skeleton-grid">
        <article v-for="index in 4" :key="index" class="habit-skeleton">
          <span class="habit-skeleton__line habit-skeleton__line--title"></span>
          <span class="habit-skeleton__line"></span>
        </article>
      </div>
      <div v-else-if="!habits.length" class="dashboard-empty">
        No tienes hábitos creados todavía.
      </div>
      <div v-else class="habit-list habit-list--grid">
        <article v-for="habit in habits" :key="habit.id" class="habit-card">
          <header class="habit-card__header">
            <div class="habit-card__heading">
              <h3>{{ habit.title }}</h3>
              <p v-if="habit.description">{{ habit.description }}</p>
            </div>
            <span class="habit-badge">{{ trackingModeLabel(habit.tracking_mode) }}</span>
          </header>

          <div class="habit-card__meta">
            <span v-if="habit.tracking_mode === 'numeric'">Meta: {{ habit.target_value }} {{ habit.unit }}</span>
            <span v-else>Hábito booleano</span>
            <span>Frecuencia: {{ habit.frequency }}</span>
          </div>

          <div class="habit-card__metrics">
            <div class="habit-card__metric"><span>Racha actual</span><strong>{{ habitStreak(habit.id).current }}</strong></div>
            <div class="habit-card__metric"><span>Racha máxima</span><strong>{{ habitStreak(habit.id).longest }}</strong></div>
          </div>

          <div class="habit-card__header-actions habit-card__management-actions">
            <RouterLink class="habit-card__detail-link" :to="{ name: 'habit-detail', params: { habitId: habit.id } }">Ver detalle</RouterLink>
            <Button type="button" icon="pi pi-pencil" severity="secondary" variant="outlined" aria-label="Editar hábito" @click="startEdit(habit)" />
            <Button type="button" icon="pi pi-trash" severity="danger" variant="outlined" aria-label="Eliminar hábito" :disabled="habitsStore.submitting" @click="handleDeleteHabit(habit)" />
          </div>
        </article>
      </div>
    </section>

    <section v-else class="habit-detail-workspace" aria-labelledby="habit-detail-title">
      <Button type="button" label="Mis hábitos" icon="pi pi-arrow-left" severity="secondary" variant="text" @click="returnToManage" />

      <div v-if="habitsStore.loading && !selectedHabit" class="habit-skeleton-grid">
        <article v-for="index in 3" :key="index" class="habit-skeleton">
          <span class="habit-skeleton__line habit-skeleton__line--title"></span>
          <span class="habit-skeleton__line"></span>
        </article>
      </div>
      <div v-else-if="!selectedHabit" class="dashboard-empty">
        No fue posible encontrar este hábito.
      </div>
      <Card v-else>
        <template #title><span id="habit-detail-title">{{ selectedHabit.title }}</span></template>
        <template #content>
          <div class="habit-detail">
            <p v-if="selectedHabit.description" class="habit-detail__description">{{ selectedHabit.description }}</p>
            <div class="habit-detail__summary">
              <div class="dashboard-stat"><span>Modo</span><strong>{{ trackingModeLabel(selectedHabit.tracking_mode) }}</strong></div>
              <div class="dashboard-stat"><span>Frecuencia</span><strong>{{ selectedHabit.frequency }}</strong></div>
              <div class="dashboard-stat"><span>Racha actual</span><strong>{{ habitStreak(selectedHabit.id).current }}</strong></div>
              <div class="dashboard-stat"><span>Racha máxima</span><strong>{{ habitStreak(selectedHabit.id).longest }}</strong></div>
            </div>

            <div class="habit-detail__configuration">
              <span v-if="selectedHabit.tracking_mode === 'numeric'">Meta: {{ selectedHabit.target_value }} {{ selectedHabit.unit }}</span>
              <span v-else>Este hábito se registra como completado o no completado.</span>
            </div>

            <div class="habits-header-actions">
              <Button type="button" label="Editar hábito" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="startEdit(selectedHabit)" />
              <Button type="button" icon="pi pi-trash" label="Eliminar hábito" severity="danger" variant="outlined" :disabled="habitsStore.submitting" @click="handleDeleteHabit(selectedHabit)" />
            </div>
          </div>
        </template>
      </Card>
    </section>

    <Dialog v-model:visible="showHabitDialog" modal dismissableMask class="app-dialog" :header="editingHabitId ? 'Editar hábito' : 'Crear hábito'">
      <p class="habits-form-card__subtitle">
        {{ editingHabitId ? 'Actualiza los datos del hábito seleccionado.' : 'Crea un nuevo hábito diario.' }}
      </p>

      <form class="habits-form" @submit.prevent="handleSubmit">
        <label class="habit-field"><span>Título</span><InputText v-model="form.title" class="habit-input" autocomplete="off" /></label>
        <label class="habit-field"><span>Descripción</span><textarea v-model="form.description" class="habit-textarea" rows="4" placeholder="Opcional" /></label>

        <div class="habit-field">
          <span>Modo de seguimiento</span>
          <div v-if="editingHabitId" class="habit-mode-lock"><span class="habit-badge">{{ trackingModeLabel(form.trackingMode) }}</span><small>El modo no se puede cambiar después de crear el hábito.</small></div>
          <div v-else class="habit-toggle-group">
            <button type="button" class="habit-toggle" :class="{ 'habit-toggle--active': form.trackingMode === 'boolean' }" @click="setTrackingMode('boolean')">Booleano</button>
            <button type="button" class="habit-toggle" :class="{ 'habit-toggle--active': form.trackingMode === 'numeric' }" @click="setTrackingMode('numeric')">Numérico</button>
          </div>
        </div>

        <div v-if="form.trackingMode === 'numeric'" class="habit-inline-grid">
          <label class="habit-field"><span>Meta</span><input v-model.number="form.targetValue" class="habit-input" type="number" min="1" step="1" /></label>
          <label class="habit-field"><span>Unidad</span><InputText v-model="form.unit" class="habit-input" autocomplete="off" /></label>
        </div>

        <p v-if="formError" class="dashboard-page__alert habits-form-card__alert">{{ formError }}</p>
        <div class="habit-form__actions">
          <Button type="submit" :label="editingHabitId ? 'Guardar cambios' : 'Crear hábito'" icon="pi pi-check" :loading="habitsStore.submitting" />
          <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" :disabled="habitsStore.submitting" @click="cancelEdit" />
        </div>
      </form>
    </Dialog>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useRoute, useRouter } from 'vue-router'

import SecondaryNav from '../../components/common/SecondaryNav.vue'
import { useDashboardStore } from '../../stores/dashboard'
import { useHabitsStore } from '../../stores/habits'
import { getLocalDateString } from '../../utils/format'

const habitsStore = useHabitsStore()
const dashboardStore = useDashboardStore()
const route = useRoute()
const router = useRouter()

const formError = ref('')
const editingHabitId = ref('')
const showHabitDialog = ref(false)
const form = reactive({ title: '', description: '', trackingMode: 'boolean', targetValue: null, unit: '' })
const logDrafts = reactive({})
const today = getLocalDateString()

const habits = computed(() => habitsStore.items)
const isTodayRoute = computed(() => route.name === 'habits-today')
const isManageRoute = computed(() => route.name === 'habits-manage')
const isDetailRoute = computed(() => route.name === 'habit-detail')
const routeHabitId = computed(() => String(route.params.habitId || ''))
const selectedHabit = computed(() => habits.value.find((habit) => habit.id === routeHabitId.value) || null)
const habitNavigation = computed(() => [
  { label: 'Hoy', routeName: 'habits-today', active: isTodayRoute.value },
  { label: 'Mis hábitos', routeName: 'habits-manage', active: isManageRoute.value || isDetailRoute.value },
])
const todayCompletedCount = computed(() => dashboardStore.habits?.completed_today ?? Object.values(habitsStore.todayLogs).filter((log) => log?.completed).length)
const topCurrentStreak = computed(() => Math.max(0, ...habits.value.map((habit) => habitStreak(habit.id).current)))

watch(
  routeHabitId,
  async () => {
    if (!habits.value.length) {
      await habitsStore.fetchHabits()
    }
  },
  { immediate: true },
)

watch(
  isTodayRoute,
  async (isToday) => {
    if (isToday && !dashboardStore.habits) {
      await dashboardStore.fetchHabits()
    }
  },
  { immediate: true },
)

function trackingModeLabel(mode) {
  return mode === 'numeric' ? 'Numérico' : 'Booleano'
}

function statusToneClass(tone) {
  return {
    'habit-status--success': tone === 'success',
    'habit-status--warning': tone === 'warning',
    'habit-status--neutral': tone === 'neutral',
  }
}

function habitStreak(habitId) {
  return habitsStore.streaks[habitId] ?? { current: 0, longest: 0 }
}

function getTodayStatus(habit) {
  const log = habitsStore.todayLogs[habit.id]
  if (!log) {
    return { label: 'Sin registro en esta sesión', tone: 'neutral' }
  }
  if (log.completed) {
    return { label: 'Completado hoy', tone: 'success' }
  }
  return { label: 'Registrado hoy', tone: 'warning' }
}

function isLoggedToday(habit) {
  return Boolean(habitsStore.todayLogs[habit.id])
}

function getLogDraft(habitId) {
  if (!logDrafts[habitId]) {
    logDrafts[habitId] = { loggedValue: null, note: '' }
  }
  return logDrafts[habitId]
}

function resetForm() {
  editingHabitId.value = ''
  form.title = ''
  form.description = ''
  form.trackingMode = 'boolean'
  form.targetValue = null
  form.unit = ''
  formError.value = ''
  showHabitDialog.value = false
}

function openCreateHabitDialog() {
  resetForm()
  showHabitDialog.value = true
}

function setTrackingMode(mode) {
  if (!editingHabitId.value) {
    form.trackingMode = mode
  }
}

function startEdit(habit) {
  editingHabitId.value = habit.id
  form.title = habit.title
  form.description = habit.description ?? ''
  form.trackingMode = habit.tracking_mode
  form.targetValue = habit.target_value ?? null
  form.unit = habit.unit ?? ''
  formError.value = ''
  showHabitDialog.value = true
}

function cancelEdit() {
  resetForm()
}

function buildHabitPayload() {
  const title = form.title.trim()
  const description = form.description.trim()
  if (!title) {
    throw new Error('El título es obligatorio.')
  }
  if (form.trackingMode === 'numeric') {
    const targetValue = Number(form.targetValue)
    const unit = form.unit.trim()
    if (!Number.isInteger(targetValue) || targetValue < 1 || !unit) {
      throw new Error('Completa la meta y la unidad para un hábito numérico.')
    }
    return { title, description: description || null, target_value: targetValue, unit, frequency: 'daily' }
  }
  return { title, description: description || null, frequency: 'daily' }
}

async function handleSubmit() {
  formError.value = ''
  try {
    const payload = buildHabitPayload()
    if (editingHabitId.value) {
      const updatePayload = { title: payload.title, description: payload.description }
      if (form.trackingMode === 'numeric') {
        updatePayload.target_value = payload.target_value
        updatePayload.unit = payload.unit
      }
      await habitsStore.updateHabit(editingHabitId.value, updatePayload)
    } else {
      await habitsStore.createHabit({ ...payload, tracking_mode: form.trackingMode })
    }
    resetForm()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleDeleteHabit(habit) {
  formError.value = ''
  if (!window.confirm(`¿Eliminar el hábito "${habit.title}"?`)) {
    return
  }
  try {
    await habitsStore.deleteHabit(habit.id)
    if (editingHabitId.value === habit.id) {
      resetForm()
    }
    if (routeHabitId.value === habit.id) {
      await router.push({ name: 'habits-manage' })
    }
  } catch {
    return
  }
}

async function handleBooleanLog(habit) {
  formError.value = ''
  try {
    await habitsStore.logHabit(habit.id, { logged_on: today })
    await refreshTodaySummary()
  } catch {
    return
  }
}

async function handleNumericLog(habit) {
  formError.value = ''
  const draft = getLogDraft(habit.id)
  if (draft.loggedValue === '' || draft.loggedValue === null || draft.loggedValue === undefined) {
    formError.value = 'Ingresa un valor válido para el progreso de hoy.'
    return
  }
  const loggedValue = Number(draft.loggedValue)
  const note = draft.note?.trim()
  if (!Number.isInteger(loggedValue) || loggedValue < 0) {
    formError.value = 'Ingresa un valor válido para el progreso de hoy.'
    return
  }
  try {
    await habitsStore.logHabit(habit.id, { logged_on: today, logged_value: loggedValue, note: note || null })
    await refreshTodaySummary()
    draft.loggedValue = null
    draft.note = ''
  } catch {
    return
  }
}

async function handleDeleteLog(habit) {
  formError.value = ''
  try {
    await habitsStore.deleteHabitLog(habit.id, today)
    await refreshTodaySummary()
  } catch {
    return
  }
}

async function refreshTodaySummary() {
  try {
    await dashboardStore.fetchHabits()
  } catch {
    return
  }
}

function returnToManage() {
  router.push({ name: 'habits-manage' })
}
</script>
