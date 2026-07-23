<template>
  <section class="page-stack savings-page">
    <section v-if="isOverviewRoute" class="savings-overview" aria-labelledby="savings-overview-title">
      <header class="savings-workspace-header">
        <div>
          <p class="savings-workspace-header__eyebrow">Planificación financiera</p>
          <h1 id="savings-overview-title">Ahorros</h1>
          <p>Organiza tus metas y consulta el progreso de cada objetivo.</p>
        </div>
        <div class="savings-header-actions">
          <Button type="button" label="Exportar CSV" icon="pi pi-download" severity="secondary" variant="outlined" :disabled="Boolean(exportingGoalsFormat)" @click="handleGoalsExport('csv')" />
          <Button type="button" label="Exportar Excel" icon="pi pi-file-excel" severity="secondary" variant="outlined" :disabled="Boolean(exportingGoalsFormat)" @click="handleGoalsExport('xlsx')" />
          <Button type="button" label="Nueva meta" icon="pi pi-plus" @click="openCreateGoalDialog" />
        </div>
      </header>

      <p v-if="savingsStore.error" class="dashboard-page__alert">
        {{ savingsStore.error }}
      </p>
      <p v-if="goalsExportError" class="dashboard-page__alert">{{ goalsExportError }}</p>

      <section class="savings-summary" aria-label="Resumen de ahorros">
        <article class="dashboard-stat">
          <span>Metas activas</span>
          <strong>{{ activeGoalsCount }}</strong>
        </article>
        <article class="dashboard-stat">
          <span>Metas completadas</span>
          <strong>{{ completedGoalsCount }}</strong>
        </article>
        <article class="dashboard-stat">
          <span>Contribuciones totales</span>
          <strong>{{ formatCurrencyCop(totalContributed) }}</strong>
        </article>
        <article class="dashboard-stat">
          <span>Progreso promedio</span>
          <strong>{{ formatPercentage(averageCompletion) }}</strong>
        </article>
      </section>

      <Card class="savings-list-card">
        <template #title>Metas guardadas</template>
        <template #content>
          <div v-if="savingsStore.loading && !goals.length" class="savings-skeleton-grid">
            <article v-for="index in 3" :key="index" class="savings-skeleton">
              <span class="savings-skeleton__line savings-skeleton__line--title"></span>
              <span class="savings-skeleton__line"></span>
              <span class="savings-skeleton__line savings-skeleton__line--short"></span>
            </article>
          </div>

          <div v-else-if="!goals.length" class="dashboard-empty">
            No tienes metas de ahorro todavía.
          </div>

          <div v-else class="savings-goal-list savings-goal-list--grid">
            <article
              v-for="goal in goals"
              :key="goal.id"
              class="savings-goal-card"
              role="link"
              tabindex="0"
              @click="openGoalDetail(goal.id)"
              @keydown.enter="openGoalDetail(goal.id)"
              @keydown.space.prevent="openGoalDetail(goal.id)"
            >
              <header class="savings-goal-card__header">
                <div class="savings-goal-card__heading">
                  <h3>{{ goal.name }}</h3>
                  <p v-if="goal.description">{{ goal.description }}</p>
                </div>

                <span class="goal-status-badge" :class="statusToneClass(goalProgress(goal.id).status || goal.status)">
                  {{ goalStatusLabel(goalProgress(goal.id).status || goal.status) }}
                </span>
              </header>

              <div class="savings-goal-card__meta">
                <span>Meta: {{ formatCurrencyCop(goal.target_amount) }}</span>
                <span>Actual: {{ formatCurrencyCop(goalProgress(goal.id).current_amount) }}</span>
                <span>Progreso: {{ formatPercentage(goalProgress(goal.id).completion_percentage) }}</span>
                <span>Fecha objetivo: {{ goal.target_date ? formatDateShort(goal.target_date) : 'Sin fecha' }}</span>
              </div>

              <div class="savings-progress-bar">
                <div class="savings-progress-bar__track">
                  <div
                    class="savings-progress-bar__fill"
                    :style="{ width: `${goalProgress(goal.id).completion_percentage}%` }"
                  ></div>
                </div>
              </div>

              <div class="savings-goal-card__actions">
                <Button
                  type="button"
                  label="Ver detalle"
                  icon="pi pi-arrow-right"
                  severity="secondary"
                  variant="outlined"
                  @click.stop="openGoalDetail(goal.id)"
                />
              </div>
            </article>
          </div>
        </template>
      </Card>
    </section>

    <section v-else class="savings-detail-workspace" aria-labelledby="savings-detail-title">
      <header class="savings-workspace-header savings-workspace-header--detail">
        <div>
          <Button
            type="button"
            label="Volver a metas"
            icon="pi pi-arrow-left"
            severity="secondary"
            variant="text"
            class="app-button app-button--secondary app-button--compact savings-back-button"
            @click="returnToGoals"
          />
          <p class="savings-workspace-header__eyebrow">Detalle de meta</p>
          <h1 id="savings-detail-title">{{ selectedGoal?.name || 'Meta de ahorro' }}</h1>
          <p>{{ selectedGoal?.description || 'Revisa el progreso y las contribuciones registradas.' }}</p>
        </div>
        <div v-if="selectedGoal" class="savings-header-actions">
          <Button type="button" label="Registrar aporte" icon="pi pi-wallet" @click="openContributionDialog" />
          <Button type="button" label="Editar meta" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="startGoalEdit(selectedGoal)" />
          <Button type="button" icon="pi pi-trash" severity="danger" variant="outlined" class="app-button app-button--icon app-button--danger" aria-label="Eliminar meta" :disabled="savingsStore.submitting" @click="handleDeleteGoal(selectedGoal)" />
        </div>
      </header>

      <p v-if="savingsStore.error" class="dashboard-page__alert">
        {{ savingsStore.error }}
      </p>

      <div v-if="detailLoading && !selectedGoal" class="savings-skeleton-grid">
        <article v-for="index in 3" :key="index" class="savings-skeleton">
          <span class="savings-skeleton__line savings-skeleton__line--title"></span>
          <span class="savings-skeleton__line"></span>
        </article>
      </div>

      <div v-else-if="!selectedGoal" class="dashboard-empty">
        No fue posible encontrar esta meta de ahorro.
      </div>

      <template v-else>
        <Card class="savings-detail-card">
          <template #content>
            <div class="savings-detail">
              <div class="savings-detail__summary">
                <div class="dashboard-stat">
                  <span>Contribuido</span>
                  <strong>{{ formatCurrencyCop(selectedProgress?.current_amount ?? 0) }}</strong>
                </div>
                <div class="dashboard-stat">
                  <span>Meta</span>
                  <strong>{{ formatCurrencyCop(selectedProgress?.target_amount ?? selectedGoal.target_amount) }}</strong>
                </div>
                <div class="dashboard-stat">
                  <span>Faltante</span>
                  <strong>{{ formatCurrencyCop(remainingAmount) }}</strong>
                </div>
                <div class="dashboard-stat">
                  <span>Progreso</span>
                  <strong>{{ formatPercentage(selectedProgress?.completion_percentage ?? 0) }}</strong>
                </div>
              </div>

              <div class="savings-detail__goal-meta">
                <span class="goal-status-badge" :class="statusToneClass(selectedProgress?.status || selectedGoal.status)">
                  {{ goalStatusLabel(selectedProgress?.status || selectedGoal.status) }}
                </span>
                <span>Fecha objetivo: {{ selectedGoal.target_date ? formatDateShort(selectedGoal.target_date) : 'Sin fecha' }}</span>
              </div>

              <div class="savings-progress-bar">
                <div class="savings-progress-bar__track">
                  <div
                    class="savings-progress-bar__fill"
                    :style="{ width: `${selectedProgress?.completion_percentage ?? 0}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <Card class="savings-detail-card">
          <template #title>Historial de contribuciones</template>
          <template #content>
            <div class="savings-contribution-toolbar">
              <p>Administra y exporta los aportes registrados para esta meta.</p>
              <div class="savings-contribution-toolbar__actions">
                <Button
                  type="button"
                  label="Exportar CSV"
                  icon="pi pi-download"
                  severity="secondary"
                  variant="outlined"
                  class="app-button app-button--secondary app-button--compact"
                  :loading="exportingContributionsFormat === 'csv'"
                  :disabled="Boolean(exportingContributionsFormat)"
                  @click="handleContributionsExport('csv')"
                />
                <Button
                  type="button"
                  label="Exportar Excel"
                  icon="pi pi-file-excel"
                  severity="secondary"
                  variant="outlined"
                  class="app-button app-button--secondary app-button--compact"
                  :loading="exportingContributionsFormat === 'xlsx'"
                  :disabled="Boolean(exportingContributionsFormat)"
                  @click="handleContributionsExport('xlsx')"
                />
              </div>
            </div>
            <p v-if="contributionsExportError" class="dashboard-page__alert">
              {{ contributionsExportError }}
            </p>
            <p v-if="contributionFeedback" class="savings-contribution-feedback">
              {{ contributionFeedback }}
            </p>
            <div v-if="detailLoading" class="dashboard-panel-state">
              Cargando historial de contribuciones...
            </div>
            <div v-else-if="!selectedContributions.length" class="dashboard-empty">
              Esta meta todavía no tiene contribuciones.
            </div>
            <ul v-else class="savings-contribution-list">
              <li v-for="contribution in selectedContributions" :key="contribution.id" class="savings-contribution">
                <div class="savings-contribution__content">
                  <strong>{{ formatCurrencyCop(contribution.amount) }}</strong>
                  <p>{{ contribution.note || 'Sin nota' }}</p>
                </div>
                <div class="savings-contribution__meta">
                  <small>{{ formatDateShort(contribution.contribution_date) }}</small>
                  <div class="savings-contribution__actions">
                    <Button
                      type="button"
                      icon="pi pi-pencil"
                      severity="secondary"
                      variant="outlined"
                      class="app-button app-button--icon"
                      aria-label="Editar aporte"
                      :disabled="savingsStore.submitting"
                      @click="startContributionEdit(contribution)"
                    />
                    <Button
                      type="button"
                      icon="pi pi-trash"
                      severity="danger"
                      variant="outlined"
                      class="app-button app-button--icon app-button--danger"
                      aria-label="Eliminar aporte"
                      :disabled="savingsStore.submitting"
                      @click="handleDeleteContribution(contribution)"
                    />
                  </div>
                </div>
              </li>
            </ul>
          </template>
        </Card>
      </template>
    </section>

    <Dialog
      v-model:visible="showGoalDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingGoalId ? 'Editar meta' : 'Crear meta'"
    >
      <p class="savings-form-card__subtitle">
        {{ editingGoalId ? 'Actualiza la meta seleccionada.' : 'Crea una nueva meta de ahorro.' }}
      </p>

      <form id="savings-goal-form" class="savings-form" @submit.prevent="handleGoalSubmit">
        <label class="savings-field">
          <span>Nombre</span>
          <InputText v-model="goalForm.name" class="savings-input" autocomplete="off" />
        </label>

        <label class="savings-field">
          <span>Descripción</span>
          <textarea v-model="goalForm.description" class="savings-textarea" rows="4" placeholder="Opcional" />
        </label>

        <div class="savings-inline-grid">
          <label class="savings-field">
            <span>Meta monetaria</span>
            <input v-model.number="goalForm.targetAmount" class="savings-input" type="number" min="1" step="1" />
          </label>
          <label class="savings-field">
            <span>Fecha objetivo</span>
            <input v-model="goalForm.targetDate" class="savings-input" type="date" />
          </label>
        </div>

        <p v-if="goalFormError" class="dashboard-page__alert savings-form-card__alert">
          {{ goalFormError }}
        </p>

      </form>
      <template #footer>
        <Button type="submit" form="savings-goal-form" :label="editingGoalId ? 'Guardar cambios' : 'Crear meta'" icon="pi pi-check" class="app-button app-button--primary" :loading="savingsStore.submitting" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="savingsStore.submitting" @click="clearGoalForm" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showContributionDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingContributionId ? 'Editar aporte' : 'Registrar aporte'"
    >
      <p class="savings-form-card__subtitle">
        {{ selectedGoal ? `Meta activa: ${selectedGoal.name}` : 'Selecciona una meta primero.' }}
      </p>

      <template v-if="selectedGoal">
        <form id="savings-contribution-form" class="savings-form" @submit.prevent="handleContributionSubmit">
          <div class="savings-inline-grid">
            <label class="savings-field">
              <span>Monto</span>
              <input v-model.number="contributionForm.amount" class="savings-input" type="number" min="1" step="1" />
            </label>
            <label class="savings-field">
              <span>Fecha</span>
              <input v-model="contributionForm.contributionDate" class="savings-input" type="date" />
            </label>
          </div>

          <label class="savings-field">
            <span>Nota</span>
            <textarea v-model="contributionForm.note" class="savings-textarea" rows="4" placeholder="Opcional" />
          </label>

          <p v-if="contributionFormError" class="dashboard-page__alert savings-form-card__alert">
            {{ contributionFormError }}
          </p>

        </form>
      </template>
      <template #footer>
        <Button type="submit" form="savings-contribution-form" :label="editingContributionId ? 'Guardar cambios' : 'Guardar aporte'" icon="pi pi-wallet" class="app-button app-button--primary" :loading="savingsStore.submitting" :disabled="!selectedGoal" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="savingsStore.submitting" @click="closeContributionDialog" />
      </template>
    </Dialog>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useRoute, useRouter } from 'vue-router'

import { useSavingsStore } from '../../stores/savings'
import * as savingsService from '../../services/savings'
import { downloadBlob } from '../../utils/download'
import { formatCurrencyCop, formatDateShort, getLocalDateString } from '../../utils/format'

const savingsStore = useSavingsStore()
const route = useRoute()
const router = useRouter()

const goalFormError = ref('')
const contributionFormError = ref('')
const editingGoalId = ref('')
const editingContributionId = ref('')
const detailLoading = ref(false)
const showGoalDialog = ref(false)
const showContributionDialog = ref(false)
const exportingGoalsFormat = ref('')
const goalsExportError = ref('')
const exportingContributionsFormat = ref('')
const contributionsExportError = ref('')
const contributionFeedback = ref('')

const goalForm = reactive({
  name: '',
  description: '',
  targetAmount: null,
  targetDate: '',
})

const contributionForm = reactive({
  amount: null,
  note: '',
  contributionDate: getLocalDateString(),
})

const goals = computed(() => savingsStore.items)
const isOverviewRoute = computed(() => route.name === 'savings-goals')
const routeGoalId = computed(() => String(route.params.goalId || ''))
const selectedGoal = computed(() => goals.value.find((goal) => goal.id === routeGoalId.value) || null)
const selectedProgress = computed(() => savingsStore.progressByGoalId[routeGoalId.value] || null)
const selectedContributions = computed(() => [
  ...(savingsStore.contributionsByGoalId[routeGoalId.value] || []),
].reverse())
const remainingAmount = computed(() => Math.max(0, Number(selectedProgress.value?.target_amount ?? selectedGoal.value?.target_amount ?? 0) - Number(selectedProgress.value?.current_amount ?? 0)))
const activeGoalsCount = computed(() => goals.value.filter((goal) => (goalProgress(goal.id).status || goal.status) === 'active').length)
const completedGoalsCount = computed(() => goals.value.filter((goal) => (goalProgress(goal.id).status || goal.status) === 'completed').length)
const totalContributed = computed(() => goals.value.reduce((total, goal) => total + Number(goalProgress(goal.id).current_amount || 0), 0))
const averageCompletion = computed(() => {
  if (!goals.value.length) {
    return 0
  }

  const sum = goals.value.reduce((total, goal) => total + Number(goalProgress(goal.id).completion_percentage || 0), 0)
  return Math.round(sum / goals.value.length)
})

watch(
  routeGoalId,
  async (goalId) => {
    if (!goals.value.length || goalId) {
      await savingsStore.fetchGoals()
    }

    if (!goalId) {
      return
    }

    detailLoading.value = true
    try {
      await Promise.all([
        savingsStore.fetchContributions(goalId),
        savingsStore.fetchProgress(goalId),
      ])
    } finally {
      detailLoading.value = false
    }
  },
  { immediate: true },
)

function formatPercentage(value) {
  return `${value ?? 0}%`
}

function goalProgress(goalId) {
  return savingsStore.progressByGoalId[goalId] || {
    current_amount: 0,
    target_amount: 0,
    completion_percentage: 0,
    status: 'active',
  }
}

function goalStatusLabel(status) {
  return status === 'completed' ? 'Completada' : 'Activa'
}

function statusToneClass(status) {
  return {
    'goal-status-badge--completed': status === 'completed',
    'goal-status-badge--active': status !== 'completed',
  }
}

function clearGoalForm() {
  editingGoalId.value = ''
  goalForm.name = ''
  goalForm.description = ''
  goalForm.targetAmount = null
  goalForm.targetDate = ''
  goalFormError.value = ''
  showGoalDialog.value = false
}

function openCreateGoalDialog() {
  clearGoalForm()
  showGoalDialog.value = true
}

async function handleGoalsExport(format) {
  goalsExportError.value = ''
  exportingGoalsFormat.value = format
  try {
    const blob = await savingsService.exportGoals(format)
    downloadBlob(blob, `habitflow-savings-goals-${getLocalDateString()}.${format}`)
  } catch {
    goalsExportError.value = 'No fue posible exportar las metas de ahorro.'
  } finally {
    exportingGoalsFormat.value = ''
  }
}

async function handleContributionsExport(format) {
  if (!routeGoalId.value) {
    return
  }

  contributionsExportError.value = ''
  exportingContributionsFormat.value = format
  try {
    const blob = await savingsService.exportGoalContributions(routeGoalId.value, format)
    downloadBlob(
      blob,
      `habitflow-savings-contributions-${routeGoalId.value}-${getLocalDateString()}.${format}`,
    )
  } catch {
    contributionsExportError.value = 'No fue posible exportar los aportes.'
  } finally {
    exportingContributionsFormat.value = ''
  }
}

function startGoalEdit(goal) {
  editingGoalId.value = goal.id
  goalForm.name = goal.name
  goalForm.description = goal.description ?? ''
  goalForm.targetAmount = goal.target_amount
  goalForm.targetDate = goal.target_date ?? ''
  goalFormError.value = ''
  showGoalDialog.value = true
}

function openContributionDialog() {
  resetContributionForm()
  contributionFeedback.value = ''
  if (selectedGoal.value) {
    showContributionDialog.value = true
  }
}

function closeContributionDialog() {
  resetContributionForm()
  showContributionDialog.value = false
}

function startContributionEdit(contribution) {
  contributionFeedback.value = ''
  editingContributionId.value = contribution.id
  contributionForm.amount = contribution.amount
  contributionForm.note = contribution.note ?? ''
  contributionForm.contributionDate = contribution.contribution_date
  contributionFormError.value = ''
  showContributionDialog.value = true
}

function resetContributionForm() {
  editingContributionId.value = ''
  contributionForm.amount = null
  contributionForm.note = ''
  contributionForm.contributionDate = getLocalDateString()
  contributionFormError.value = ''
}

function openGoalDetail(goalId) {
  router.push({ name: 'saving-goal-detail', params: { goalId } })
}

function returnToGoals() {
  router.push({ name: 'savings-goals' })
}

function buildGoalPayload() {
  const name = goalForm.name.trim()
  const description = goalForm.description.trim()
  const targetAmount = Number(goalForm.targetAmount)
  const targetDate = goalForm.targetDate || null

  if (!name) {
    throw new Error('El nombre es obligatorio.')
  }

  if (!Number.isInteger(targetAmount) || targetAmount < 1) {
    throw new Error('Ingresa una meta monetaria válida.')
  }

  return {
    name,
    description: description || null,
    target_amount: targetAmount,
    target_date: targetDate,
  }
}

async function handleGoalSubmit() {
  goalFormError.value = ''

  try {
    const payload = buildGoalPayload()
    await (editingGoalId.value
      ? savingsStore.updateGoal(editingGoalId.value, payload)
      : savingsStore.createGoal(payload))
    clearGoalForm()
  } catch (error) {
    goalFormError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleDeleteGoal(goal) {
  goalFormError.value = ''

  if (!window.confirm(`¿Eliminar la meta "${goal.name}"?`)) {
    return
  }

  try {
    await savingsStore.deleteGoal(goal.id)
    if (editingGoalId.value === goal.id) {
      clearGoalForm()
    }
    if (routeGoalId.value === goal.id) {
      await router.push({ name: 'savings-goals' })
    }
  } catch {
    return
  }
}

async function handleContributionSubmit() {
  contributionFormError.value = ''
  const amount = Number(contributionForm.amount)
  const note = contributionForm.note.trim()

  if (!routeGoalId.value) {
    contributionFormError.value = 'Selecciona una meta primero.'
    return
  }

  if (!Number.isInteger(amount) || amount < 1) {
    contributionFormError.value = 'Ingresa un monto válido.'
    return
  }

  if (!contributionForm.contributionDate) {
    contributionFormError.value = 'Selecciona una fecha para el aporte.'
    return
  }

  if (contributionForm.contributionDate > getLocalDateString()) {
    contributionFormError.value = 'La fecha del aporte no puede estar en el futuro.'
    return
  }

  try {
    const payload = {
      amount,
      note: note || null,
      contribution_date: contributionForm.contributionDate,
    }
    await (editingContributionId.value
      ? savingsStore.updateContribution(routeGoalId.value, editingContributionId.value, payload)
      : savingsStore.addContribution(routeGoalId.value, payload))
    contributionFeedback.value = editingContributionId.value
      ? 'Aporte actualizado.'
      : 'Aporte registrado.'
    resetContributionForm()
    showContributionDialog.value = false
  } catch {
    return
  }
}

async function handleDeleteContribution(contribution) {
  if (!routeGoalId.value || !window.confirm('¿Eliminar este aporte?')) {
    return
  }

  try {
    await savingsStore.deleteContribution(routeGoalId.value, contribution.id)
    contributionFeedback.value = 'Aporte eliminado.'
  } catch {
    return
  }
}
</script>
