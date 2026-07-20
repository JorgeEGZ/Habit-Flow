import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/auth/LoginPage.vue'),
      meta: {
        guestOnly: true,
        title: 'Iniciar sesión',
      },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../pages/auth/RegisterPage.vue'),
      meta: {
        guestOnly: true,
        title: 'Crear cuenta',
      },
    },
    {
      path: '/',
      component: AppLayout,
      meta: {
        requiresAuth: true,
      },
      children: [
        {
          path: '',
          redirect: { name: 'dashboard' },
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../pages/dashboard/DashboardPage.vue'),
          meta: {
            title: 'Tablero',
            section: 'dashboard',
          },
        },
        {
          path: 'habits',
          name: 'habits',
          redirect: { name: 'habits-today' },
          meta: {
            title: 'Hábitos',
            section: 'habits',
          },
        },
        {
          path: 'habits/today',
          name: 'habits-today',
          component: () => import('../pages/habits/HabitsPage.vue'),
          meta: {
            title: 'Hoy',
            section: 'habits',
          },
        },
        {
          path: 'habits/manage',
          name: 'habits-manage',
          component: () => import('../pages/habits/HabitsPage.vue'),
          meta: {
            title: 'Mis hábitos',
            section: 'habits',
          },
        },
        {
          path: 'habits/:habitId',
          name: 'habit-detail',
          component: () => import('../pages/habits/HabitsPage.vue'),
          meta: {
            title: 'Detalle del hábito',
            section: 'habits',
          },
        },
        {
          path: 'savings',
          name: 'savings',
          redirect: { name: 'savings-goals' },
          meta: {
            title: 'Ahorros',
            section: 'savings',
          },
        },
        {
          path: 'savings/goals',
          name: 'savings-goals',
          component: () => import('../pages/savings/SavingsPage.vue'),
          meta: {
            title: 'Metas',
            section: 'savings',
          },
        },
        {
          path: 'savings/goals/:goalId',
          name: 'saving-goal-detail',
          component: () => import('../pages/savings/SavingsPage.vue'),
          meta: {
            title: 'Detalle de meta',
            section: 'savings',
          },
        },
        {
          path: 'finances',
          name: 'finances',
          redirect: { name: 'finances-movements' },
          meta: {
            title: 'Finanzas',
            section: 'finances',
          },
        },
        {
          path: 'finances/movements',
          name: 'finances-movements',
          component: () => import('../pages/finances/FinancesPage.vue'),
          meta: {
            title: 'Movimientos',
            section: 'finances',
          },
        },
        {
          path: 'finances/recurring',
          name: 'finances-recurring',
          component: () => import('../pages/finances/FinancesPage.vue'),
          meta: {
            title: 'Recurrentes',
            section: 'finances',
          },
        },
        {
          path: 'finances/accounts',
          name: 'finances-accounts',
          component: () => import('../pages/finances/FinancesPage.vue'),
          meta: {
            title: 'Cuentas',
            section: 'finances',
          },
        },
        {
          path: 'finances/categories',
          name: 'finances-categories',
          component: () => import('../pages/finances/FinancesPage.vue'),
          meta: {
            title: 'Categorías',
            section: 'finances',
          },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  await authStore.initialize()

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const guestOnly = to.matched.some((record) => record.meta.guestOnly)

  if (requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (guestOnly && authStore.isAuthenticated) {
    return {
      name: 'dashboard',
    }
  }

  return true
})

export default router
