import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useModuleSettingsStore } from '../stores/moduleSettings';
import { useAppModeStore, APP_MODES, APP_MODE_MODULE_KEYS } from '../stores/appMode';
import { Notify } from 'quasar';
import { licenseAPI } from '../services/api';
import { getCachedLicensePublic } from '../utils/licensePublicCache';

const routes = [
  {
    path: '/license-setup',
    name: 'LicenseSetup',
    component: () => import('../pages/LicenseSetup.vue'),
    meta: { requiresAuth: false },
  },
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
        meta: { requiresAuth: true, allowedRoles: ['Management', 'Admin', 'Billing'] },
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
        meta: { requiresAuth: true, requiresInventoryHubAccess: true },
      },
      {
        path: '/pharmacy/requisitions/create',
        name: 'CreateRequisition',
        component: () => import('../pages/CreateRequisition.vue'),
        meta: { requiresAuth: true, requireCreateRequisitionAccess: true },
      },
      {
        path: '/pharmacy/ward-stock',
        name: 'WardStock',
        component: () => import('../pages/WardStock.vue'),
        meta: { requiresAuth: true, requiresWardStockAccess: true },
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
        path: '/claims/ghims-import',
        name: 'GhimsXmlImport',
        component: () => import('../pages/GhimsXmlImport.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/ghims-import/batch/:batchId',
        name: 'GhimsXmlImportBatch',
        component: () => import('../pages/GhimsXmlImport.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Claims', 'Admin', 'Doctor', 'PA'] },
      },
      {
        path: '/claims/ghims-import/item/:itemId',
        name: 'GhimsImportedClaimEdit',
        component: () => import('../pages/GhimsImportedClaimEdit.vue'),
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
        meta: { requiresAuth: true, requiresInventoryHubAccess: true },
      },
      {
        path: '/admin/store-stock',
        name: 'StoreStockManagement',
        component: () => import('../pages/StoreStockManagement.vue'),
        meta: { requiresAuth: true, inventoryStoreStockAccess: true },
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
        path: 'reports',
        name: 'InventoryModeReports',
        component: () => import('../pages/InventoryReports.vue'),
        meta: { requiresAuth: true, requiresInventoryHubAccess: true },
      },
      {
        path: 'store-stock',
        name: 'InventoryModeStoreStock',
        component: () => import('../pages/StoreStockManagement.vue'),
        meta: { requiresAuth: true, inventoryStoreStockAccess: true },
      },
      {
        path: 'requisitions',
        name: 'InventoryModeRequisitions',
        component: () => import('../pages/PharmacyRequisitions.vue'),
        meta: { requiresAuth: true, requiresInventoryHubAccess: true },
      },
      {
        path: 'requisitions/create',
        name: 'InventoryModeCreateRequisition',
        component: () => import('../pages/CreateRequisition.vue'),
        meta: { requiresAuth: true, requireCreateRequisitionAccess: true },
      },
      {
        path: 'ward-stock',
        name: 'InventoryModeWardStock',
        component: () => import('../pages/WardStock.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'inventory-debits',
        name: 'InventoryModeDebits',
        component: () => import('../pages/InventoryDebitManagement.vue'),
        meta: {
          requiresAuth: true,
          allowedRoles: ['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Management', 'Admin'],
        },
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
        path: 'audit-logs',
        name: 'InventoryModeAuditLogs',
        component: () => import('../pages/AuditLogs.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Auditor'] },
      },
      {
        path: 'price-list',
        name: 'InventoryModePriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Pharmacy Head', 'Store Manager'] },
      },
      {
        path: 'staff',
        name: 'InventoryModeStaffManagement',
        component: () => import('../pages/StaffManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
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
        path: 'visits/:id/inventory-debit',
        name: 'CompanionInventoryDebit',
        component: () => import('../pages/companion/CompanionInventoryDebit.vue'),
        meta: {
          requiresAuth: true,
          allowedRoles: ['Nurse', 'Doctor', 'PA', 'Pharmacy', 'Pharmacy Head', 'Billing', 'Admin'],
        },
      },
      {
        path: 'billing',
        name: 'CompanionBilling',
        component: () => import('../pages/companion/CompanionBilling.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Billing', 'Records', 'Admin'] },
      },
      {
        path: 'audit-logs',
        name: 'CompanionAuditLogs',
        component: () => import('../pages/AuditLogs.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Auditor'] },
      },
      {
        path: 'price-list',
        name: 'CompanionPriceListManagement',
        component: () => import('../pages/PriceListManagement.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Admin', 'Pharmacy Head', 'Store Manager'] },
      },
      {
        path: 'staff',
        name: 'CompanionStaffManagement',
        component: () => import('../pages/StaffManagement.vue'),
        meta: { requiresAuth: true, requiresRole: 'Admin' },
      },
      {
        path: 'management/transactions',
        name: 'CompanionManagementTransactions',
        component: () => import('../pages/ManagementTransactions.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Management', 'Admin'] },
      },
      {
        path: 'management/undertakings',
        name: 'CompanionManagementUndertakings',
        component: () => import('../pages/ManagementUndertakings.vue'),
        meta: { requiresAuth: true, allowedRoles: ['Management', 'Admin', 'Billing'] },
      },
    ],
  },
];

// Must match quasar.config.js build.publicPath (Vite injects import.meta.env.BASE_URL, e.g. /frontend/)
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
  'InventoryModeReports': 'inventory',
  'StoreStockManagement': 'inventory',
  'InventoryModeStoreStock': 'inventory',
  'InventoryModeRequisitions': 'inventory',
  'InventoryModeCreateRequisition': 'inventory',
  'InventoryModeWardStock': 'inventory',
  'InventoryModeDebits': 'inventory',
  'InventoryModeStoreManagement': 'inventory',
  'InventoryModeWardManagement': 'inventory',
  'InventoryModeAuditLogs': 'audit_logs',
  'InventoryModePriceListManagement': 'price_list',
  'InventoryModeStaffManagement': 'staff',
  'Icd10DrgMapping': 'icd10_mapping',
  'StaffManagement': 'staff',
  'CompanionPriceListManagement': 'price_list',
  'CompanionStaffManagement': 'staff',
  'AuditLogs': 'audit_logs',
  'CompanionAuditLogs': 'audit_logs',
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

    let licenseOk = true;
    try {
      const data = await getCachedLicensePublic(() => licenseAPI.getPublicStatus());
      if (data.enforcement_enabled && !data.has_valid_license) {
        licenseOk = false;
      }
    } catch {
      licenseOk = true;
    }

    if (!licenseOk && to.meta.requiresAuth) {
      next('/license-setup');
      return;
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
      // License page must not run mode/module/role guards (avoids blank screen and redirect loops).
      if (to.path === '/license-setup') {
        next();
        return;
      }

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

      if (
        !isSuperAdmin &&
        appModeStore.currentMode === APP_MODES.COMPANION &&
        !isCompanionRoute &&
        to.path !== '/license-setup'
      ) {
        next('/companion');
        return;
      }
      if (
        !isSuperAdmin &&
        appModeStore.currentMode === APP_MODES.INVENTORY &&
        !isInventoryRoute &&
        to.path !== '/license-setup'
      ) {
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
        return;
      }
      if (!isSuperAdmin && appModeStore.currentMode === APP_MODES.HMS && (isCompanionRoute || isInventoryRoute)) {
        next('/');
        return;
      }

      if (!isSuperAdmin && to.path.startsWith('/inventory-mode')) {
        if (authStore.user?.can_access_inventory_mode === undefined) {
          try {
            await authStore.fetchUser();
          } catch (e) {
            void 0;
          }
        }
        if (!authStore.canAccessInventoryMode) {
          Notify.create({
            type: 'negative',
            message:
              'You do not have access to Inventory mode. It is limited to department IC/deputy assignments, store assignments, Management, or authorized roles.',
            position: 'top',
          });
          next('/choose-mode');
          return;
        }
      }

      if (to.meta.requiresInventoryHubAccess) {
        if (!isSuperAdmin) {
          if (authStore.user?.can_access_inventory_mode === undefined) {
            try {
              await authStore.fetchUser();
            } catch (e) {
              void 0;
            }
          }
          if (!authStore.canAccessInventoryMode) {
            Notify.create({
              type: 'negative',
              message:
                'Requisitions require department IC/deputy or store assignment, Management, Pharmacy, or other authorized roles.',
              position: 'top',
            });
            next('/');
            return;
          }
        }
        next();
        return;
      }

      if (to.meta.requiresWardStockAccess) {
        if (!isSuperAdmin) {
          if (authStore.user?.can_access_inventory_mode === undefined) {
            try {
              await authStore.fetchUser();
            } catch (e) {
              void 0;
            }
          }
          const byInventoryMode = authStore.canAccessInventoryMode;
          const byClinicalOrPharmacy = authStore.canAccess([
            'Nurse',
            'Doctor',
            'PA',
            'Pharmacy Head',
            'Pharmacy',
            'Store Manager',
            'Department Head',
            'Management',
            'Admin',
          ]);
          if (!byInventoryMode && !byClinicalOrPharmacy) {
            Notify.create({
              type: 'negative',
              message:
                'Department/unit stock requires pharmacy/clinical access or Inventory mode access (e.g. department IC/deputy assignment).',
              position: 'top',
            });
            next('/');
            return;
          }
        }
        next();
        return;
      }

      if (to.meta.requireCreateRequisitionAccess) {
        if (!isSuperAdmin) {
          const ok =
            authStore.canAccess(['Admin']) || Boolean(authStore.user?.is_department_ic_or_deputy);
          if (!ok) {
            Notify.create({
              type: 'negative',
              message: 'Only Admin or department IC/deputy can create requisitions.',
              position: 'top',
            });
            next(
              to.path.startsWith('/inventory-mode')
                ? '/inventory-mode/requisitions'
                : '/pharmacy/requisitions'
            );
            return;
          }
        }
        next();
        return;
      }

      if (to.meta.inventoryStoreStockAccess) {
        if (!isSuperAdmin) {
          const roleOk = authStore.canAccess([
            'Admin',
            'Management',
            'Store Manager',
            'Department Head',
            'Pharmacy Head',
            'Pharmacy',
          ]);
          const assignOk =
            Boolean(authStore.user?.has_store_manager_assignment) ||
            Boolean(authStore.user?.has_store_department_head_assignment);
          if (!roleOk && !assignOk) {
            Notify.create({
              type: 'negative',
              message:
                'Store stock needs a store or department-head assignment, or an authorized role.',
              position: 'top',
            });
            next(to.path.startsWith('/inventory-mode') ? '/inventory-mode' : '/');
            return;
          }
        }
        next();
        return;
      }

      if (to.meta.requiresRole) {
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
        let canAccess = authStore.canAccess(to.meta.allowedRoles);
        if (!canAccess) {
          console.warn('Access denied:', {
            path: to.path,
            userRole: authStore.userRole,
            allUserRoles: authStore.allUserRoles,
            allowedRoles: to.meta.allowedRoles,
            user: authStore.user,
          });
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
    if (to.path === '/license-setup') {
      next();
      return;
    }
    if (to.path !== '/login') {
      next('/login');
    } else {
      next();
    }
  }
});

export default router;

