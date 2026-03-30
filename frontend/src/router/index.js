import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useModuleSettingsStore } from '../stores/moduleSettings';
import { useAppModeStore, APP_MODES, APP_MODE_MODULE_KEYS } from '../stores/appMode';
import { Notify } from 'quasar';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/choose-mode',
    name: 'ChooseMode',
    component: () => import('../pages/ChooseMode.vue'),
    meta: { requiresAuth: true },
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
        path: '/management/transactions',
        name: 'ManagementTransactions',
        component: () => import('../pages/ManagementTransactions.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Management', 'Admin'] },
      },
      {
        path: '/management/undertakings',
        name: 'ManagementUndertakings',
        component: () => import('../pages/ManagementUndertakings.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Management', 'Admin'] },
      },
      {
        path: '/pharmacy',
        name: 'Pharmacy',
        component: () => import('../pages/Pharmacy.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: '/pharmacy/inventory-debits',
        name: 'InventoryDebitManagement',
        component: () => import('../pages/InventoryDebitManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: '/pharmacy/requisitions',
        name: 'PharmacyRequisitions',
        component: () => import('../pages/PharmacyRequisitions.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: '/pharmacy/requisitions/create',
        name: 'CreateRequisition',
        component: () => import('../pages/CreateRequisition.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/pharmacy/ward-stock',
        name: 'WardStock',
        component: () => import('../pages/WardStock.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin'] },
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
        path: '/lab/templates',
        name: 'LabTemplates',
        component: () => import('../pages/LabTemplates.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Lab Head', 'Admin'] },
      },
      {
        path: '/lab/results/formatted/:investigationId',
        name: 'FormattedLabResult',
        component: () => import('../pages/FormattedLabResult.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Doctor', 'PA', 'Admin', 'Lab', 'Lab Head'] },
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
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/list',
        name: 'ClaimsList',
        component: () => import('../pages/ClaimsList.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/correct-errors',
        name: 'ClaimItCorrectErrors',
        component: () => import('../pages/ClaimItCorrectErrors.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/correct-errors/batch/:batchId',
        name: 'ClaimItCorrectErrorsBatch',
        component: () => import('../pages/ClaimItCorrectErrors.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/edit/:claimId',
        name: 'EditClaim',
        component: () => import('../pages/EditClaim.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/generate/:encounterId',
        name: 'GenerateClaim',
        component: () => import('../pages/GenerateClaim.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/admin/price-list',
        name: 'PriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Pharmacy Head', 'Store Manager'] },
      },
      {
        path: '/inventory',
        name: 'InventoryManagement',
        component: () => import('../pages/InventoryManagement.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: '/admin/store-stock',
        name: 'StoreStockManagement',
        component: () => import('../pages/StoreStockManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Store Manager', 'Department Head', 'Pharmacy Head'] },
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
        path: '/admin/audit-logs',
        name: 'AuditLogs',
        component: () => import('../pages/AuditLogs.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Auditor'] },
      },
      {
        path: '/admin/patient-upload',
        name: 'PatientUpload',
        component: () => import('../pages/PatientUpload.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/admin/additional-services',
        name: 'AdditionalServicesManagement',
        component: () => import('../pages/AdditionalServicesManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/admin/blood-transfusion-types',
        name: 'BloodTransfusionTypesManagement',
        component: () => import('../pages/BloodTransfusionTypesManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Lab Head'] },
      },
      {
        path: '/admin/database',
        name: 'DatabaseManagement',
        component: () => import('../pages/DatabaseManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/admin/module-management',
        name: 'ModuleManagement',
        component: () => import('../pages/ModuleManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: '/admin/facility-setup',
        name: 'FacilitySetup',
        component: () => import('../pages/FacilitySetup.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin', facilitySetup: true },
      },
      {
        path: '/ipd/inventory-debit/:id',
        name: 'InpatientInventoryDebit',
        component: () => import('../pages/InpatientInventoryDebit.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/blood-transfusion-request/:id',
        name: 'BloodTransfusionRequest',
        component: () => import('../pages/BloodTransfusionRequest.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/lab/blood-transfusion-requests',
        name: 'BloodTransfusionLabManagement',
        component: () => import('../pages/BloodTransfusionLabManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Lab', 'Lab Head', 'Admin'] },
      },
      {
        path: '/ipd',
        name: 'IPD',
        component: () => import('../pages/IPD.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/ward-management',
        name: 'WardManagement',
        component: () => import('../pages/WardManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin'] },
      },
      {
        path: '/ipd/store-management',
        name: 'StoreManagement',
        component: () => import('../pages/StoreManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin'] },
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
        path: '/ipd/operation-theatre-calendar',
        name: 'OperationTheatreCalendar',
        component: () => import('../pages/OperationTheatreCalendar.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin', 'Anaesthetist'] },
      },
      {
        path: '/ipd/nurse-mid-documentation/:id',
        name: 'NurseMidDocumentation',
        component: () => import('../pages/NurseMidDocumentation.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/clinical-review/:id',
        name: 'ClinicalReview',
        component: () => import('../pages/ClinicalReview.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/ipd/treatment-sheet/:id',
        name: 'TreatmentSheet',
        component: () => import('../pages/TreatmentSheet.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: '/mis-reports',
        name: 'MISReport',
        component: () => import('../pages/MISReport.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Records'] },
      },
    ],
  },
  {
    path: '/inventory-mode',
    component: () => import('../layouts/InventoryLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'InventoryModeDashboard',
        component: () => import('../pages/InventoryManagement.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'store-stock',
        name: 'InventoryModeStoreStock',
        component: () => import('../pages/StoreStockManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Store Manager', 'Department Head', 'Pharmacy Head'] },
      },
      {
        path: 'requisitions',
        name: 'InventoryModeRequisitions',
        component: () => import('../pages/PharmacyRequisitions.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: 'requisitions/create',
        name: 'InventoryModeCreateRequisition',
        component: () => import('../pages/CreateRequisition.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: 'ward-stock',
        name: 'InventoryModeWardStock',
        component: () => import('../pages/WardStock.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: 'inventory-debits',
        name: 'InventoryModeDebits',
        component: () => import('../pages/InventoryDebitManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'] },
      },
      {
        path: 'store-management',
        name: 'InventoryModeStoreManagement',
        component: () => import('../pages/StoreManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin'] },
      },
      {
        path: 'ward-management',
        name: 'InventoryModeWardManagement',
        component: () => import('../pages/WardManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin'] },
      },
      {
        path: 'profile',
        name: 'InventoryModeProfile',
        component: () => import('../pages/UserProfile.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'facility-setup',
        name: 'InventoryFacilitySetup',
        component: () => import('../pages/FacilitySetup.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin', facilitySetup: true },
      },
    ],
  },
  {
    path: '/companion',
    component: () => import('../layouts/CompanionLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'CompanionDashboard',
        component: () => import('../pages/CompanionDashboard.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'profile',
        name: 'CompanionProfile',
        component: () => import('../pages/UserProfile.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'facility-setup',
        name: 'CompanionFacilitySetup',
        component: () => import('../pages/FacilitySetup.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin', facilitySetup: true },
      },
      {
        path: 'visits/create',
        name: 'CompanionCreateService',
        component: () => import('../pages/companion/CompanionCreateService.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Records', 'Admin'] },
      },
      {
        path: 'visits',
        name: 'CompanionVisitList',
        component: () => import('../pages/companion/CompanionVisitList.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'visits/:id',
        name: 'CompanionVisitDetail',
        component: () => import('../pages/companion/CompanionVisitDetail.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'visits/:id/investigation',
        name: 'CompanionAddInvestigation',
        component: () => import('../pages/companion/CompanionAddInvestigation.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Lab', 'Lab Head', 'Admin'] },
      },
      {
        path: 'visits/:id/drugs',
        name: 'CompanionAddDrugs',
        component: () => import('../pages/companion/CompanionAddDrugs.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Admin'] },
      },
      {
        path: 'visits/:id/scan',
        name: 'CompanionAddScan',
        component: () => import('../pages/companion/CompanionAddScan.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Scan', 'Scan Head', 'Admin'] },
      },
      {
        path: 'visits/:id/xray',
        name: 'CompanionAddXray',
        component: () => import('../pages/companion/CompanionAddXray.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Xray', 'Xray Head', 'Admin'] },
      },
      {
        path: 'visits/:id/day-surgery',
        name: 'CompanionAddDaySurgery',
        component: () => import('../pages/companion/CompanionAddDaySurgery.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: 'visits/:id/major-surgery',
        name: 'CompanionAddMajorSurgery',
        component: () => import('../pages/companion/CompanionAddMajorSurgery.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: 'visits/:id/dressing',
        name: 'CompanionAddDressing',
        component: () => import('../pages/companion/CompanionAddDressing.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: 'visits/:id/oxygen',
        name: 'CompanionAddOxygen',
        component: () => import('../pages/companion/CompanionAddOxygen.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
      },
      {
        path: 'billing',
        name: 'CompanionBilling',
        component: () => import('../pages/companion/CompanionBilling.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Billing', 'Admin'] },
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

// Module key mapping for routes
const routeModuleMap = {
  'PatientRegistration': 'patients',
  'PatientProfile': 'patients',
  'PatientSearchResults': 'patients',
  'EncountersCalendar': 'encounters',
  'Vitals': 'vitals',
  'Consultation': 'consultation',
  'Billing': 'billing',
  'Pharmacy': 'pharmacy',
  'InventoryDebitManagement': 'pharmacy',
  'PharmacyRequisitions': 'pharmacy',
  'CreateRequisition': 'pharmacy',
  'WardStock': 'pharmacy',
  'Lab': 'lab',
  'LabResult': 'lab',
  'LabTemplates': 'lab',
  'FormattedLabResult': 'lab',
  'Scan': 'scan',
  'ScanResult': 'scan',
  'Xray': 'xray',
  'XrayResult': 'xray',
  'Claims': 'claims',
  'EditClaim': 'claims',
  'GenerateClaim': 'claims',
  'IPD': 'ipd',
  'WardManagement': 'ipd',
  'StoreManagement': 'ipd',
  'AdmissionRecommendations': 'ipd',
  'AdmitPatient': 'ipd',
  'TransferPatient': 'ipd',
  'DoctorNursingStation': 'ipd',
  'AdmissionManager': 'ipd',
  'BedManagement': 'ipd',
  'Registers': 'ipd',
  'DailyWardState': 'ipd',
  'TransferAcceptance': 'ipd',
  'OperationTheatreCalendar': 'ipd',
  'NurseMidDocumentation': 'ipd',
  'ClinicalReview': 'ipd',
  'TreatmentSheet': 'ipd',
  'InpatientInventoryDebit': 'ipd',
  'BloodTransfusionRequest': 'ipd',
  'BloodTransfusionLabManagement': 'ipd',
  'PriceListManagement': 'price_list',
  'InventoryManagement': 'inventory',
  'InventoryModeDashboard': 'inventory',
  'StoreStockManagement': 'inventory',
  'InventoryModeStoreStock': 'inventory',
  'InventoryModeRequisitions': 'inventory',
  'InventoryModeCreateRequisition': 'inventory',
  'InventoryModeWardStock': 'inventory',
  'InventoryModeDebits': 'inventory',
  'InventoryModeStoreManagement': 'inventory',
  'InventoryModeWardManagement': 'inventory',
  'Icd10DrgMapping': 'icd10_mapping',
  'StaffManagement': 'staff',
  'AuditLogs': 'audit_logs',
  'PatientUpload': 'patients',
  'AdditionalServicesManagement': 'additional_services',
  'BloodTransfusionTypesManagement': 'blood_transfusion',
  'DatabaseManagement': 'database',
  'MISReport': 'mis_reports',
  'ModuleManagement': 'staff', // Admin only, use staff module check
};

// Navigation guard
router.beforeEach(async (to, from, next) => {
  try {
    const authStore = useAuthStore();
    const moduleSettingsStore = useModuleSettingsStore();
    const appModeStore = useAppModeStore();
    const isSuperAdmin = Boolean(authStore.user?.is_super_admin);

    // Initialize auth if needed
    if (!authStore.isAuthenticated && localStorage.getItem('auth_token')) {
      authStore.initAuth();
    }

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      next('/login');
    } else if (to.path === '/login' && authStore.isAuthenticated) {
      next('/choose-mode');
    } else if (to.path === '/' && authStore.isAuthenticated) {
      if (appModeStore.currentMode === APP_MODES.COMPANION) {
        next('/companion');
      } else if (appModeStore.currentMode === APP_MODES.INVENTORY) {
        next('/inventory-mode');
      } else {
        next();
      }
    } else if (to.path === '/choose-mode') {
      next();
    } else if (authStore.isAuthenticated) {
      // Facility-level mode activation check (Super Admin bypass).
      const selectedModeModuleKey = APP_MODE_MODULE_KEYS[appModeStore.currentMode];
      if (!isSuperAdmin && selectedModeModuleKey) {
        // Always fetch fresh status to avoid stale cache allowing inactive mode access.
        await moduleSettingsStore.fetchModuleStatus([selectedModeModuleKey]);
        if (!moduleSettingsStore.isModuleActive(selectedModeModuleKey)) {
          next('/choose-mode');
          return;
        }
      }

      // Restrict navigation based on currently selected application mode.
      const isCompanionRoute = to.path.startsWith('/companion');
      const isInventoryRoute = to.path.startsWith('/inventory-mode');

      if (!isSuperAdmin && appModeStore.currentMode === APP_MODES.COMPANION && !isCompanionRoute) {
        next('/companion');
      } else if (!isSuperAdmin && appModeStore.currentMode === APP_MODES.INVENTORY && !isInventoryRoute) {
        const inventoryPathRedirects = {
          '/inventory': '/inventory-mode',
          '/admin/store-stock': '/inventory-mode/store-stock',
          '/pharmacy/requisitions': '/inventory-mode/requisitions',
          '/pharmacy/requisitions/create': '/inventory-mode/requisitions/create',
          '/pharmacy/ward-stock': '/inventory-mode/ward-stock',
          '/pharmacy/inventory-debits': '/inventory-mode/inventory-debits',
          '/ipd/store-management': '/inventory-mode/store-management',
          '/ipd/ward-management': '/inventory-mode/ward-management',
        };
        next(inventoryPathRedirects[to.path] || '/inventory-mode');
      } else if (!isSuperAdmin && appModeStore.currentMode === APP_MODES.HMS && (isCompanionRoute || isInventoryRoute)) {
        next('/');
      } else if (to.meta.requiresRole) {
        // Check for specific role requirement (e.g., Admin only)
        // Super Admin may open facility setup without Admin role
        const roleOk = authStore.canAccess([to.meta.requiresRole]);
        const superOk = to.meta.facilitySetup && authStore.isSuperAdmin;
        if (!roleOk && !superOk) {
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
            allUserRoles: authStore.allUserRoles,
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
        // Check module status if route has a module mapping
        const moduleKey = routeModuleMap[to.name];
        if (moduleKey) {
          // Fetch module status if not already loaded
          if (!moduleSettingsStore.modules[moduleKey]) {
            await moduleSettingsStore.fetchModuleStatus([moduleKey]);
          }

          const moduleStatus = moduleSettingsStore.getModuleStatus(moduleKey);
          if (!moduleStatus.is_active) {
            Notify.create({
              type: 'warning',
              message: 'This module is currently inactive',
              position: 'top',
            });
            next('/'); // Redirect to dashboard
            return;
          }
        }

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

