/**
 * Navigation config for HMS + Claims modes.
 * Roles / moduleKey gate visibility; labels drive Favorites & Recents.
 */

export const HMS_NAV_GROUPS = [
  {
    id: 'clinical',
    label: 'Clinical',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', to: { name: 'Dashboard' } },
      {
        id: 'patient-registration',
        label: 'Patient Registration',
        icon: 'person_add',
        to: { name: 'PatientRegistration' },
        roles: ['Records', 'Admin', 'PA', 'Doctor'],
      },
      {
        id: 'encounters-calendar',
        label: 'Appointment Calendar',
        icon: 'calendar_month',
        to: { name: 'EncountersCalendar' },
      },
      {
        id: 'vitals',
        label: 'Vitals',
        icon: 'favorite',
        to: { name: 'Vitals' },
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
      {
        id: 'consultation',
        label: 'Consultation',
        icon: 'medical_services',
        to: { name: 'Consultation' },
        roles: ['Doctor', 'PA', 'Admin'],
      },
      {
        id: 'ipd',
        label: 'IPD',
        icon: 'local_hospital',
        to: { name: 'IPD' },
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
    ],
  },
  {
    id: 'diagnostics',
    label: 'Diagnostics',
    items: [
      {
        id: 'lab',
        label: 'Lab',
        icon: 'science',
        to: { name: 'Lab' },
        roles: ['Lab', 'Admin', 'Lab Head'],
      },
      {
        id: 'lab-templates',
        label: 'Lab Templates',
        icon: 'description',
        to: { name: 'LabTemplates' },
        roles: ['Lab Head', 'Admin'],
      },
      {
        id: 'scan',
        label: 'Scan',
        icon: 'biotech',
        to: { name: 'Scan' },
        roles: ['Scan', 'Scan Head', 'Admin'],
      },
      {
        id: 'xray',
        label: 'X-ray',
        icon: 'radio_button_checked',
        to: { name: 'Xray' },
        roles: ['Xray', 'Xray Head', 'Admin'],
      },
      {
        id: 'blood-transfusion-lab',
        label: 'Blood Transfusion Requests',
        icon: 'science',
        to: { name: 'BloodTransfusionLabManagement' },
        roles: ['Lab', 'Lab Head', 'Admin'],
      },
    ],
  },
  {
    id: 'pharmacy-finance',
    label: 'Pharmacy & Finance',
    items: [
      {
        id: 'pharmacy',
        label: 'Pharmacy',
        icon: 'medication',
        to: { name: 'Pharmacy' },
        roles: ['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'],
      },
      {
        id: 'billing',
        label: 'Billing',
        icon: 'receipt',
        to: { name: 'Billing' },
        roles: ['Billing', 'Admin'],
        moduleKey: 'billing',
      },
      {
        id: 'claims',
        label: 'Claims',
        icon: 'description',
        to: { name: 'Claims' },
        roles: ['Claims', 'Admin', 'Doctor', 'PA'],
        moduleKey: 'claims',
      },
      {
        id: 'mis-reports',
        label: 'MIS Reports',
        icon: 'assessment',
        to: { name: 'MISReport' },
        roles: ['Admin', 'Records'],
      },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    items: [
      {
        id: 'price-list',
        label: 'Price List Management',
        icon: 'price_check',
        to: { name: 'PriceListManagement' },
        roles: ['Admin', 'Pharmacy Head', 'Store Manager'],
      },
      {
        id: 'staff',
        label: 'Staff Management',
        icon: 'people',
        to: { name: 'StaffManagement' },
        roles: ['Admin'],
      },
      {
        id: 'patient-upload',
        label: 'Patient Upload',
        icon: 'file_upload',
        to: { name: 'PatientUpload' },
        roles: ['Admin'],
      },
      {
        id: 'icd10',
        label: 'ICD-10 DRG Mapping',
        icon: 'medical_information',
        to: { name: 'Icd10DrgMapping' },
        roles: ['Admin'],
      },
      {
        id: 'additional-services',
        label: 'Additional Services',
        icon: 'add_circle',
        to: { name: 'AdditionalServicesManagement' },
        roles: ['Admin'],
      },
      {
        id: 'blood-types',
        label: 'Blood Transfusion Types',
        icon: 'bloodtype',
        to: { name: 'BloodTransfusionTypesManagement' },
        roles: ['Admin', 'Lab Head'],
      },
      {
        id: 'database',
        label: 'Database Management',
        icon: 'storage',
        to: { name: 'DatabaseManagement' },
        roles: ['Admin'],
      },
      {
        id: 'modules',
        label: 'Module Management',
        icon: 'settings_applications',
        to: { name: 'ModuleManagement' },
        roles: ['Admin'],
      },
      {
        id: 'facility',
        label: 'Facility branding',
        icon: 'business',
        to: { name: 'FacilitySetup' },
        roles: ['Admin'],
        allowSuperAdmin: true,
      },
      {
        id: 'audit',
        label: 'Audit Trail Logs',
        icon: 'history',
        to: { name: 'AuditLogs' },
        roles: ['Admin', 'Auditor'],
      },
    ],
  },
];

export const CLAIMS_NAV_GROUPS = [
  {
    id: 'claims-main',
    label: 'Claims',
    items: [
      { id: 'claims-home', label: 'Claims home', icon: 'apps', to: { name: 'Claims' }, moduleKey: 'claims' },
      { id: 'claims-dashboard', label: 'Dashboard', icon: 'dashboard', to: { name: 'ClaimsDashboard' }, moduleKey: 'claims' },
      { id: 'claims-list', label: 'Claims', icon: 'description', to: { name: 'ClaimsList' }, moduleKey: 'claims' },
      { id: 'claims-reports', label: 'Reports', icon: 'assessment', to: { name: 'ClaimsReports' }, moduleKey: 'claims' },
      { id: 'claims-errors', label: 'Correct errors', icon: 'error_outline', to: { name: 'ClaimItCorrectErrors' }, moduleKey: 'claims' },
      { id: 'claims-ghims', label: 'Import GHIMS XML', icon: 'upload_file', to: { name: 'GhimsXmlImport' }, moduleKey: 'claims' },
      { id: 'claims-ai-vetting', label: 'AI Vetting', icon: 'auto_awesome', to: { name: 'AiClaimsVetting' }, moduleKey: 'claims' },
      { id: 'claims-ai-local-assist', label: 'Local AI Assist', icon: 'smart_toy', to: { name: 'AiLocalAssist' }, moduleKey: 'claims' },
      { id: 'claims-cfx', label: 'CFX Convert & Diff', icon: 'compare_arrows', to: { name: 'ClaimsCxfTools' }, moduleKey: 'claims' },
      {
        id: 'claims-price-list',
        label: 'Price List Management',
        icon: 'price_check',
        to: { name: 'ClaimsPriceListManagement' },
        moduleKey: 'price_list',
      },
      {
        id: 'claims-icd10',
        label: 'ICD-10 DRG Mapping',
        icon: 'medical_information',
        to: { name: 'ClaimsIcd10DrgMapping' },
        moduleKey: 'icd10_mapping',
      },
    ],
  },
];

/** Flat list of all navigable items (for favorites lookup / command palette). */
export function flattenNavItems(groups) {
  return groups.flatMap((g) => g.items.map((item) => ({ ...item, group: g.label })));
}
