import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../layouts/SuhumLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: { name: 'Home' } },
      {
        path: 'home',
        name: 'Home',
        component: () => import('../pages/Home.vue'),
      },
      {
        path: 'price-list',
        name: 'PriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
      },
      {
        path: 'icd10-drg-mapping',
        name: 'Icd10DrgMapping',
        component: () => import('../pages/Icd10DrgMapping.vue'),
      },
      {
        path: 'ghims-import',
        name: 'GhimsXmlImport',
        component: () => import('../pages/GhimsXmlImport.vue'),
      },
      {
        path: 'ghims-import/batch/:batchId',
        name: 'GhimsXmlImportBatch',
        component: () => import('../pages/GhimsXmlImport.vue'),
      },
      {
        path: 'ghims-import/item/:itemId',
        name: 'GhimsImportedClaimEdit',
        component: () => import('../pages/GhimsImportedClaimEdit.vue'),
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('../pages/UserManagement.vue'),
        meta: { requiresAdmin: true },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  if (!authStore.isAuthenticated && localStorage.getItem('auth_token')) {
    authStore.initAuth();
    if (!authStore.user) await authStore.fetchUser();
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }

  if (to.meta.requiresAdmin) {
    if (!authStore.user && authStore.isAuthenticated) {
      await authStore.fetchUser();
    }
    if (!authStore.isAdmin) {
      next({ name: 'Home' });
      return;
    }
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Home' });
    return;
  }

  next();
});

export default router;
