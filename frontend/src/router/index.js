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
        meta: { requiresAuth: true, allowedRoles: ['Lab', 'Lab Head', 'Admin'] },
      },
      {
        path: '/lab/result/:investigationId',
        name: 'LabResult',
        component: () => import('../pages/LabResult.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Lab', 'Lab Head', 'Admin'] },
      },
      {
        path: '/scan',
        name: 'Scan',
        component: () => import('../pages/Scan.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Scan', 'Scan Head', 'Admin'] },
      },
      {
        path: '/scan/result/:investigationId',
        name: 'ScanResult',
        component: () => import('../pages/ScanResult.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Scan', 'Scan Head', 'Admin'] },
      },
      {
        path: '/xray',
        name: 'Xray',
        component: () => import('../pages/Xray.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Xray', 'Xray Head', 'Admin'] },
      },
      {
        path: '/xray/result/:investigationId',
        name: 'XrayResult',
        component: () => import('../pages/XrayResult.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Xray', 'Xray Head', 'Admin'] },
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
        path: '/claims/generate/:encounterId',
        name: 'GenerateClaim',
        component: () => import('../pages/GenerateClaim.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin'] },
      },
      {
        path: '/admin/price-list',
        name: 'PriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Pharmacy Head'] },
      },
      {
        path: '/admin/icd10-drg-mapping',
        name: 'Icd10DrgMapping',
        component: () => import('../pages/Icd10DrgMapping.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Billing', 'Doctor'] },
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
      {
        path: '/ipd/admission-recommendations',
        name: 'AdmissionRecommendations',
        component: () => import('../pages/AdmissionRecommendations.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/admit-patient',
        name: 'AdmitPatient',
        component: () => import('../pages/AdmitPatient.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/transfer-patient',
        name: 'TransferPatient',
        component: () => import('../pages/TransferPatient.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/doctor-nursing-station',
        name: 'DoctorNursingStation',
        component: () => import('../pages/DoctorNursingStation.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/admission-manager/:id',
        name: 'AdmissionManager',
        component: () => import('../pages/AdmissionManager.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/bed-management',
        name: 'BedManagement',
        component: () => import('../pages/BedManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin'] },
      },
      {
        path: '/ipd/registers',
        name: 'Registers',
        component: () => import('../pages/Registers.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/daily-ward-state',
        name: 'DailyWardState',
        component: () => import('../pages/DailyWardState.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/transfer-acceptance',
        name: 'TransferAcceptance',
        component: () => import('../pages/TransferAcceptance.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/nurse-mid-documentation/:id',
        name: 'NurseMidDocumentation',
        component: () => import('../pages/NurseMidDocumentation.vue'),
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

