import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { Notify } from 'quasar';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { requiresAuth: false },
  },
 
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../pages/Dashboard.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/profile',
        name: 'UserProfile',
        component: () => import('../pages/UserProfile.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/patients/register',
        name: 'PatientRegistration',
        component: () => import('../pages/PatientRegistration.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Records', 'Admin', 'PA', 'Doctor'] },
      },
      {
        path: '/patients/:cardNumber',
        name: 'PatientProfile',
        component: () => import('../pages/PatientProfile.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/patients/search/results',
        name: 'PatientSearchResults',
        component: () => import('../pages/PatientSearchResults.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/encounters/calendar',
        name: 'EncountersCalendar',
        component: () => import('../pages/EncountersCalendar.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/vitals',
        name: 'Vitals',
        component: () => import('../pages/Vitals.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/consultation/:encounterId?',
        name: 'Consultation',
        component: () => import('../pages/Consultation.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/billing/:encounterId?',
        name: 'Billing',
        component: () => import('../pages/Billing.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Billing', 'Admin'] },
      },
      {
        path: '/pharmacy',
        name: 'Pharmacy',
        component: () => import('../pages/Pharmacy.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Admin'] },
      },
      {
        path: '/lab',
        name: 'Lab',
        component: () => import('../pages/Lab.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Lab', 'Admin'] },
      },
      {
        path: '/scan',
        name: 'Scan',
        component: () => import('../pages/Scan.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Scan', 'Admin'] },
      },
      {
        path: '/xray',
        name: 'Xray',
        component: () => import('../pages/Xray.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Xray', 'Admin'] },
      },
      {
        path: '/claims',
        name: 'Claims',
        component: () => import('../pages/Claims.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin'] },
      },
      {
        path: '/claims/edit/:claimId',
        name: 'EditClaim',
        component: () => import('../pages/EditClaim.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin'] },
      },
      {
        path: '/admin/price-list',
        name: 'PriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Pharmacy Head'] },
      },
      {
        path: '/admin/staff',
        name: 'StaffManagement',
        component: () => import('../pages/StaffManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/admin/patient-upload',
        name: 'PatientUpload',
        component: () => import('../pages/PatientUpload.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/ipd',
        name: 'IPD',
        component: () => import('../pages/IPD.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
    ],
  },
];

// Use /frontend/ as base path in production
const base = process.env.NODE_ENV === 'production' ? '/frontend/' : '/';

const router = createRouter({
  history: createWebHistory(base),
  routes,
});

// Navigation guard
router.beforeEach((to, from, next) => {
  try {
    const authStore = useAuthStore();

    // Initialize auth if needed
    if (!authStore.isAuthenticated && localStorage.getItem('auth_token')) {
      authStore.initAuth();
    }

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      next('/login');
    } else if (to.path === '/login' && authStore.isAuthenticated) {
      next('/');
    } else if (to.meta.requiresRole) {
      // Check for specific role requirement (e.g., Admin only)
      if (authStore.userRole !== to.meta.requiresRole) {
        next('/');
      } else {
        next();
      }
    } else if (to.meta.allowedRoles) {
      const canAccess = authStore.canAccess(to.meta.allowedRoles);
      if (!canAccess) {
        console.warn('Access denied:', {
          path: to.path,
          userRole: authStore.userRole,
          allowedRoles: to.meta.allowedRoles,
          user: authStore.user
        });
        // Show notification and redirect to dashboard
        Notify.create({
          type: 'negative',
          message: `Access denied. Your role (${authStore.userRole || 'Unknown'}) does not have permission to access this page. Required roles: ${to.meta.allowedRoles.join(', ')}`,
          position: 'top',
        });
        next('/');
      } else {
        next();
      }
    } else {
      next();
    }
  } catch (error) {
    console.error('Router guard error:', error);
    // If there's an error, allow navigation to login
    if (to.path !== '/login') {
      next('/login');
    } else {
      next();
    }
  }
});

export default router;

