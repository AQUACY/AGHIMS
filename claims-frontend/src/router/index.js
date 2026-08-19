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
    path: '/no-access',
    name: 'NoAccess',
    component: () => import('../pages/NoAccess.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../layouts/ClaimsLayout.vue'),
    meta: { requiresAuth: true, requiresClaimsRole: true },
    children: [
      {
        path: '',
        redirect: { name: 'Claims' },
      },
      {
        path: 'claims',
        name: 'Claims',
        component: () => import('../pages/Claims.vue'),
      },
      {
        path: 'claims/list',
        name: 'ClaimsList',
        component: () => import('../pages/ClaimsList.vue'),
      },
      {
        path: 'claims/correct-errors',
        name: 'ClaimItCorrectErrors',
        component: () => import('../pages/ClaimItCorrectErrors.vue'),
      },
      {
        path: 'claims/correct-errors/batch/:batchId',
        name: 'ClaimItCorrectErrorsBatch',
        component: () => import('../pages/ClaimItCorrectErrors.vue'),
      },
      {
        path: 'claims/ghims-import',
        name: 'GhimsXmlImport',
        component: () => import('../pages/GhimsXmlImport.vue'),
      },
      {
        path: 'claims/ai-vetting',
        name: 'AiClaimsVetting',
        component: () => import('../pages/AiClaimsVetting.vue'),
      },
      {
        path: 'claims/ai-local-assist',
        name: 'AiLocalAssist',
        component: () => import('../pages/AiLocalAssist.vue'),
      },
      {
        path: 'claims/ghims-import/batch/:batchId',
        name: 'GhimsXmlImportBatch',
        component: () => import('../pages/GhimsXmlImport.vue'),
      },
      {
        path: 'claims/ghims-import/item/:itemId',
        name: 'GhimsImportedClaimEdit',
        component: () => import('../pages/GhimsImportedClaimEdit.vue'),
      },
      {
        path: 'claims/edit/:claimId',
        name: 'EditClaim',
        component: () => import('../pages/EditClaim.vue'),
      },
      {
        path: 'claims/generate/:encounterId',
        name: 'GenerateClaim',
        component: () => import('../pages/GenerateClaim.vue'),
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
    if (!authStore.user) {
      await authStore.fetchUser();
    }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }

  if (to.meta.requiresClaimsRole) {
    if (!authStore.user && authStore.isAuthenticated) {
      await authStore.fetchUser();
    }
    if (!authStore.hasClaimsRole) {
      next({ name: 'NoAccess' });
      return;
    }
  }

  if ((to.name === 'Login' || to.name === 'NoAccess') && authStore.isAuthenticated && authStore.hasClaimsRole) {
    next({ name: 'Claims' });
    return;
  }

  next();
});

export default router;
