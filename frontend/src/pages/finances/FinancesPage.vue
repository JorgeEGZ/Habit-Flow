<template>
  <section class="page-stack finances-page">
    <section class="finance-workspace" aria-labelledby="finances-workspace-title">
      <header class="finance-workspace__header">
        <div>
          <p class="finance-workspace__eyebrow">Panorama financiero</p>
          <h1 id="finances-workspace-title">Finanzas</h1>
          <p>Controla tus movimientos, cuentas y reglas desde un solo espacio.</p>
        </div>
      </header>

      <p v-if="financesStore.error" class="dashboard-page__alert finances-page__alert">
        {{ financesStore.error }}
      </p>

      <SecondaryNav :items="financeNavigation" aria-label="Secciones de finanzas" />

      <section v-if="isMovementsWorkspace" class="finance-kpis" aria-label="Resumen financiero mensual">
        <article class="finance-kpi finance-kpi--balance">
          <span>Balance mensual</span>
          <strong :class="transactionAmountClass(financeSummary.monthly_balance >= 0 ? 'income' : 'expense')">
            {{ formatCurrencyCop(financeSummary.monthly_balance) }}
          </strong>
          <small>Ingresos menos gastos del mes</small>
        </article>
        <article class="finance-kpi">
          <span>Ingresos del mes</span>
          <strong class="transaction-amount--income">{{ formatCurrencyCop(financeSummary.monthly_income) }}</strong>
          <small>Movimientos registrados este mes</small>
        </article>
        <article class="finance-kpi">
          <span>Gastos del mes</span>
          <strong class="transaction-amount--expense">{{ formatCurrencyCop(financeSummary.monthly_expenses) }}</strong>
          <small>Movimientos registrados este mes</small>
        </article>
        <article class="finance-kpi">
          <span>Balance total de cuentas</span>
          <strong>{{ formatCurrencyCop(totalAccountBalance) }}</strong>
          <small>{{ accounts.length }} cuentas registradas</small>
        </article>
      </section>

      <section
        v-if="isMovementsWorkspace"
        class="finance-tab-panel"
      >
        <header class="finance-panel-header">
          <div>
            <h2>Movimientos</h2>
            <p>Revisa y administra los registros financieros más recientes.</p>
          </div>
          <Button type="button" label="Nuevo movimiento" icon="pi pi-plus" @click="openCreateTransactionDialog" />
        </header>

        <div class="finance-toolbar">
          <div class="finance-toolbar__filters">
            <label class="transaction-field">
              <span>Cuenta</span>
              <select v-model="transactionFilters.accountId" class="finance-input">
                <option value="all">Todas las cuentas</option>
                <option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.name }}</option>
              </select>
            </label>
            <label class="transaction-field">
              <span>Categoría</span>
              <select v-model="transactionFilters.categoryId" class="finance-input">
                <option value="all">Todas las categorías</option>
                <option v-for="category in categories" :key="category.id" :value="category.id">
                  {{ category.name }} - {{ categoryTypeLabel(category.type) }}
                </option>
              </select>
            </label>
            <label class="transaction-field">
              <span>Tipo</span>
              <select v-model="transactionFilters.type" class="finance-input">
                <option value="all">Todos los tipos</option>
                <option v-for="type in transactionTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
              </select>
            </label>
            <label class="transaction-field">
              <span>Ordenar por fecha</span>
              <select v-model="transactionFilters.sortOrder" class="finance-input">
                <option v-for="option in sortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>
          </div>
          <div class="finance-toolbar__actions">
            <span>{{ visibleTransactions.length }} de {{ transactions.length }} movimientos</span>
            <Button type="button" label="Limpiar filtros" icon="pi pi-filter-slash" severity="secondary" variant="outlined" @click="resetTransactionFilters" />
          </div>
        </div>

        <div v-if="transactionsLoading && !transactions.length" class="finance-skeleton-grid">
          <article v-for="index in 4" :key="index" class="finance-skeleton">
            <span class="finance-skeleton__line finance-skeleton__line--title"></span>
            <span class="finance-skeleton__line"></span>
          </article>
        </div>
        <div v-else-if="!transactions.length" class="dashboard-empty">No tienes movimientos registrados todavía.</div>
        <div v-else-if="!visibleTransactions.length" class="dashboard-empty">No hay movimientos que coincidan con los filtros actuales.</div>
        <div v-else class="finance-data-table finance-data-table--transactions">
          <div class="finance-data-table__head">
            <span>Movimiento</span><span>Cuenta</span><span>Categoría</span><span>Fecha</span><span>Monto</span><span>Acciones</span>
          </div>
          <article v-for="transaction in visibleTransactions" :key="transaction.id" class="finance-data-row">
            <div class="finance-data-cell finance-data-cell--primary"><span>Movimiento</span><strong>{{ transaction.description || categoryLabel(transaction.category_id) }}</strong></div>
            <div class="finance-data-cell"><span>Cuenta</span><p>{{ accountLabel(transaction.account_id) }}</p></div>
            <div class="finance-data-cell"><span>Categoría</span><p>{{ categoryLabel(transaction.category_id) }}</p></div>
            <div class="finance-data-cell"><span>Fecha</span><p>{{ formatDateShort(transaction.transaction_date) }}</p></div>
            <div class="finance-data-cell finance-data-cell--amount"><span>Monto</span><strong :class="transactionAmountClass(transaction.type)">{{ formatTransactionAmount(transaction) }}</strong></div>
            <div class="finance-data-row__actions">
              <Button type="button" icon="pi pi-pencil" severity="secondary" variant="outlined" class="app-button app-button--icon app-button--icon-secondary" aria-label="Editar movimiento" @click="startTransactionEdit(transaction)" />
              <Button type="button" icon="pi pi-trash" severity="danger" variant="outlined" class="app-button app-button--icon app-button--danger" aria-label="Eliminar movimiento" :disabled="financesStore.submitting" @click="handleDeleteTransaction(transaction)" />
            </div>
          </article>
        </div>
      </section>

      <section
        v-else-if="isRecurringWorkspace"
        class="finance-tab-panel"
      >
        <header class="finance-panel-header">
          <div>
            <h2>Reglas recurrentes</h2>
            <p>Estas reglas no generan movimientos reales automáticamente todavía.</p>
          </div>
          <Button type="button" label="Nueva regla" icon="pi pi-plus" @click="openCreateRecurringDialog" />
        </header>

        <div v-if="recurringLoading && !recurringRules.length" class="finance-skeleton-grid">
          <article v-for="index in 3" :key="index" class="finance-skeleton"><span class="finance-skeleton__line finance-skeleton__line--title"></span><span class="finance-skeleton__line"></span></article>
        </div>
        <div v-else-if="!recurringRules.length" class="dashboard-empty">No tienes reglas recurrentes registradas todavía.</div>
        <div v-else class="finance-data-table finance-data-table--recurring">
          <div class="finance-data-table__head">
            <span>Regla</span><span>Cuenta</span><span>Categoría</span><span>Frecuencia</span><span>Estado</span><span>Monto</span><span>Acciones</span>
          </div>
          <article v-for="rule in visibleRecurringRules" :key="rule.id" class="finance-data-row">
            <div class="finance-data-cell finance-data-cell--primary"><span>Regla</span><strong>{{ rule.description || categoryLabel(rule.category_id) }}</strong><p>{{ recurringDateRange(rule) }}</p></div>
            <div class="finance-data-cell"><span>Cuenta</span><p>{{ accountLabel(rule.account_id) }}</p></div>
            <div class="finance-data-cell"><span>Categoría</span><p>{{ categoryLabel(rule.category_id) }}</p></div>
            <div class="finance-data-cell"><span>Frecuencia</span><p>{{ frequencyLabel(rule.frequency) }}</p></div>
            <div class="finance-data-cell"><span>Estado</span><span class="recurring-status-pill" :class="recurringStatusClass(rule.is_active)">{{ rule.is_active ? 'Activa' : 'Pausada' }}</span></div>
            <div class="finance-data-cell finance-data-cell--amount"><span>Monto</span><strong :class="transactionAmountClass(rule.type)">{{ formatTransactionAmount(rule) }}</strong></div>
            <div class="finance-data-row__actions">
              <Button type="button" :label="rule.is_active ? 'Pausar' : 'Reanudar'" :icon="rule.is_active ? 'pi pi-pause' : 'pi pi-play'" severity="secondary" variant="outlined" class="app-button app-button--secondary app-button--compact finance-recurring-toggle" :aria-label="rule.is_active ? 'Pausar regla recurrente' : 'Reanudar regla recurrente'" :disabled="financesStore.submitting" @click="toggleRecurringActive(rule)" />
              <Button type="button" icon="pi pi-pencil" severity="secondary" variant="outlined" class="app-button app-button--icon app-button--icon-secondary" aria-label="Editar regla recurrente" @click="startRecurringEdit(rule)" />
              <Button type="button" icon="pi pi-trash" severity="danger" variant="outlined" class="app-button app-button--icon app-button--danger" aria-label="Eliminar regla recurrente" :disabled="financesStore.submitting" @click="handleDeleteRecurring(rule)" />
            </div>
          </article>
        </div>
      </section>

      <section
        v-else
        class="finance-tab-panel"
      >
        <div class="finance-configuration finance-configuration--single">
          <section v-if="isAccountsWorkspace" class="finance-configuration__accounts">
            <header class="finance-panel-header">
              <div><h2>Cuentas</h2><p>Consulta el saldo actual de cada cuenta.</p></div>
              <Button type="button" label="Nueva cuenta" icon="pi pi-plus" severity="secondary" variant="outlined" @click="openCreateAccountDialog" />
            </header>
            <div v-if="loadingFinanceData && !accounts.length" class="finance-skeleton-grid"><article v-for="index in 3" :key="index" class="finance-skeleton"><span class="finance-skeleton__line finance-skeleton__line--title"></span><span class="finance-skeleton__line"></span></article></div>
            <div v-else-if="!accounts.length" class="dashboard-empty">No tienes cuentas registradas todavía.</div>
            <div v-else class="finance-compact-list">
              <article v-for="account in accounts" :key="account.id" class="finance-compact-row">
                <div><strong>{{ account.name }}</strong><span>{{ accountTypeLabel(account.type) }} · Saldo inicial {{ formatCurrencyCop(account.initial_balance) }}</span></div>
                <strong class="finance-compact-row__amount">{{ formatCurrencyCop(account.current_balance) }}</strong>
                <div class="finance-compact-row__actions">
                  <Button type="button" icon="pi pi-pencil" severity="secondary" variant="text" class="app-button app-button--icon app-button--icon-secondary" aria-label="Editar cuenta" @click="startAccountEdit(account)" />
                  <Button type="button" icon="pi pi-trash" severity="danger" variant="text" class="app-button app-button--icon app-button--danger" aria-label="Eliminar cuenta" :disabled="financesStore.submitting" @click="handleDeleteAccount(account)" />
                </div>
              </article>
            </div>
          </section>
          <section v-else class="finance-configuration__categories">
            <header class="finance-panel-header">
              <div><h2>Categorías</h2><p>Organiza ingresos y gastos.</p></div>
              <Button type="button" label="Nueva categoría" icon="pi pi-plus" severity="secondary" variant="outlined" @click="openCreateCategoryDialog" />
            </header>
            <div v-if="loadingFinanceData && !categories.length" class="finance-skeleton-grid"><article v-for="index in 3" :key="index" class="finance-skeleton"><span class="finance-skeleton__line finance-skeleton__line--title"></span></article></div>
            <div v-else-if="!categories.length" class="dashboard-empty">No tienes categorías registradas todavía.</div>
            <div v-else class="finance-category-groups">
              <section v-for="group in categoryGroups" :key="group.id" class="finance-category-group">
                <h3>{{ group.label }}</h3>
                <div class="finance-compact-list">
                  <article v-for="category in group.items" :key="category.id" class="finance-compact-row">
                    <div><strong>{{ category.name }}</strong><span>{{ categoryTypeLabel(category.type) }}</span></div>
                    <div class="finance-compact-row__actions">
                      <Button type="button" icon="pi pi-pencil" severity="secondary" variant="text" class="app-button app-button--icon app-button--icon-secondary" aria-label="Editar categoría" @click="startCategoryEdit(category)" />
                      <Button type="button" icon="pi pi-trash" severity="danger" variant="text" class="app-button app-button--icon app-button--danger" aria-label="Eliminar categoría" :disabled="financesStore.submitting" @click="handleDeleteCategory(category)" />
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </section>
        </div>
      </section>
    </section>
    <Dialog
      v-model:visible="showTransactionDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingTransactionId ? 'Editar movimiento' : 'Crear movimiento'"
    >
      <p class="transaction-panel__subtitle">
        {{ editingTransactionId ? 'Actualiza el movimiento seleccionado.' : 'Registra un nuevo movimiento.' }}
      </p>

      <p v-if="transactionFormError" class="dashboard-page__alert transaction-panel__alert">
        {{ transactionFormError }}
      </p>

      <form id="transaction-editor-form" class="transaction-form" @submit.prevent="handleTransactionSubmit">
        <div class="transaction-inline-grid">
          <label class="transaction-field">
            <span>Fecha</span>
            <input v-model="transactionForm.transactionDate" class="finance-input" type="date" required />
          </label>

          <label class="transaction-field">
            <span>Monto</span>
            <input
              v-model.number="transactionForm.amount"
              class="finance-input"
              type="number"
              min="1"
              step="1"
              inputmode="numeric"
            />
          </label>
        </div>

        <label class="transaction-field">
          <span>Cuenta</span>
          <select v-model="transactionForm.accountId" class="finance-input">
            <option value="">Selecciona una cuenta</option>
            <option v-for="account in accounts" :key="account.id" :value="account.id">
              {{ account.name }} - {{ accountTypeLabel(account.type) }}
            </option>
          </select>
        </label>

        <div class="transaction-field">
          <span>Tipo</span>
          <div class="finance-toggle-group transaction-type-group">
            <button
              v-for="type in transactionTypes"
              :key="type.value"
              type="button"
              class="finance-toggle"
              :class="{ 'finance-toggle--active': transactionForm.type === type.value }"
              @click="transactionForm.type = type.value"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

        <label class="transaction-field">
          <span>Categoría</span>
          <select v-model="transactionForm.categoryId" class="finance-input">
            <option value="">Selecciona una categoría</option>
            <option v-for="category in transactionCategoryOptions" :key="category.id" :value="category.id">
              {{ category.name }}
            </option>
          </select>
        </label>

        <label class="transaction-field">
          <span>Descripción</span>
          <textarea
            v-model="transactionForm.description"
            class="finance-input finance-textarea"
            rows="3"
            placeholder="Opcional"
          />
        </label>

        <p class="transaction-panel__hint">
          La categoría seleccionada debe coincidir con el tipo del movimiento.
        </p>

      </form>
      <template #footer>
        <Button type="submit" form="transaction-editor-form" :label="editingTransactionId ? 'Guardar cambios' : 'Crear movimiento'" icon="pi pi-check" class="app-button app-button--primary" :loading="financesStore.submitting" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="financesStore.submitting" @click="resetTransactionForm" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showRecurringDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingRecurringId ? 'Editar regla recurrente' : 'Crear regla recurrente'"
    >
      <p class="recurring-panel__subtitle">
        Administra reglas programadas. No se generan transacciones reales desde esta vista.
      </p>

      <p v-if="recurringFormError" class="dashboard-page__alert recurring-panel__alert">
        {{ recurringFormError }}
      </p>

      <form id="recurring-editor-form" class="recurring-form" @submit.prevent="handleRecurringSubmit">
        <div class="recurring-inline-grid">
          <label class="recurring-field">
            <span>Fecha de inicio</span>
            <input v-model="recurringForm.startDate" class="finance-input" type="date" required />
          </label>

          <label class="recurring-field">
            <span>Fecha de fin</span>
            <input v-model="recurringForm.endDate" class="finance-input" type="date" />
          </label>
        </div>

        <div class="recurring-inline-grid">
          <label class="recurring-field">
            <span>Monto</span>
            <input
              v-model.number="recurringForm.amount"
              class="finance-input"
              type="number"
              min="1"
              step="1"
              inputmode="numeric"
            />
          </label>

          <label class="recurring-field">
            <span>Frecuencia</span>
            <select v-model="recurringForm.frequency" class="finance-input">
              <option v-for="option in frequencyOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>

        <label class="recurring-field">
          <span>Cuenta</span>
          <select v-model="recurringForm.accountId" class="finance-input">
            <option value="">Selecciona una cuenta</option>
            <option v-for="account in accounts" :key="account.id" :value="account.id">
              {{ account.name }} - {{ accountTypeLabel(account.type) }}
            </option>
          </select>
        </label>

        <div class="recurring-field">
          <span>Tipo</span>
          <div class="finance-toggle-group recurring-type-group">
            <button
              v-for="type in recurringTypes"
              :key="type.value"
              type="button"
              class="finance-toggle"
              :class="{ 'finance-toggle--active': recurringForm.type === type.value }"
              @click="recurringForm.type = type.value"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

        <label class="recurring-field">
          <span>Categoría</span>
          <select v-model="recurringForm.categoryId" class="finance-input">
            <option value="">Selecciona una categoría</option>
            <option v-for="category in recurringCategoryOptions" :key="category.id" :value="category.id">
              {{ category.name }}
            </option>
          </select>
        </label>

        <label class="recurring-field">
          <span>Descripción</span>
          <textarea
            v-model="recurringForm.description"
            class="finance-input finance-textarea"
            rows="3"
            placeholder="Opcional"
          />
        </label>

        <label class="recurring-switch">
          <input v-model="recurringForm.isActive" type="checkbox" />
          <span>Regla activa</span>
        </label>

        <p class="recurring-panel__hint">
          La categoría debe coincidir con el tipo de la regla y el monto debe ser mayor que cero.
        </p>

      </form>
      <template #footer>
        <Button type="submit" form="recurring-editor-form" :label="editingRecurringId ? 'Guardar cambios' : 'Crear regla'" icon="pi pi-check" class="app-button app-button--primary" :loading="financesStore.submitting" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="financesStore.submitting" @click="resetRecurringForm" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showAccountDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingAccountId ? 'Editar cuenta' : 'Crear cuenta'"
    >
      <p class="finance-panel__subtitle">
        {{ editingAccountId ? 'Actualiza la cuenta seleccionada.' : 'Crea una nueva cuenta.' }}
      </p>

      <p v-if="accountFormError" class="dashboard-page__alert finance-panel__alert">
        {{ accountFormError }}
      </p>

      <form id="account-editor-form" class="finance-form" @submit.prevent="handleAccountSubmit">
        <label class="finance-field">
          <span>Nombre</span>
          <InputText v-model="accountForm.name" class="finance-input" autocomplete="off" />
        </label>

        <div class="finance-field">
          <span>Tipo</span>
          <div class="finance-toggle-group">
            <button
              v-for="type in accountTypes"
              :key="type.value"
              type="button"
              class="finance-toggle"
              :class="{ 'finance-toggle--active': accountForm.type === type.value }"
              @click="accountForm.type = type.value"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

        <label class="finance-field">
          <span>Saldo inicial</span>
          <input
            v-model.number="accountForm.initialBalance"
            class="finance-input"
            type="number"
            min="0"
            step="1"
            inputmode="numeric"
          />
        </label>

        <p class="finance-panel__hint">
          El saldo actual se calcula de forma automática y no se edita aquí.
        </p>

      </form>
      <template #footer>
        <Button type="submit" form="account-editor-form" :label="editingAccountId ? 'Guardar cambios' : 'Crear cuenta'" icon="pi pi-check" class="app-button app-button--primary" :loading="financesStore.submitting" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="financesStore.submitting" @click="resetAccountForm" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showCategoryDialog"
      modal
      dismissableMask
      class="app-dialog"
      :header="editingCategoryId ? 'Editar categoría' : 'Crear categoría'"
    >
      <p class="finance-panel__subtitle">
        {{ editingCategoryId ? 'Actualiza la categoría seleccionada.' : 'Crea una nueva categoría.' }}
      </p>

      <p v-if="categoryFormError" class="dashboard-page__alert finance-panel__alert">
        {{ categoryFormError }}
      </p>

      <form id="category-editor-form" class="finance-form" @submit.prevent="handleCategorySubmit">
        <label class="finance-field">
          <span>Nombre</span>
          <InputText v-model="categoryForm.name" class="finance-input" autocomplete="off" />
        </label>

        <div class="finance-field">
          <span>Tipo</span>
          <div class="finance-toggle-group">
            <button
              v-for="type in categoryTypes"
              :key="type.value"
              type="button"
              class="finance-toggle"
              :class="{ 'finance-toggle--active': categoryForm.type === type.value }"
              @click="categoryForm.type = type.value"
            >
              {{ type.label }}
            </button>
          </div>
        </div>

      </form>
      <template #footer>
        <Button type="submit" form="category-editor-form" :label="editingCategoryId ? 'Guardar cambios' : 'Crear categoría'" icon="pi pi-check" class="app-button app-button--primary" :loading="financesStore.submitting" />
        <Button type="button" label="Cancelar" icon="pi pi-times" severity="secondary" variant="outlined" class="app-button app-button--secondary" :disabled="financesStore.submitting" @click="resetCategoryForm" />
      </template>
    </Dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useRoute } from 'vue-router'

import SecondaryNav from '../../components/common/SecondaryNav.vue'
import { useDashboardStore } from '../../stores/dashboard'
import { useFinancesStore } from '../../stores/finances'
import { formatCurrencyCop, formatDateShort, getLocalDateString } from '../../utils/format'

const financesStore = useFinancesStore()
const dashboardStore = useDashboardStore()
const route = useRoute()

const loadingFinanceData = ref(false)
const editingAccountId = ref('')
const editingCategoryId = ref('')
const editingTransactionId = ref('')
const editingRecurringId = ref('')
const showAccountDialog = ref(false)
const showCategoryDialog = ref(false)
const showTransactionDialog = ref(false)
const showRecurringDialog = ref(false)
const accountFormError = ref('')
const categoryFormError = ref('')
const transactionFormError = ref('')
const recurringFormError = ref('')

const accountForm = reactive({
  name: '',
  type: 'checking',
  initialBalance: 0,
})

const categoryForm = reactive({
  name: '',
  type: 'income',
})

const transactionForm = reactive({
  accountId: '',
  categoryId: '',
  type: 'expense',
  amount: 1,
  description: '',
  transactionDate: getLocalDateString(),
})

const recurringForm = reactive({
  accountId: '',
  categoryId: '',
  type: 'expense',
  amount: 1,
  description: '',
  frequency: 'monthly',
  startDate: getLocalDateString(),
  endDate: '',
  isActive: true,
})

const transactionFilters = reactive({
  accountId: 'all',
  categoryId: 'all',
  type: 'all',
  sortOrder: 'desc',
})

const accountTypes = [
  { value: 'checking', label: 'Corriente' },
  { value: 'savings', label: 'Ahorros' },
  { value: 'cash', label: 'Efectivo' },
  { value: 'credit', label: 'Crédito' },
]

const categoryTypes = [
  { value: 'income', label: 'Ingreso' },
  { value: 'expense', label: 'Gasto' },
]

const transactionTypes = [
  { value: 'income', label: 'Ingreso' },
  { value: 'expense', label: 'Gasto' },
]

const recurringTypes = [
  { value: 'income', label: 'Ingreso' },
  { value: 'expense', label: 'Gasto' },
]

const frequencyOptions = [
  { value: 'daily', label: 'Diaria' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'monthly', label: 'Mensual' },
]

const sortOptions = [
  { value: 'desc', label: 'Más recientes primero' },
  { value: 'asc', label: 'Más antiguos primero' },
]

const financeNavigation = computed(() => [
  { label: 'Movimientos', routeName: 'finances-movements', active: route.name === 'finances-movements' },
  { label: 'Recurrentes', routeName: 'finances-recurring', active: route.name === 'finances-recurring' },
  { label: 'Cuentas', routeName: 'finances-accounts', active: route.name === 'finances-accounts' },
  { label: 'Categorías', routeName: 'finances-categories', active: route.name === 'finances-categories' },
])

const isMovementsWorkspace = computed(() => route.name === 'finances-movements')
const isRecurringWorkspace = computed(() => route.name === 'finances-recurring')
const isAccountsWorkspace = computed(() => route.name === 'finances-accounts')

const accounts = computed(() => financesStore.accounts)
const categories = computed(() => financesStore.categories)
const transactions = computed(() => financesStore.transactions)
const recurringRules = computed(() => financesStore.recurring)
const recurringLoading = computed(() => loadingFinanceData.value || financesStore.loadingRecurring)
const transactionsLoading = computed(() => loadingFinanceData.value || financesStore.loadingTransactions)

const transactionCategoryOptions = computed(() =>
  categories.value.filter((category) => category.type === transactionForm.type),
)

const recurringCategoryOptions = computed(() =>
  categories.value.filter((category) => category.type === recurringForm.type),
)

const accountById = computed(() =>
  accounts.value.reduce((lookup, account) => {
    lookup[account.id] = account
    return lookup
  }, {}),
)

const categoryById = computed(() =>
  categories.value.reduce((lookup, category) => {
    lookup[category.id] = category
    return lookup
  }, {}),
)

const visibleTransactions = computed(() => {
  const filtered = transactions.value.filter((transaction) => {
    const matchesAccount =
      transactionFilters.accountId === 'all' || transaction.account_id === transactionFilters.accountId
    const matchesCategory =
      transactionFilters.categoryId === 'all' || transaction.category_id === transactionFilters.categoryId
    const matchesType = transactionFilters.type === 'all' || transaction.type === transactionFilters.type

    return matchesAccount && matchesCategory && matchesType
  })

  return [...filtered].sort((left, right) => {
    const leftDate = new Date(left.transaction_date).getTime()
    const rightDate = new Date(right.transaction_date).getTime()

    if (leftDate !== rightDate) {
      return transactionFilters.sortOrder === 'asc' ? leftDate - rightDate : rightDate - leftDate
    }

    const leftCreated = new Date(left.created_at ?? left.transaction_date).getTime()
    const rightCreated = new Date(right.created_at ?? right.transaction_date).getTime()

    if (leftCreated !== rightCreated) {
      return transactionFilters.sortOrder === 'asc' ? leftCreated - rightCreated : rightCreated - leftCreated
    }

    return transactionFilters.sortOrder === 'asc'
      ? String(left.id).localeCompare(String(right.id))
      : String(right.id).localeCompare(String(left.id))
  })
})

const visibleRecurringRules = computed(() =>
  [...recurringRules.value].sort((left, right) => {
    if (left.is_active !== right.is_active) {
      return left.is_active ? -1 : 1
    }

    const leftDate = new Date(left.start_date).getTime()
    const rightDate = new Date(right.start_date).getTime()

    if (leftDate !== rightDate) {
      return rightDate - leftDate
    }

    return String(left.id).localeCompare(String(right.id))
  }),
)

const financeSummary = computed(() =>
  dashboardStore.finances ?? {
    monthly_income: 0,
    monthly_expenses: 0,
    monthly_balance: 0,
    account_balances: [],
  },
)
const totalAccountBalance = computed(() =>
  financeSummary.value.account_balances.reduce((total, account) => total + Number(account.current_balance || 0), 0),
)
const categoryGroups = computed(() => [
  { id: 'income', label: 'Ingreso', items: categories.value.filter((category) => category.type === 'income') },
  { id: 'expense', label: 'Gasto', items: categories.value.filter((category) => category.type === 'expense') },
])

watch(
  () => transactionForm.type,
  (type) => {
    if (!transactionForm.categoryId) {
      return
    }

    const selectedCategory = categoryById.value[transactionForm.categoryId]
    if (selectedCategory && selectedCategory.type !== type) {
      transactionForm.categoryId = ''
    }
  },
)

watch(
  () => recurringForm.type,
  (type) => {
    if (!recurringForm.categoryId) {
      return
    }

    const selectedCategory = categoryById.value[recurringForm.categoryId]
    if (selectedCategory && selectedCategory.type !== type) {
      recurringForm.categoryId = ''
    }
  },
)

function accountTypeLabel(type) {
  return accountTypes.find((entry) => entry.value === type)?.label ?? type
}

function categoryTypeLabel(type) {
  return categoryTypes.find((entry) => entry.value === type)?.label ?? type
}

function transactionTypeLabel(type) {
  return transactionTypes.find((entry) => entry.value === type)?.label ?? type
}

function frequencyLabel(frequency) {
  return frequencyOptions.find((entry) => entry.value === frequency)?.label ?? frequency
}

function transactionAmountClass(type) {
  return {
    'transaction-amount--income': type === 'income',
    'transaction-amount--expense': type === 'expense',
  }
}

function recurringStatusClass(isActive) {
  return {
    'recurring-status-pill--active': isActive,
    'recurring-status-pill--paused': !isActive,
  }
}

function recurringDateRange(rule) {
  const start = formatDateShort(rule.start_date)
  const end = rule.end_date ? formatDateShort(rule.end_date) : 'Sin fin'
  return `${start} - ${end}`
}

function accountLabel(accountId) {
  return accountById.value[accountId]?.name ?? 'Cuenta eliminada'
}

function categoryLabel(categoryId) {
  return categoryById.value[categoryId]?.name ?? 'Categoría eliminada'
}

function formatTransactionAmount(transaction) {
  const prefix = transaction.type === 'expense' ? '- ' : '+ '
  return `${prefix}${formatCurrencyCop(transaction.amount)}`
}

function resetAccountForm() {
  editingAccountId.value = ''
  accountForm.name = ''
  accountForm.type = 'checking'
  accountForm.initialBalance = 0
  accountFormError.value = ''
  showAccountDialog.value = false
}

function resetCategoryForm() {
  editingCategoryId.value = ''
  categoryForm.name = ''
  categoryForm.type = 'income'
  categoryFormError.value = ''
  showCategoryDialog.value = false
}

function resetTransactionForm() {
  editingTransactionId.value = ''
  transactionForm.accountId = ''
  transactionForm.categoryId = ''
  transactionForm.type = 'expense'
  transactionForm.amount = 1
  transactionForm.description = ''
  transactionForm.transactionDate = getLocalDateString()
  transactionFormError.value = ''
  showTransactionDialog.value = false
}

function resetRecurringForm() {
  editingRecurringId.value = ''
  recurringForm.accountId = ''
  recurringForm.categoryId = ''
  recurringForm.type = 'expense'
  recurringForm.amount = 1
  recurringForm.description = ''
  recurringForm.frequency = 'monthly'
  recurringForm.startDate = getLocalDateString()
  recurringForm.endDate = ''
  recurringForm.isActive = true
  recurringFormError.value = ''
  showRecurringDialog.value = false
}

function openCreateAccountDialog() {
  resetAccountForm()
  showAccountDialog.value = true
}

function openCreateCategoryDialog() {
  resetCategoryForm()
  showCategoryDialog.value = true
}

function openCreateTransactionDialog() {
  resetTransactionForm()
  showTransactionDialog.value = true
}

function openCreateRecurringDialog() {
  resetRecurringForm()
  showRecurringDialog.value = true
}

function resetTransactionFilters() {
  transactionFilters.accountId = 'all'
  transactionFilters.categoryId = 'all'
  transactionFilters.type = 'all'
  transactionFilters.sortOrder = 'desc'
}

function startAccountEdit(account) {
  editingAccountId.value = account.id
  accountForm.name = account.name
  accountForm.type = account.type
  accountForm.initialBalance = account.initial_balance
  accountFormError.value = ''
  showAccountDialog.value = true
}

function startCategoryEdit(category) {
  editingCategoryId.value = category.id
  categoryForm.name = category.name
  categoryForm.type = category.type
  categoryFormError.value = ''
  showCategoryDialog.value = true
}

function startTransactionEdit(transaction) {
  editingTransactionId.value = transaction.id
  transactionForm.accountId = transaction.account_id
  transactionForm.categoryId = transaction.category_id
  transactionForm.type = transaction.type
  transactionForm.amount = transaction.amount
  transactionForm.description = transaction.description ?? ''
  transactionForm.transactionDate = String(transaction.transaction_date).slice(0, 10)
  transactionFormError.value = ''
  showTransactionDialog.value = true
}

function startRecurringEdit(rule) {
  editingRecurringId.value = rule.id
  recurringForm.accountId = rule.account_id
  recurringForm.categoryId = rule.category_id
  recurringForm.type = rule.type
  recurringForm.amount = rule.amount
  recurringForm.description = rule.description ?? ''
  recurringForm.frequency = rule.frequency
  recurringForm.startDate = String(rule.start_date).slice(0, 10)
  recurringForm.endDate = rule.end_date ? String(rule.end_date).slice(0, 10) : ''
  recurringForm.isActive = Boolean(rule.is_active)
  recurringFormError.value = ''
  showRecurringDialog.value = true
}

function buildAccountPayload() {
  const name = accountForm.name.trim()
  const initialBalance = Number(accountForm.initialBalance)

  if (!name) {
    throw new Error('El nombre de la cuenta es obligatorio.')
  }

  if (!Number.isInteger(initialBalance) || initialBalance < 0) {
    throw new Error('El saldo inicial debe ser cero o mayor.')
  }

  return {
    name,
    type: accountForm.type,
    initial_balance: initialBalance,
  }
}

function buildCategoryPayload() {
  const name = categoryForm.name.trim()

  if (!name) {
    throw new Error('El nombre de la categoría es obligatorio.')
  }

  return {
    name,
    type: categoryForm.type,
  }
}

function buildTransactionPayload() {
  const accountId = transactionForm.accountId
  const categoryId = transactionForm.categoryId
  const amount = Number(transactionForm.amount)
  const description = transactionForm.description.trim()
  const transactionDate = transactionForm.transactionDate
  const account = accountById.value[accountId]
  const category = categoryById.value[categoryId]

  if (!accountId) {
    throw new Error('Selecciona una cuenta.')
  }

  if (!categoryId) {
    throw new Error('Selecciona una categoría.')
  }

  if (!transactionForm.type) {
    throw new Error('Selecciona un tipo de movimiento.')
  }

  if (!account) {
    throw new Error('Selecciona una cuenta válida.')
  }

  if (!transactionDate) {
    throw new Error('La fecha del movimiento es obligatoria.')
  }

  if (!Number.isInteger(amount) || amount <= 0) {
    throw new Error('El monto debe ser mayor que cero.')
  }

  if (!category) {
    throw new Error('Selecciona una categoría válida.')
  }

  if (category.type !== transactionForm.type) {
    throw new Error('La categoría debe coincidir con el tipo del movimiento.')
  }

  return {
    account_id: accountId,
    category_id: categoryId,
    type: transactionForm.type,
    amount,
    description: description || null,
    transaction_date: transactionDate,
  }
}

function buildRecurringPayload() {
  const accountId = recurringForm.accountId
  const categoryId = recurringForm.categoryId
  const amount = Number(recurringForm.amount)
  const description = recurringForm.description.trim()
  const startDate = recurringForm.startDate
  const endDate = recurringForm.endDate || null
  const account = accountById.value[accountId]
  const category = categoryById.value[categoryId]

  if (!accountId) {
    throw new Error('Selecciona una cuenta.')
  }

  if (!categoryId) {
    throw new Error('Selecciona una categoría.')
  }

  if (!recurringForm.frequency) {
    throw new Error('Selecciona una frecuencia.')
  }

  if (!startDate) {
    throw new Error('La fecha de inicio es obligatoria.')
  }

  if (!Number.isInteger(amount) || amount <= 0) {
    throw new Error('El monto debe ser mayor que cero.')
  }

  if (!account) {
    throw new Error('Selecciona una cuenta válida.')
  }

  if (!category) {
    throw new Error('Selecciona una categoría válida.')
  }

  if (category.type !== recurringForm.type) {
    throw new Error('La categoría debe coincidir con el tipo de la regla.')
  }

  if (endDate && endDate < startDate) {
    throw new Error('La fecha de fin no puede ser anterior a la fecha de inicio.')
  }

  return {
    account_id: accountId,
    category_id: categoryId,
    type: recurringForm.type,
    amount,
    description: description || null,
    frequency: recurringForm.frequency,
    start_date: startDate,
    end_date: endDate,
    is_active: recurringForm.isActive,
  }
}

async function loadFinanceData() {
  loadingFinanceData.value = true
  try {
    await Promise.all([
      financesStore.fetchAccounts(),
      financesStore.fetchCategories(),
      financesStore.fetchTransactions(),
      financesStore.fetchRecurring(),
      dashboardStore.fetchFinances(),
    ])
  } finally {
    loadingFinanceData.value = false
  }
}

async function refreshFinanceSummary() {
  try {
    await dashboardStore.fetchFinances()
  } catch {
    return
  }
}

async function handleAccountSubmit() {
  accountFormError.value = ''

  try {
    const payload = buildAccountPayload()
    if (editingAccountId.value) {
      await financesStore.updateAccount(editingAccountId.value, payload)
    } else {
      await financesStore.createAccount(payload)
    }
    await refreshFinanceSummary()
    resetAccountForm()
  } catch (error) {
    accountFormError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleCategorySubmit() {
  categoryFormError.value = ''

  try {
    const payload = buildCategoryPayload()
    if (editingCategoryId.value) {
      await financesStore.updateCategory(editingCategoryId.value, payload)
    } else {
      await financesStore.createCategory(payload)
    }
    resetCategoryForm()
  } catch (error) {
    categoryFormError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleTransactionSubmit() {
  transactionFormError.value = ''

  try {
    const payload = buildTransactionPayload()
    if (editingTransactionId.value) {
      await financesStore.updateTransaction(editingTransactionId.value, payload)
    } else {
      await financesStore.createTransaction(payload)
    }
    await refreshFinanceSummary()
    resetTransactionForm()
  } catch (error) {
    transactionFormError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleRecurringSubmit() {
  recurringFormError.value = ''

  try {
    const payload = buildRecurringPayload()
    if (editingRecurringId.value) {
      await financesStore.updateRecurring(editingRecurringId.value, payload)
    } else {
      await financesStore.createRecurring(payload)
    }
    resetRecurringForm()
  } catch (error) {
    recurringFormError.value = error instanceof Error ? error.message : 'Revisa los datos e inténtalo de nuevo.'
  }
}

async function handleDeleteAccount(account) {
  if (!window.confirm(`¿Eliminar la cuenta "${account.name}"?`)) {
    return
  }

  try {
    await financesStore.deleteAccount(account.id)
    await refreshFinanceSummary()
    if (editingAccountId.value === account.id) {
      resetAccountForm()
    }
  } catch {
    return
  }
}

async function handleDeleteCategory(category) {
  if (!window.confirm(`¿Eliminar la categoría "${category.name}"?`)) {
    return
  }

  try {
    await financesStore.deleteCategory(category.id)
    if (editingCategoryId.value === category.id) {
      resetCategoryForm()
    }
  } catch {
    return
  }
}

async function handleDeleteTransaction(transaction) {
  const label = transaction.description || categoryLabel(transaction.category_id)
  if (!window.confirm(`¿Eliminar el movimiento "${label}"?`)) {
    return
  }

  try {
    await financesStore.deleteTransaction(transaction.id)
    await refreshFinanceSummary()
    if (editingTransactionId.value === transaction.id) {
      resetTransactionForm()
    }
  } catch {
    return
  }
}

async function handleDeleteRecurring(rule) {
  const label = rule.description || categoryLabel(rule.category_id)
  if (!window.confirm(`¿Eliminar la regla recurrente "${label}"?`)) {
    return
  }

  try {
    await financesStore.deleteRecurring(rule.id)
    if (editingRecurringId.value === rule.id) {
      resetRecurringForm()
    }
  } catch {
    return
  }
}

async function toggleRecurringActive(rule) {
  try {
    await financesStore.updateRecurring(rule.id, {
      is_active: !rule.is_active,
    })
  } catch {
    return
  }
}

onMounted(loadFinanceData)
</script>
