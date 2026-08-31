import axios from 'axios';

// API_BASE_URL comes from frontend/.env (loaded in quasar.config.js → build.env).
// Example: API_BASE_URL=http://10.10.16.40:8000/api
const getApiBaseUrl = () => {
  const configured = String(process.env.API_BASE_URL || '').trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  // Fallbacks only if .env / build.env was not set
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  if (['9000', '9001', '3000'].includes(window.location.port)) {
    return `${protocol}//${hostname}:8000/api`;
  }
  return 'https://app.aquacy.me/api';
};

const API_BASE_URL = getApiBaseUrl();

export { getApiBaseUrl, API_BASE_URL };

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // When sending FormData, do not set Content-Type so the browser sets multipart/form-data with boundary
    if (config.data && typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Only redirect if not already on login page to avoid redirect loops
      if (window.location.pathname === '/login') {
        return Promise.reject(error);
      }

      // Check if token was just set (within last 5 seconds) - might be clock sync issue
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          // Try to decode token to check age
          const parts = token.split('.');
          if (parts.length === 3) {
            const base64Url = parts[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
              atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
            );
            const payload = JSON.parse(jsonPayload);
            
            // Check if token was issued very recently (within last 5 seconds)
            if (payload.iat) {
              const tokenAge = Date.now() - (payload.iat * 1000);
              if (tokenAge < 5000) {
                // Token is very new, might be clock sync issue - don't logout immediately
                console.warn('401 error but token is very new (age:', tokenAge, 'ms), might be clock sync - not logging out');
                return Promise.reject(error);
              }
            }
          }
        } catch (e) {
          // If we can't decode, proceed with refresh attempt
          console.warn('Could not decode token to check age:', e);
        }
      }

      // If we're already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch(err => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        const response = await api.post('/auth/refresh');
        const { access_token } = response.data;
        
        // Update token in storage
        localStorage.setItem('auth_token', access_token);
        
        // Update axios default header
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        
        // Process queued requests
        processQueue(null, access_token);
        
        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - logout user
        processQueue(refreshError, null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        
        // Use a small delay to allow any ongoing operations to complete
        setTimeout(() => {
          window.location.href = '/login';
        }, 100);
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authAPI = {
  login: (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getMe: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) => 
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  refreshToken: () => api.post('/auth/refresh'),
};

// Patient endpoints
export const patientsAPI = {
  create: (data) => api.post('/patients/', data),
  getRegistrationConfig: () => api.get('/patients/registration-config'),
  validateRegistration: (data) => api.post('/patients/validate-registration', data),
  get: (patientId) => api.get(`/patients/${patientId}`),
  getByCard: (cardNumber) => api.get(`/patients/card/${encodeURIComponent(cardNumber)}`),
  searchByName: (name) => api.get(`/patients/search/name?name=${encodeURIComponent(name)}`),
  searchByCcc: (cccNumber) => api.get(`/patients/search/ccc?ccc_number=${encodeURIComponent(cccNumber)}`),
  searchByContact: (contactNumber) => api.get(`/patients/search/contact?contact_number=${encodeURIComponent(contactNumber)}`),
  update: (patientId, data) => api.put(`/patients/${patientId}`, data),
  import: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/patients/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  lookupNhia: (insuranceId, otac = null) =>
    api.post('/patients/nhia/lookup', { insurance_id: insuranceId, otac: otac || null }),
  generateCcc: (patientId, otac = null) =>
    api.post(`/patients/${patientId}/generate-ccc`, { otac: otac || null }),
  createEncounter: (patientId, serviceType, cccNumber = null, procedureGDrgCode = null, procedureName = null) => {
    const params = new URLSearchParams({ service_type: serviceType });
    if (cccNumber) {
      params.append('ccc_number', cccNumber);
    }
    if (procedureGDrgCode) {
      params.append('procedure_g_drg_code', procedureGDrgCode);
    }
    if (procedureName) {
      params.append('procedure_name', procedureName);
    }
    return api.post(`/patients/${patientId}/encounter?${params.toString()}`);
  },
};

// Encounter endpoints
export const encountersAPI = {
  get: (encounterId) => api.get(`/encounters/${encounterId}`),
  update: (encounterId, data) => api.put(`/encounters/${encounterId}`, data),
  updateStatus: (encounterId, newStatus) => 
    api.put(`/encounters/${encounterId}/status?new_status=${newStatus}`),
  delete: (encounterId) => api.delete(`/encounters/${encounterId}`),
  getPatientEncounters: (patientId) => api.get(`/encounters/patient/${patientId}`),
  getByDate: (date) => api.get(`/encounters/date/${date}`),
  getBillTotal: (encounterId) => api.get(`/encounters/${encounterId}/bill-total`),
};

// Companion (copayment) visits - external card/visit from government system
export const companionVisitsAPI = {
  create: (data, options = {}) =>
    api.post('/companion-visits/', data, { params: { ignore_outstanding: Boolean(options.ignore_outstanding) } }),
  createFromGovernmentExport: (file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/companion-visits/create-from-government-export', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { ignore_outstanding: Boolean(options.ignore_outstanding) },
    });
  },
  checkOutstanding: (cardNumber, excludeVisitNumber = null) =>
    api.get('/companion-visits/outstanding-check', {
      params: {
        card_number: cardNumber,
        ...(excludeVisitNumber ? { exclude_visit_number: excludeVisitNumber } : {}),
      },
    }),
  list: (params = {}) => api.get('/companion-visits/', { params }),
  get: (visitId) => api.get(`/companion-visits/${visitId}`),
  update: (visitId, data) => api.patch(`/companion-visits/${visitId}`, data),
  delete: (visitId) => api.delete(`/companion-visits/${visitId}`),
  close: (visitId) => api.post(`/companion-visits/${visitId}/close`),
  reopen: (visitId, data) => api.post(`/companion-visits/${visitId}/reopen`, data),
  requestUndertaking: (visitId, data = {}) => api.post(`/companion-visits/${visitId}/undertaking/request`, data),
  updateUndertaking: (visitId, data) => api.patch(`/companion-visits/${visitId}/undertaking`, data),
  cancelUndertaking: (visitId) => api.post(`/companion-visits/${visitId}/undertaking/cancel`),
  approveUndertaking: (visitId) => api.post(`/companion-visits/${visitId}/undertaking/approve`),
  rejectUndertaking: (visitId, data) => api.post(`/companion-visits/${visitId}/undertaking/reject`, data),
  revertRejectedUndertaking: (visitId) => api.post(`/companion-visits/${visitId}/undertaking/revert-reject`),
  unapproveUndertaking: (visitId, data) => api.post(`/companion-visits/${visitId}/undertaking/unapprove`, data),
  deleteUndertaking: (visitId) => api.post(`/companion-visits/${visitId}/undertaking/delete`),
  getItems: (visitId, category = null) =>
    api.get(`/companion-visits/${visitId}/items`, { params: category ? { category } : {} }),
  addItem: (visitId, data) => api.post(`/companion-visits/${visitId}/items`, data),
  updateItem: (visitId, itemId, data) => api.patch(`/companion-visits/${visitId}/items/${itemId}`, data),
  deleteItem: (visitId, itemId) => api.delete(`/companion-visits/${visitId}/items/${itemId}`),
  markItemsPaid: (visitId, data) => api.post(`/companion-visits/${visitId}/items/mark-paid`, data),
  refundItems: (visitId, itemIds) =>
    api.post(`/companion-visits/${visitId}/items/refund`, { item_ids: itemIds }),
  getActiveInvestigations: () => api.get('/companion-visits/active-investigations'),
  addActiveInvestigation: (data) => api.post('/companion-visits/active-investigations', data),
  removeActiveInvestigation: (gDrgCode) =>
    api.delete(`/companion-visits/active-investigations/${encodeURIComponent(gDrgCode)}`),
  getActiveScans: () => api.get('/companion-visits/active-scans'),
  addActiveScan: (data) => api.post('/companion-visits/active-scans', data),
  removeActiveScan: (gDrgCode) =>
    api.delete(`/companion-visits/active-scans/${encodeURIComponent(gDrgCode)}`),
  getActiveXrays: () => api.get('/companion-visits/active-xrays'),
  addActiveXray: (data) => api.post('/companion-visits/active-xrays', data),
  removeActiveXray: (gDrgCode) =>
    api.delete(`/companion-visits/active-xrays/${encodeURIComponent(gDrgCode)}`),
  getActiveDaySurgeries: () => api.get('/companion-visits/active-day-surgeries'),
  addActiveDaySurgery: (data) => api.post('/companion-visits/active-day-surgeries', data),
  removeActiveDaySurgery: (gDrgCode) =>
    api.delete(`/companion-visits/active-day-surgeries/${encodeURIComponent(gDrgCode)}`),
  getActiveMajorSurgeries: () => api.get('/companion-visits/active-major-surgeries'),
  addActiveMajorSurgery: (data) => api.post('/companion-visits/active-major-surgeries', data),
  removeActiveMajorSurgery: (gDrgCode) =>
    api.delete(`/companion-visits/active-major-surgeries/${encodeURIComponent(gDrgCode)}`),
  getActiveDressings: () => api.get('/companion-visits/active-dressings'),
  addActiveDressing: (data) => api.post('/companion-visits/active-dressings', data),
  removeActiveDressing: (gDrgCode) =>
    api.delete(`/companion-visits/active-dressings/${encodeURIComponent(gDrgCode)}`),
  getActiveOxygens: () => api.get('/companion-visits/active-oxygens'),
  addActiveOxygen: (data) => api.post('/companion-visits/active-oxygens', data),
  removeActiveOxygen: (gDrgCode) =>
    api.delete(`/companion-visits/active-oxygens/${encodeURIComponent(gDrgCode)}`),
  parseDrugsPdf: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/companion-visits/parse-drugs-pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  parseDrugsExcel: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/companion-visits/parse-drugs-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  reconcileOpdGovernment: (visitId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/companion-visits/${visitId}/reconcile-opd-government`, formData);
  },
  reconcileOpdGovernmentSaved: (visitId) => api.get(`/companion-visits/${visitId}/government-opd-export/reconcile`),
  clearSavedOpdGovernmentExport: (visitId) => api.delete(`/companion-visits/${visitId}/government-opd-export`),

  reconcileIpdGovernment: (visitId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/companion-visits/${visitId}/reconcile-ipd-government`, formData);
  },
  reconcileIpdGovernmentSaved: (visitId) => api.get(`/companion-visits/${visitId}/government-ipd-export/reconcile`),
  clearSavedIpdGovernmentExport: (visitId) => api.delete(`/companion-visits/${visitId}/government-ipd-export`),
  addMissingFromOpdExport: (visitId, category, lines) =>
    api.post(`/companion-visits/${visitId}/items/add-missing-from-opd-export`, { category, lines }),
  getPriceSuggestions: (visitId, category, q, limit = 15) =>
    api.get(`/companion-visits/${visitId}/price-suggestions`, { params: { category, q, limit } }),
  confirmFromOpdExportLine: (visitId, description, quantity) =>
    api.post(`/companion-visits/${visitId}/items/confirm-from-opd-export-line`, { description, quantity }),
  cancelItem: (visitId, itemId, reason) =>
    api.post(`/companion-visits/${visitId}/items/${itemId}/cancel`, { reason }),
  /** Aggregated ward stock lines for a department (for picking items to debit). */
  getDepartmentStock: (ward) =>
    api.get('/companion-visits/ward-stock', { params: { ward } }),
  listInventoryDebits: (visitId) => api.get(`/companion-visits/${visitId}/inventory-debits`),
  createInventoryDebit: (visitId, data) => api.post(`/companion-visits/${visitId}/inventory-debits`, data),
  batchInventoryDebits: (visitId, items) =>
    api.post(`/companion-visits/${visitId}/inventory-debits/batch`, { items }),
  updateInventoryDebit: (visitId, debitId, data) =>
    api.patch(`/companion-visits/${visitId}/inventory-debits/${debitId}`, data),
  deleteInventoryDebit: (visitId, debitId) =>
    api.delete(`/companion-visits/${visitId}/inventory-debits/${debitId}`),
  chargeInventoryDebitToBill: (visitId, debitId) =>
    api.post(`/companion-visits/${visitId}/inventory-debits/${debitId}/charge-to-bill`),
};

// Management: transactions and user list for filters (Management, Admin only)
export const managementAPI = {
  getTransactions: (params = {}) => api.get('/management/transactions', { params }),
  getPendingPayments: (params = {}) => api.get('/management/pending-payments', { params }),
  getUsers: () => api.get('/management/users'),
};

// Vitals endpoints
export const vitalsAPI = {
  create: (data) => api.post('/vitals/', data),
  getByEncounter: (encounterId) => api.get(`/vitals/encounter/${encounterId}`),
  getToday: (cardNumber = null) => {
    const params = cardNumber ? { card_number: cardNumber } : {};
    return api.get('/vitals/', { params });
  },
  getByDate: (date, cardNumber = null) => {
    const params = cardNumber ? { card_number: cardNumber } : {};
    return api.get(`/vitals/date/${date}`, { params });
  },
};

// Consultation endpoints
export const consultationAPI = {
  createDiagnosis: (data) => api.post('/consultation/diagnosis', data),
  updateDiagnosis: (diagnosisId, data) => api.put(`/consultation/diagnosis/${diagnosisId}`, data),
  deleteDiagnosis: (diagnosisId) => api.delete(`/consultation/diagnosis/${diagnosisId}`),
  getDiagnoses: (encounterId) => api.get(`/consultation/diagnosis/encounter/${encounterId}`),
  createPrescription: (data) => api.post('/consultation/prescription', data),
  createDirectPrescription: (data) => api.post('/consultation/prescription/direct', data),
  updatePrescription: (prescriptionId, data) => api.put(`/consultation/prescription/${prescriptionId}`, data),
  deletePrescription: (prescriptionId) => api.delete(`/consultation/prescription/${prescriptionId}`),
  getPrescriptions: (encounterId) => api.get(`/consultation/prescription/encounter/${encounterId}`),
  createInvestigation: (data) => api.post('/consultation/investigation', data),
  updateInvestigation: (investigationId, data) => api.put(`/consultation/investigation/${investigationId}`, data),
  deleteInvestigation: (investigationId) => api.delete(`/consultation/investigation/${investigationId}`),
  getInvestigations: (encounterId) => api.get(`/consultation/investigation/encounter/${encounterId}`),
  confirmInvestigation: (investigationId) => 
    api.put(`/consultation/investigation/${investigationId}/confirm`),
  bulkConfirmInvestigations: (investigationIds) => 
    api.put('/consultation/investigations/bulk-confirm', { investigation_ids: investigationIds }),
  cancelInvestigation: (investigationId, data) => 
    api.put(`/consultation/investigation/${investigationId}/cancel`, data),
  getConsultationNotes: (encounterId) => api.get(`/consultation/notes/encounter/${encounterId}`),
  saveConsultationNotes: (data) => api.post('/consultation/notes', data),
  // Doctor note entries endpoints
  getDoctorNoteEntries: (encounterId) => api.get(`/consultation/encounters/${encounterId}/doctor-notes`),
  getPatientDoctorNotes: (patientId, excludeEncounterId = null) => {
    const params = excludeEncounterId ? { exclude_encounter_id: excludeEncounterId } : {};
    return api.get(`/consultation/patients/${patientId}/doctor-notes`, { params });
  },
  createDoctorNoteEntry: (encounterId, data) => api.post(`/consultation/encounters/${encounterId}/doctor-notes`, data),
  updateDoctorNoteEntry: (noteId, data) => api.put(`/consultation/doctor-notes/${noteId}`, data),
  // Consultation template endpoints
  getConsultationTemplates: (includeShared = true) => api.get('/consultation/consultation-templates', { params: { include_shared: includeShared } }),
  getConsultationTemplate: (templateId) => api.get(`/consultation/consultation-templates/${templateId}`),
  createConsultationTemplate: (data) => api.post('/consultation/consultation-templates', data),
  updateConsultationTemplate: (templateId, data) => api.put(`/consultation/consultation-templates/${templateId}`, data),
  deleteConsultationTemplate: (templateId) => api.delete(`/consultation/consultation-templates/${templateId}`),
  getPrescriptionsByPatientCard: (cardNumber, encounterId) => 
    api.get(`/consultation/prescription/patient/${cardNumber}/encounter/${encounterId}`),
  confirmPrescription: (prescriptionId, data = null) => {
    // Send empty object if data is null to ensure request body is sent
    return api.put(`/consultation/prescription/${prescriptionId}/confirm`, data || {});
  },
  unconfirmPrescription: (prescriptionId) => {
    return api.put(`/consultation/prescription/${prescriptionId}/unconfirm`);
  },
  dispensePrescription: (prescriptionId, data = null) => 
    api.put(`/consultation/prescription/${prescriptionId}/dispense`, data),
  returnPrescription: (prescriptionId) => 
    api.put(`/consultation/prescription/${prescriptionId}/return`),
  getDispensedPrescriptions: (encounterId) => 
    api.get(`/consultation/prescription/encounter/${encounterId}/dispensed`),
  // Inpatient prescription endpoints
  getWardAdmissionsByPatientCard: (cardNumber, includeDischarged = false) => 
    api.get(`/consultation/ward-admissions/patient/${cardNumber}`, { params: { include_discharged: includeDischarged } }),
  getInpatientPrescriptionsByPatientCard: (cardNumber) => 
    api.get(`/consultation/inpatient-prescription/patient/${cardNumber}`),
  getInpatientPrescriptionsByWardAdmission: (wardAdmissionId) => 
    api.get(`/consultation/ward-admissions/${wardAdmissionId}/prescriptions/all`),
  getAllInpatientDiagnoses: (wardAdmissionId) => 
    api.get(`/consultation/ward-admissions/${wardAdmissionId}/diagnoses/all`),
  confirmInpatientPrescription: (prescriptionId, data = null) => 
    api.put(`/consultation/inpatient-prescription/${prescriptionId}/confirm`, data || {}),
  unconfirmInpatientPrescription: (prescriptionId) => 
    api.put(`/consultation/inpatient-prescription/${prescriptionId}/unconfirm`),
  dispenseInpatientPrescription: (prescriptionId, data = null) => 
    api.put(`/consultation/inpatient-prescription/${prescriptionId}/dispense`, data),
  returnInpatientPrescription: (prescriptionId) => 
    api.put(`/consultation/inpatient-prescription/${prescriptionId}/return`),
  updateInpatientPrescription: (prescriptionId, data) => 
    api.put(`/consultation/inpatient-prescription/${prescriptionId}`, data),
  getInvestigationsByPatientCard: (cardNumber, encounterId, investigationType = null) => {
    const url = `/consultation/investigation/patient/${cardNumber}/encounter/${encounterId}`;
    const params = investigationType ? { investigation_type: investigationType } : {};
    return api.get(url, { params });
  },
  getInvestigationsByType: (investigationType, filters = {}) => {
    const url = `/consultation/investigation/list/${investigationType}`;
    return api.get(url, { params: filters });
  },
  getInpatientInvestigationsByType: (investigationType, filters = {}) => {
    const url = `/consultation/inpatient-investigations/by-type`;
    return api.get(url, { params: { investigation_type: investigationType, ...filters } });
  },
  confirmInpatientInvestigation: (investigationId, data = {}) => {
    return api.put(`/consultation/inpatient-investigation/${investigationId}/confirm`, data);
  },
  revertInpatientInvestigationStatus: (investigationId) => 
    api.put(`/consultation/inpatient-investigation/${investigationId}/revert-status`),
  revertInpatientInvestigationToRequested: (investigationId, reason) => 
    api.put(`/consultation/inpatient-investigation/${investigationId}/revert-to-requested`, { reason }),
  updateInpatientInvestigationDetails: (investigationId, data) =>
    api.put(`/consultation/inpatient-investigation/${investigationId}/update-details`, data),
  bulkConfirmInpatientInvestigations: (investigationIds, addToIpdBill = true) => 
    api.put('/consultation/inpatient-investigations/bulk-confirm', { 
      investigation_ids: investigationIds,
      add_to_ipd_bill: addToIpdBill
    }),
  getInvestigation: (investigationId) => {
    return api.get(`/consultation/investigation/${investigationId}`);
  },
  getInpatientInvestigation: (investigationId) => {
    return api.get(`/consultation/inpatient-investigation/${investigationId}`);
  },
  updateInvestigationDetails: (investigationId, data) => 
    api.put(`/consultation/investigation/${investigationId}/update-details`, data),
  revertInvestigationStatus: (investigationId) => 
    api.put(`/consultation/investigation/${investigationId}/revert-status`),
  revertInvestigationToRequested: (investigationId, reason) => 
    api.put(`/consultation/investigation/${investigationId}/revert-to-requested`, { reason }),
  getLabResult: (investigationId) => 
    api.get(`/consultation/lab-result/investigation/${investigationId}`),
  saveSampleId: (investigationId, sampleId) =>
    api.post('/consultation/lab-result/sample-id', {
      investigation_id: investigationId,
      sample_no: sampleId,
    }),
  createLabResult: (formData) => 
    api.post('/consultation/lab-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadLabResultAttachment: (investigationId, view = false) => 
    api.get(`/consultation/lab-result/${investigationId}/download`, {
      params: { view: view },
      responseType: 'blob',
    }),
  deleteLabResultAttachment: (investigationId) => 
    api.delete(`/consultation/lab-result/${investigationId}/attachment`),
  getLabResultTemplateForInvestigation: (investigationId) =>
    api.get(`/consultation/lab-result/investigation/${investigationId}/template`),
  getScanResult: (investigationId) => 
    api.get(`/consultation/scan-result/investigation/${investigationId}`),
  createScanResult: (formData) => 
    api.post('/consultation/scan-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadScanResultAttachment: (investigationId, attachmentPath, view = false) => {
    const url = `/consultation/scan-result/${investigationId}/download`;
    const params = {};
    if (attachmentPath) params.attachment_path = attachmentPath;
    if (view) params.view = true;
    return api.get(url, {
      params,
      responseType: 'blob',
    });
  },
  deleteScanResultAttachment: (investigationId, attachmentPath) => {
    const url = `/consultation/scan-result/${investigationId}/attachment`;
    return api.delete(url, {
      params: { attachment_path: attachmentPath },
    });
  },
  getXrayResult: (investigationId) => 
    api.get(`/consultation/xray-result/investigation/${investigationId}`),
  createXrayResult: (formData) => 
    api.post('/consultation/xray-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadXrayResultAttachment: (investigationId, attachmentPath, view = false) => {
    const url = `/consultation/xray-result/${investigationId}/download`;
    const params = {};
    if (attachmentPath) params.attachment_path = attachmentPath;
    if (view) params.view = true;
    return api.get(url, {
      params,
      responseType: 'blob',
    });
  },
  deleteXrayResultAttachment: (investigationId, attachmentPath) => {
    const url = `/consultation/xray-result/${investigationId}/attachment`;
    return api.delete(url, {
      params: { attachment_path: attachmentPath },
    });
  },
  getAdmissionRecommendations: () => api.get('/consultation/admissions'),
  confirmAdmission: (admissionId, formData) => api.put(`/consultation/admissions/${admissionId}/confirm`, formData),
  revertAdmissionConfirmation: (admissionId) => api.put(`/consultation/admissions/${admissionId}/revert-confirmation`),
  cancelAdmission: (admissionId, reason) => api.put(`/consultation/admissions/${admissionId}/cancel`, { reason }),
  getWardAdmissions: (ward, includeDischarged = false) => {
    const params = {};
    if (ward) params.ward = ward;
    if (includeDischarged) params.include_discharged = true;
    return api.get('/consultation/ward-admissions', { params });
  },
  getWardAdmission: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}`),
    partialDischargePatient: (wardAdmissionId, dischargeData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/partial-discharge`, dischargeData),
    revertPartialDischarge: (wardAdmissionId) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/revert-partial-discharge`),
    dischargePatient: (wardAdmissionId, dischargeData) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/discharge`, dischargeData),
    cancelWardAdmission: (wardAdmissionId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}`),
    updateAdmissionNotes: (wardAdmissionId, notes) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/admission-notes`, { notes }),
    // Nurse Notes
    createNurseNote: (wardAdmissionId, notes) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/nurse-notes`, { notes }),
    getNurseNotes: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/nurse-notes`),
    toggleNurseNoteStrikethrough: (wardAdmissionId, noteId) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/nurse-notes/${noteId}/strikethrough`),
    // Nurse Mid Documentation
    createNurseMidDocumentation: (wardAdmissionId, data) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/nurse-mid-documentations`, data),
    getNurseMidDocumentations: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/nurse-mid-documentations`),
    updateNurseMidDocumentation: (wardAdmissionId, documentationId, data) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/nurse-mid-documentations/${documentationId}`, data),
    // Inpatient Vitals
    createInpatientVital: (wardAdmissionId, vitalData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/vitals`, vitalData),
    getInpatientVitals: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/vitals`),
    updateInpatientVital: (wardAdmissionId, vitalId, vitalData) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/vitals/${vitalId}`, vitalData),
    // Inpatient Clinical Reviews
    createInpatientClinicalReview: (wardAdmissionId, reviewData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews`, reviewData),
    getInpatientClinicalReviews: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews`),
  getInpatientClinicalReview: (clinicalReviewId) => api.get(`/consultation/clinical-reviews/${clinicalReviewId}`),
    updateInpatientClinicalReview: (wardAdmissionId, clinicalReviewId, reviewData) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}`, reviewData),
    deleteInpatientClinicalReview: (wardAdmissionId, clinicalReviewId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}`),
    // Inpatient Diagnoses
    createInpatientDiagnosis: (wardAdmissionId, clinicalReviewId, diagnosisData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/diagnoses`, diagnosisData),
    getInpatientDiagnoses: (wardAdmissionId, clinicalReviewId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/diagnoses`),
    deleteInpatientDiagnosis: (wardAdmissionId, clinicalReviewId, diagnosisId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/diagnoses/${diagnosisId}`),
    // Inpatient Prescriptions
    createInpatientPrescription: (wardAdmissionId, clinicalReviewId, prescriptionData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/prescriptions`, prescriptionData),
    getInpatientPrescriptions: (wardAdmissionId, clinicalReviewId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/prescriptions`),
    deleteInpatientPrescription: (wardAdmissionId, clinicalReviewId, prescriptionId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/prescriptions/${prescriptionId}`),
    getAllWardAdmissionPrescriptions: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/prescriptions`),
    // Treatment Sheet
    createTreatmentAdministration: (wardAdmissionId, administrationData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/treatment-sheet/administrations`, administrationData),
    getTreatmentAdministrations: (wardAdmissionId, prescriptionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/treatment-sheet/administrations${prescriptionId ? `?prescription_id=${prescriptionId}` : ''}`),
    deleteTreatmentAdministration: (wardAdmissionId, administrationId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/treatment-sheet/administrations/${administrationId}`),
    // Inpatient Investigations
    createInpatientInvestigation: (wardAdmissionId, clinicalReviewId, investigationData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/investigations`, investigationData),
    getInpatientInvestigations: (wardAdmissionId, clinicalReviewId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/investigations`),
    getAllInpatientInvestigations: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/investigations/all`),
    deleteInpatientInvestigation: (wardAdmissionId, clinicalReviewId, investigationId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/clinical-reviews/${clinicalReviewId}/investigations/${investigationId}`),
    // Inpatient Surgeries
    createInpatientSurgery: (wardAdmissionId, surgeryData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/surgeries`, surgeryData),
    getInpatientSurgeries: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/surgeries`),
    getInpatientSurgery: (wardAdmissionId, surgeryId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/surgeries/${surgeryId}`),
    updateInpatientSurgery: (wardAdmissionId, surgeryId, surgeryData) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/surgeries/${surgeryId}`, surgeryData),
    deleteInpatientSurgery: (wardAdmissionId, surgeryId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/surgeries/${surgeryId}`),
    getSurgeriesCalendar: (date = null, startDate = null, endDate = null) => {
      const params = {};
      if (startDate && endDate) {
        params.start_date = startDate;
        params.end_date = endDate;
      } else if (date) {
        params.date = date;
      }
      return api.get('/consultation/surgeries/calendar', { params });
    },
    updateSurgeryAnaesthetistInfo: (surgeryId, anaesthetistData) => api.put(`/consultation/surgeries/${surgeryId}/anaesthetist-info`, anaesthetistData),
    // Additional Services (Admin-defined)
    createAdditionalService: (serviceData) => api.post('/consultation/additional-services', serviceData),
    getAdditionalServices: (activeOnly = false) => api.get(`/consultation/additional-services?active_only=${activeOnly}`),
    getAdditionalService: (serviceId) => api.get(`/consultation/additional-services/${serviceId}`),
    updateAdditionalService: (serviceId, serviceData) => api.put(`/consultation/additional-services/${serviceId}`, serviceData),
    deleteAdditionalService: (serviceId) => api.delete(`/consultation/additional-services/${serviceId}`),
    // Inpatient Additional Service Usage
    startAdditionalService: (wardAdmissionId, serviceData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/additional-services`, serviceData),
    getInpatientAdditionalServices: (wardAdmissionId, activeOnly = false) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/additional-services?active_only=${activeOnly}`),
    stopAdditionalService: (wardAdmissionId, serviceUsageId, stopData) => api.put(`/consultation/ward-admissions/${wardAdmissionId}/additional-services/${serviceUsageId}/stop`, stopData),
    // Inpatient Inventory Debits
    createInpatientInventoryDebit: (wardAdmissionId, debitData) => api.post(`/consultation/ward-admissions/${wardAdmissionId}/inventory-debits`, debitData),
    getInpatientInventoryDebits: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/inventory-debits`),
    deleteInpatientInventoryDebit: (wardAdmissionId, debitId) => api.delete(`/consultation/ward-admissions/${wardAdmissionId}/inventory-debits/${debitId}`),
    getAllInventoryDebits: (params = {}) => api.get('/consultation/inventory-debits', { params }),
    releaseInventoryDebit: (debitId, params = {}) =>
      api.put(`/consultation/inventory-debits/${debitId}/release`, null, { params }),
    // Encounter Inventory Debits (for OPD)
    createEncounterInventoryDebit: (encounterId, debitData) => api.post(`/consultation/encounters/${encounterId}/inventory-debits`, debitData),
    getEncounterInventoryDebits: (encounterId) => api.get(`/consultation/encounters/${encounterId}/inventory-debits`),
    deleteEncounterInventoryDebit: (encounterId, debitId) => api.delete(`/consultation/encounters/${encounterId}/inventory-debits/${debitId}`),
    // Ward Admission Transfers
    getWardAdmissionTransfers: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}/transfers`),
    // Direct Admission
    createDirectAdmission: (admissionData) => api.post('/consultation/admissions/direct', admissionData),
    // Daily Ward State
    getDailyWardState: (ward, date) => {
      const params = {};
      if (date) params.date = date;
      return api.get(`/consultation/ward-admissions/daily-state/${encodeURIComponent(ward)}`, { params });
    },
    // Transfer Patient
    transferPatient: (transferData) => api.post('/consultation/ward-admissions/transfer', transferData),
    // Pending Transfers
    getPendingTransfers: (ward) => {
      const params = ward ? { ward } : {};
      return api.get('/consultation/ward-admissions/pending-transfers', { params });
    },
    acceptTransfer: (transferId, bedId) => api.post(`/consultation/ward-admissions/transfers/${transferId}/accept`, { bed_id: bedId }),
    rejectTransfer: (transferId, reason) => api.post(`/consultation/ward-admissions/transfers/${transferId}/reject`, { rejection_reason: reason }),
    // Blood Transfusion Types (Admin)
    createBloodTransfusionType: (typeData) => api.post('/consultation/blood-transfusion-types', typeData),
    getBloodTransfusionTypes: (activeOnly = false) => api.get(`/consultation/blood-transfusion-types?active_only=${activeOnly}`),
    getBloodTransfusionType: (typeId) => api.get(`/consultation/blood-transfusion-types/${typeId}`),
    updateBloodTransfusionType: (typeId, typeData) => api.put(`/consultation/blood-transfusion-types/${typeId}`, typeData),
    deleteBloodTransfusionType: (typeId) => api.delete(`/consultation/blood-transfusion-types/${typeId}`),
    // Blood Transfusion Requests
    createBloodTransfusionRequest: (requestData) => api.post('/consultation/blood-transfusion-requests', requestData),
    updateBloodTransfusionRequest: (requestId, updateData) => api.put(`/consultation/blood-transfusion-requests/${requestId}`, updateData),
    getBloodTransfusionRequests: (status = null, ward = null) => {
      const params = {};
      if (status) params.status = status;
      if (ward) params.ward = ward;
      return api.get('/consultation/blood-transfusion-requests', { params });
    },
    acceptBloodTransfusionRequest: (requestId) => api.post(`/consultation/blood-transfusion-requests/${requestId}/accept`),
    fulfillBloodTransfusionRequest: (requestId) => api.post(`/consultation/blood-transfusion-requests/${requestId}/fulfill`),
    cancelBloodTransfusionRequest: (requestId, reason) => api.post(`/consultation/blood-transfusion-requests/${requestId}/cancel`, { cancellation_reason: reason }),
    deleteBloodTransfusionRequest: (requestId) => api.delete(`/consultation/blood-transfusion-requests/${requestId}`),
    returnBloodTransfusionRequest: (requestId) => api.post(`/consultation/blood-transfusion-requests/${requestId}/return`),
    addProcessingFeeToBloodRequest: (requestId, serviceData) => api.post(`/consultation/blood-transfusion-requests/${requestId}/add-processing-fee`, serviceData),
  getWards: () => api.get('/consultation/wards'),
  getBeds: (ward, availableOnly = false) => {
    const params = {};
    if (ward) params.ward = ward;
    if (availableOnly) params.available_only = true;
    return api.get('/consultation/beds', { params });
  },
  createBed: (bedData) => api.post('/consultation/beds', bedData),
  updateBed: (bedId, bedData) => api.put(`/consultation/beds/${bedId}`, bedData),
  deleteBed: (bedId) => api.delete(`/consultation/beds/${bedId}`),
  getDoctors: () => api.get('/consultation/doctors'),
};

// Billing endpoints
export const billingAPI = {
  createBill: (data) => api.post('/billing/', data),
  createReceipt: (data) => api.post('/billing/receipt', data),
  getEncounterBills: (encounterId) => api.get(`/billing/encounter/${encounterId}`),
  getBillDetails: (billId) => api.get(`/billing/bill/${billId}`),
  autoCalculateBillItems: (encounterId) => api.get(`/billing/encounter/${encounterId}/auto-calculate`),
  refundReceipt: (receiptId) => api.post(`/billing/receipt/${receiptId}/refund`),
  addManualReceiptToBillItem: (billItemId, data) => api.post(`/billing/bill-item/${billItemId}/receipt`, data),
  deleteReceiptItem: (receiptItemId) => api.delete(`/billing/receipt-item/${receiptItemId}`),
  deleteBill: (billId) => api.delete(`/billing/bill/${billId}`),
  updateBill: (billId, data) => api.put(`/billing/bill/${billId}`, data),
  updateBillItem: (billItemId, data) => api.put(`/billing/bill-item/${billItemId}`, data),
  getOpdCccForEncounter: (encounterId) => api.get(`/billing/encounter/${encounterId}/opd-ccc`),
  recalculateBillingWithInsurance: (encounterId, data) => api.post(`/billing/encounter/${encounterId}/recalculate-insurance`, data),
  /** Parse government IPD (in-patient) invoice file (.xls/.xlsx). For companion app IPD check. */
  parseIpdInvoice: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/billing/parse-ipd-invoice', formData);
  },
};

// Price list endpoints
export const priceListAPI = {
  upload: (fileType, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/price-list/upload/${fileType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  exportCSV: (fileType) => {
    return api.get(`/price-list/export/${fileType}/csv`, { responseType: 'blob' });
  },
  exportProductCSV: () => {
    return api.get('/price-list/export/product/csv', {
      responseType: 'blob',
    });
  },
  createItem: (fileType, data) => api.post(`/price-list/item/${fileType}`, data),
  uploadIcd10Mapping: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/price-list/upload/icd10-mapping', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  searchIcd10: (searchTerm, limit = 50) => {
    const params = { limit };
    if (searchTerm) {
      params.search_term = searchTerm;
    }
    return api.get('/price-list/icd10/search', { params });
  },
  searchPriceItems: (searchTerm = null, serviceType = null, fileType = null, statusFilter = 'active', subCategory2 = null, insuranceCovered = null) => {
    const params = {};
    if (searchTerm) params.search_term = searchTerm;
    if (serviceType) params.service_type = serviceType;
    if (fileType) params.file_type = fileType;
    if (statusFilter) params.status_filter = statusFilter;
    if (subCategory2) params.sub_category_2 = subCategory2;
    if (insuranceCovered) params.insurance_covered = insuranceCovered;
    return api.get('/price-list/search', { params });
  },
  getDrgCodesFromIcd10: (icd10Code) => {
    return api.get(`/price-list/icd10/${icd10Code}/drg-codes`);
  },
  getIcd10CodesFromDrg: (drgCode) => {
    if (!drgCode || !String(drgCode).trim()) return Promise.resolve({ data: [] });
    return api.get(`/price-list/drg-codes/${encodeURIComponent(drgCode.trim())}/icd10-codes`);
  },
  // ICD-10 DRG Mapping Management
  getIcd10DrgMappings: (skip = 0, limit = 100, search = null, isActive = null, unmappedOnly = false) => {
    const params = { skip, limit };
    if (search) {
      params.search = search;
    }
    if (isActive !== null) {
      params.is_active = isActive;
    }
    if (unmappedOnly) {
      params.unmapped_only = true;
    }
    return api.get('/price-list/icd10-mappings', { params });
  },
  createIcd10DrgMapping: (data) => {
    return api.post('/price-list/icd10-mappings', data);
  },
  updateIcd10DrgMapping: (mappingId, data) => {
    return api.put(`/price-list/icd10-mappings/${mappingId}`, data);
  },
  deleteIcd10DrgMapping: (mappingId) => {
    return api.delete(`/price-list/icd10-mappings/${mappingId}`);
  },
  exportIcd10DrgMapping: (params = {}) => {
    return api.get('/price-list/export/icd10-mapping/csv', {
      params,
      responseType: 'blob',
    });
  },
  searchDrgCodes: (searchTerm, limit = 50) => {
    const params = { limit };
    if (searchTerm) {
      params.search_term = searchTerm;
    }
    return api.get('/price-list/drg-codes/search', { params });
  },
  search: (searchTerm, serviceType, fileType, statusFilter = 'active', subCategory2 = null, insuranceCovered = null) => 
    api.get('/price-list/search', { 
      params: { 
        search_term: searchTerm || undefined,
        service_type: serviceType || undefined,
        file_type: fileType || undefined,
        status_filter: statusFilter || 'active',
        sub_category_2: subCategory2 || undefined,
        insurance_covered: insuranceCovered || undefined,
      } 
    }),
  getServiceTypes: () => api.get('/price-list/service-types'),
  getProductSubcategories: () => api.get('/price-list/product-subcategories'),
  getProceduresByServiceType: (serviceType) =>
    api.get('/price-list/procedures/by-service-type', {
      params: { service_type: serviceType }
    }),
  /** Get all surgery price list items (file type surgery) for major surgery selection. */
  getSurgeries: () => api.get('/price-list/surgeries'),
  updateItem: (fileType, id, data) => api.put(`/price-list/item/${fileType}/${id}`, data),
  bulkClear: (fileType, data) =>
    api.post(`/price-list/bulk-clear/${fileType}`, data),
};

// Claims endpoints
export const claimsAPI = {
  create: (data) => api.post('/claims/', data),
  getEligibleEncounters: (type = null, startDate = null, endDate = null, claimStatus = null, cardNumber = null, claimId = null, ccc = null, specialty = null, skip = 0, limit = 50) => {
    const params = { skip, limit };
    if (type) params.claim_type = type;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (claimStatus) params.claim_status = claimStatus;
    if (cardNumber) params.card_number = cardNumber;
    if (claimId) params.claim_id = claimId;
    if (ccc) params.ccc = ccc;
    if (specialty) params.specialty = specialty;
    return api.get('/claims/eligible-encounters', { params });
  },
  getSpecialties: (claimType = null) => {
    const params = {};
    if (claimType) params.claim_type = claimType;
    return api.get('/claims/specialties', { params });
  },
  get: (claimId) => api.get(`/claims/${claimId}`),
  getAll: () => api.get('/claims/'),
  update: (claimId, data) => api.put(`/claims/${claimId}`, data),
  updateDetailed: (claimId, data) => api.put(`/claims/${claimId}/detailed`, data),
  getEditDetails: (claimId) => api.get(`/claims/${claimId}/edit-details`),
  fetchCcc: (claimId, memberNo = null, otac = null) =>
    api.post(`/claims/${claimId}/fetch-ccc`, {
      ...(memberNo ? { member_no: memberNo } : {}),
      ...(otac ? { otac } : {}),
    }),
  convertGhanaCardToHin: (claimId, ghanaCard = null, otac = null) =>
    api.post(`/claims/${claimId}/convert-ghana-card-to-hin`, {
      ...(ghanaCard ? { ghana_card: ghanaCard } : {}),
      ...(otac ? { otac } : {}),
    }),
  fetchGhimsImportCcc: (itemId, memberNo = null, otac = null) =>
    api.post(`/claims/ghims-import/items/${itemId}/fetch-ccc`, {
      ...(memberNo ? { member_no: memberNo } : {}),
      ...(otac ? { otac } : {}),
    }),
  convertGhimsGhanaCardToHin: (itemId, ghanaCard = null, otac = null) =>
    api.post(`/claims/ghims-import/items/${itemId}/convert-ghana-card-to-hin`, {
      ...(ghanaCard ? { ghana_card: ghanaCard } : {}),
      ...(otac ? { otac } : {}),
    }),
  // Diagnosis templates (investigations + medicines presets)
  listDiagnosisTemplates: (params = {}) =>
    api.get('/claims/diagnosis-templates', { params }),
  matchDiagnosisTemplates: ({ icd10, diagnosis, gdrg } = {}) =>
    api.get('/claims/diagnosis-templates/match', {
      params: {
        ...(icd10 ? { icd10 } : {}),
        ...(diagnosis ? { diagnosis } : {}),
        ...(gdrg ? { gdrg } : {}),
      },
    }),
  getDiagnosisTemplate: (id) => api.get(`/claims/diagnosis-templates/${id}`),
  createDiagnosisTemplate: (data) => api.post('/claims/diagnosis-templates', data),
  updateDiagnosisTemplate: (id, data) => api.put(`/claims/diagnosis-templates/${id}`, data),
  deleteDiagnosisTemplate: (id) => api.delete(`/claims/diagnosis-templates/${id}`),
  finalize: (claimId) => api.put(`/claims/${claimId}/finalize`),
  vetClaim: (claimId, by, clear = false) => api.put(`/claims/${claimId}/vet`, { by, clear: !!clear }),
  reopen: (claimId) => api.put(`/claims/${claimId}/reopen`),
  regenerate: (claimId, data) => api.put(`/claims/${claimId}/regenerate`, data),
  exportSingle: (claimId) =>
    api.get(`/claims/export/${claimId}`, { responseType: 'blob', timeout: 60000 }),
  exportByDateRange: (startDate, endDate) =>
    api.get('/claims/export-by-date-range', {
      params: { start_date: startDate, end_date: endDate },
      responseType: 'blob',
      timeout: 600000,
    }),
  exportBatch: (claimIds) =>
    api.post('/claims/export/batch', { claim_ids: claimIds }, { responseType: 'blob', timeout: 300000 }),
  // ClaimIT report upload & error batches
  uploadClaimitReport: (formData) =>
    api.post('/claims/claimit-report/upload', formData, {
      timeout: 120000,
      headers: { 'Content-Type': undefined },
    }),
  getClaimitBatches: () => api.get('/claims/claimit-report/batches'),
  getClaimitBatch: (batchId) => api.get(`/claims/claimit-report/batches/${batchId}`),
  deleteClaimitBatch: (batchId) => api.delete(`/claims/claimit-report/batches/${batchId}`),
  setClaimitErrorComplete: (batchId, errorId, completed) =>
    api.patch(`/claims/claimit-report/batches/${batchId}/errors/${errorId}/complete`, { completed }),
  // GHIMS XML import batches
  uploadGhimsXml: (formData) =>
    api.post('/claims/ghims-import/upload', formData, {
      timeout: 120000,
      headers: { 'Content-Type': undefined },
    }),
  getGhimsImportBatches: () => api.get('/claims/ghims-import/batches'),
  getGhimsImportBatch: (batchId, params = {}) =>
    api.get(`/claims/ghims-import/batches/${batchId}`, { params }),
  getGhimsImportBatchClaimTotals: (batchId) =>
    api.get(`/claims/ghims-import/batches/${batchId}/claim-totals`),
  deleteGhimsImportBatch: (batchId) => api.delete(`/claims/ghims-import/batches/${batchId}`),
  getGhimsImportItem: (itemId) => api.get(`/claims/ghims-import/items/${itemId}`),
  updateGhimsImportItem: (itemId, payload) => api.put(`/claims/ghims-import/items/${itemId}`, { payload }),
  finalizeGhimsImportItem: (itemId) => api.patch(`/claims/ghims-import/items/${itemId}/finalize`),
  vetGhimsImportItem: (itemId, by, clear = false) =>
    api.patch(`/claims/ghims-import/items/${itemId}/vet`, { by, clear: !!clear }),
  flagGhimsImportItem: (itemId, comment) =>
    api.patch(`/claims/ghims-import/items/${itemId}/flag`, { comment }),
  reopenGhimsImportItem: (itemId) => api.patch(`/claims/ghims-import/items/${itemId}/reopen`),
  bulkUpdateGhimsImportItemsStatus: (itemIds, action, comment = null) =>
    api.patch('/claims/ghims-import/items/bulk-status', { item_ids: itemIds, action, comment }),
  getGhimsImportAssignees: () => api.get('/claims/ghims-import/assignees'),
  assignGhimsImportItem: (itemId, { assigned_to_id = null, assignment_note = null } = {}) =>
    api.patch(`/claims/ghims-import/items/${itemId}/assign`, { assigned_to_id, assignment_note }),
  bulkAssignGhimsImportBatch: (batchId, rules, { replace_plan = false, save_plan = false } = {}) =>
    api.post(`/claims/ghims-import/batches/${batchId}/assign`, {
      rules,
      replace_plan: !!replace_plan,
      save_plan: !!save_plan,
    }),
  exportGhimsImportItems: (itemIds) => api.post('/claims/ghims-import/export', { item_ids: itemIds }, { responseType: 'blob' }),
  // CFX convert / diff tools
  previewCxf: (formData) =>
    api.post('/claims/cxf/preview', formData, {
      timeout: 180000,
      headers: { 'Content-Type': undefined },
    }),
  convertCxfToXml: (formData) =>
    api.post('/claims/cxf/convert', formData, {
      timeout: 180000,
      responseType: 'blob',
      headers: { 'Content-Type': undefined },
    }),
  diffXmlVsCxf: (formData) =>
    api.post('/claims/cxf/diff', formData, {
      timeout: 180000,
      headers: { 'Content-Type': undefined },
    }),
  downloadXmlMissingFromCxf: (formData) =>
    api.post('/claims/cxf/diff/download-missing', formData, {
      timeout: 180000,
      responseType: 'blob',
      headers: { 'Content-Type': undefined },
    }),
};

/** AI Claims Vetting (optional module: ai_claims_vetting) */
export const aiClaimVettingAPI = {
  getStatus: () => api.get('/ai-claim-vetting/status'),
  analyzeSample: (payload) => api.post('/ai-claim-vetting/analyze', payload),
  analyzeGhimsItem: (itemId, { mode = 'phase1' } = {}) =>
    api.post(`/ai-claim-vetting/ghims-items/${itemId}/analyze`, null, {
      params: { mode },
    }),
  listGhimsFindings: (itemId, statusFilter = null) =>
    api.get(`/ai-claim-vetting/ghims-items/${itemId}/findings`, {
      params: statusFilter ? { status_filter: statusFilter } : {},
    }),
  decideFinding: (findingId, { decision, note = null, otac = null, chosen_value = null } = {}) =>
    api.post(`/ai-claim-vetting/findings/${findingId}/decide`, {
      decision,
      ...(note ? { note } : {}),
      ...(otac ? { otac } : {}),
      ...(chosen_value ? { chosen_value } : {}),
    }),
  startBatchAnalyze: (batchId, { item_ids = null, include_finalized = false, mode = 'phase1' } = {}) =>
    api.post(`/ai-claim-vetting/batches/${batchId}/analyze`, {
      item_ids: item_ids && item_ids.length ? item_ids : null,
      include_finalized: !!include_finalized,
      mode: mode || 'phase1',
    }),
  startLlmAssist: (batchId, { item_ids, note = null } = {}) =>
    api.post(`/ai-claim-vetting/batches/${batchId}/llm-assist`, {
      item_ids: item_ids || [],
      ...(note ? { note } : {}),
    }, { timeout: 120000 }),
  getJob: (jobId) => api.get(`/ai-claim-vetting/jobs/${jobId}`),
  getLatestBatchJob: (batchId, { mode = null } = {}) =>
    api.get(`/ai-claim-vetting/batches/${batchId}/jobs/latest`, {
      params: mode ? { mode } : {},
    }),
  getBatchReport: (batchId, statusFilter = 'pending', { scope = 'rules' } = {}) =>
    api.get(`/ai-claim-vetting/batches/${batchId}/report`, {
      params: { status_filter: statusFilter, scope },
    }),
  bulkDecideFindings: ({ finding_ids, decision, note = null, otac = null, chosen_value = null }) =>
    api.post('/ai-claim-vetting/findings/bulk-decide', {
      finding_ids,
      decision,
      ...(note ? { note } : {}),
      ...(otac ? { otac } : {}),
      ...(chosen_value ? { chosen_value } : {}),
    }, { timeout: 600000 }),
  listRules: (enabledOnly = false) =>
    api.get('/ai-claim-vetting/rules', { params: enabledOnly ? { enabled_only: true } : {} }),
  getRulesMeta: () => api.get('/ai-claim-vetting/rules/meta'),
  draftRuleFromText: (instruction) =>
    api.post('/ai-claim-vetting/rules/draft-from-text', { instruction }, { timeout: 120000 }),
  createRule: (payload) => api.post('/ai-claim-vetting/rules', payload),
  updateRule: (ruleId, payload) => api.patch(`/ai-claim-vetting/rules/${ruleId}`, payload),
  deleteRule: (ruleId) => api.delete(`/ai-claim-vetting/rules/${ruleId}`),
};

/** Claims analytics: dashboard aggregates + advice */
export const claimsAnalyticsAPI = {
  getDashboard: (params = {}) => api.get('/claims/dashboard', { params }),
};

// Staff endpoints
export const staffAPI = {
  getAll: () => api.get('/staff/'),
  create: (data) => api.post('/staff/', data),
  update: (userId, data) => api.put(`/staff/${userId}`, data),
  delete: (userId) => api.delete(`/staff/${userId}`),
  import: (file, defaultPassword = 'password123') => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/staff/import?default_password=${encodeURIComponent(defaultPassword)}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // User roles management
  getUserRoles: (userId) => api.get(`/staff/${userId}/roles`),
  addUserRole: (userId, role) => api.post(`/staff/${userId}/roles`, { role }),
  removeUserRole: (userId, roleId) => api.delete(`/staff/${userId}/roles/${roleId}`),
  removeUserRoleByName: (userId, roleName) => api.delete(`/staff/${userId}/roles/by-name/${roleName}`),
};

// Lab Templates API
export const databaseAPI = {
  cleanupAuditLogs: (data) => api.post('/database/cleanup-audit-logs', data),
  // Backup operations
  exportBackup: () =>
    api.get('/database/backup/export', { responseType: 'blob' }),
  importBackup: (file) => {
    const formData = new FormData();
    formData.append('backup_file', file);
    return api.post('/database/backup/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listBackups: () => api.get('/database/backup/list'),
  deleteBackup: (filename) => api.delete(`/database/backup/${filename}`),
  getBackupStatus: () => api.get('/database/backup/status'),
  configureBackupSchedule: (schedule) =>
    api.post('/database/backup/schedule', schedule),
  
  // Sync operations
  getSyncStatus: () => api.get('/database/sync/status'),
  testSyncConnection: () => api.post('/database/sync/test'),
  runSync: () => api.post('/database/sync/run'),
  
  // Database info
  getDatabaseInfo: () => api.get('/database/info'),
};

export const labTemplatesAPI = {
  getAll: (procedure_name = null, g_drg_code = null, is_active = null) => {
    const params = {};
    if (procedure_name) params.procedure_name = procedure_name;
    if (g_drg_code) params.g_drg_code = g_drg_code;
    if (is_active !== null) params.is_active = is_active;
    return api.get('/lab-templates', { params });
  },
  getByProcedure: (procedure_name) => 
    api.get(`/lab-templates/by-procedure/${encodeURIComponent(procedure_name)}`),
  getAvailableProcedures: () => 
    api.get('/lab-templates/available-procedures'),
  get: (templateId) => 
    api.get(`/lab-templates/${templateId}`),
  create: (data) => 
    api.post('/lab-templates', data),
  update: (templateId, data) => 
    api.put(`/lab-templates/${templateId}`, data),
  delete: (templateId) => 
    api.delete(`/lab-templates/${templateId}`),
  generateSampleId: (source = null, investigationId = null) => {
    const params = {};
    if (source) params.source = source;
    if (investigationId) params.investigation_id = investigationId;
    return api.get('/lab-templates/generate-sample-id', { params });
  },
};

// System endpoints
// Audit Logs endpoints
export const auditLogsAPI = {
  getLogs: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.role) params.append('role', filters.role);
    if (filters.full_name) params.append('full_name', filters.full_name);
    if (filters.username) params.append('username', filters.username);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.action) params.append('action', filters.action);
    if (filters.resource_type) params.append('resource_type', filters.resource_type);
    if (filters.endpoint_path) params.append('endpoint_path', filters.endpoint_path);
    if (filters.http_method) params.append('http_method', filters.http_method);
    if (filters.page) params.append('page', filters.page);
    if (filters.page_size) params.append('page_size', filters.page_size);
    return api.get(`/audit-logs?${params.toString()}`);
  },
  getLog: (logId) => api.get(`/audit-logs/${logId}`),
  getRoles: () => api.get('/audit-logs/roles'),
  getActions: () => api.get('/audit-logs/actions'),
  getResourceTypes: () => api.get('/audit-logs/resource-types'),
  getEndpointPaths: () => api.get('/audit-logs/endpoint-paths'),
  getHttpMethods: () => api.get('/audit-logs/http-methods'),
};

export const systemAPI = {
  getApplicationDate: () => api.get('/system/date'),
};

// Requisitions endpoints
export const pharmacyRequisitionsAPI = {
  create: (data) => api.post('/pharmacy-requisitions', data),
  update: (requisitionId, data) => api.put(`/pharmacy-requisitions/${requisitionId}`, data),
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.ward) params.append('ward', filters.ward); // Legacy
    if (filters.department_id) params.append('department_id', filters.department_id);
    if (filters.store_id) params.append('store_id', filters.store_id);
    if (filters.status) params.append('status', filters.status);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.page) params.append('page', filters.page);
    if (filters.page_size) params.append('page_size', filters.page_size);
    return api.get(`/pharmacy-requisitions?${params.toString()}`);
  },
  get: (requisitionId) => api.get(`/pharmacy-requisitions/${requisitionId}`),
  approve: (requisitionId, data) => api.put(`/pharmacy-requisitions/${requisitionId}/approve`, data),
  reject: (requisitionId, data) => api.put(`/pharmacy-requisitions/${requisitionId}/reject`, data),
  revertApproval: (requisitionId) => api.put(`/pharmacy-requisitions/${requisitionId}/revert-approval`),
  revertFulfillment: (requisitionId) => api.put(`/pharmacy-requisitions/${requisitionId}/revert-fulfillment`),
  cancel: (requisitionId) => api.put(`/pharmacy-requisitions/${requisitionId}/cancel`),
  fulfill: (requisitionId, data) => api.put(`/pharmacy-requisitions/${requisitionId}/fulfill`, data),
  getWardStock: (ward, productCode = null, storeId = null) => {
    const params = new URLSearchParams();
    if (storeId) params.append('store_id', storeId);
    if (productCode) {
      return api.get(`/pharmacy-requisitions/ward-stock/${ward}/${productCode}?${params.toString()}`);
    }
    return api.get(`/pharmacy-requisitions/ward-stock/${ward}?${params.toString()}`);
  },
};

// Notifications endpoints
export const notificationsAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.is_read !== undefined) params.append('is_read', filters.is_read);
    if (filters.page) params.append('page', filters.page);
    if (filters.page_size) params.append('page_size', filters.page_size);
    return api.get(`/notifications?${params.toString()}`);
  },
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markRead: (notificationId) => api.put(`/notifications/${notificationId}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
  delete: (notificationId) => api.delete(`/notifications/${notificationId}`),
};

// Vendors endpoints
export const vendorsAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.is_active !== undefined) params.append('is_active', filters.is_active);
    return api.get(`/vendors?${params.toString()}`);
  },
  get: (vendorId) => api.get(`/vendors/${vendorId}`),
  create: (data) => api.post('/vendors', data),
  update: (vendorId, data) => api.put(`/vendors/${vendorId}`, data),
  delete: (vendorId) => api.delete(`/vendors/${vendorId}`),
};

// Store Stock endpoints
export const storeStockAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.store_id) params.append('store_id', filters.store_id);
    if (filters.product_code) params.append('product_code', filters.product_code);
    if (filters.status) params.append('status', filters.status);
    if (filters.vendor_id) params.append('vendor_id', filters.vendor_id);
    return api.get(`/store-stock?${params.toString()}`);
  },
  get: (stockId) => api.get(`/store-stock/${stockId}`),
  create: (data) => api.post('/store-stock', data),
  update: (stockId, data) => api.put(`/store-stock/${stockId}`, data),
  delete: (stockId) => api.delete(`/store-stock/${stockId}`),
  approve: (stockId, data) => api.put(`/store-stock/${stockId}/approve`, data),
  getSummaryByProduct: (storeId = null) => {
    const params = new URLSearchParams();
    if (storeId) params.append('store_id', storeId);
    return api.get(`/store-stock/summary/by-product?${params.toString()}`);
  },
};

export const misReportsAPI = {
  getConsultingRoomRegister: (startDate, endDate, department = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (department) params.department = department;
    return api.get('/mis-reports/consulting-room-register', { params });
  },
  exportConsultingRoomRegister: (startDate, endDate, department = null, clinicName) => {
    const params = { start_date: startDate, end_date: endDate };
    if (department) params.department = department;
    if (clinicName != null && String(clinicName).trim() !== '') {
      params.clinic_name = String(clinicName).trim();
    }
    return api.get('/mis-reports/consulting-room-register/export', { 
      params,
      responseType: 'blob'
    });
  },
  getStatementOfOutpatient: (startDate, endDate, departments = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (departments) params.departments = departments;
    return api.get('/mis-reports/statement-of-outpatient', { params });
  },
  exportStatementOfOutpatient: (startDate, endDate, departments = null, clinicName, clinicCity = '', clinicRegion = 'N/A', clinicDistrict = 'N/A') => {
    const params = {
      start_date: startDate,
      end_date: endDate,
      clinic_city: clinicCity,
      clinic_region: clinicRegion,
      clinic_district: clinicDistrict,
    };
    if (clinicName != null && String(clinicName).trim() !== '') {
      params.clinic_name = String(clinicName).trim();
    }
    if (departments) params.departments = departments;
    return api.get('/mis-reports/statement-of-outpatient/export', { 
      params,
      responseType: 'blob'
    });
  },
  getOPDMorbidity: (startDate, endDate, departments = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (departments) params.departments = departments;
    return api.get('/mis-reports/opd-morbidity', { params });
  },
  exportOPDMorbidity: (startDate, endDate, departments = null, clinicName, clinicCity = '', clinicRegion = 'N/A', clinicDistrict = 'N/A') => {
    const params = {
      start_date: startDate,
      end_date: endDate,
      clinic_city: clinicCity,
      clinic_region: clinicRegion,
      clinic_district: clinicDistrict,
    };
    if (clinicName != null && String(clinicName).trim() !== '') {
      params.clinic_name = String(clinicName).trim();
    }
    if (departments) params.departments = departments;
    return api.get('/mis-reports/opd-morbidity/export', { 
      params,
      responseType: 'blob'
    });
  },
  getInhouseLabParameters: (startDate, endDate, departments = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (departments) params.departments = departments;
    return api.get('/mis-reports/inhouse-lab-parameters', { params });
  },
  exportInhouseLabParameters: (startDate, endDate, departments = null) => {
    const params = { start_date: startDate, end_date: endDate };
    if (departments) params.departments = departments;
    return api.get('/mis-reports/inhouse-lab-parameters/export', {
      params,
      responseType: 'blob'
    });
  },
  getDrugsDispensed: (startDate, endDate, medicineCode = null, medicineName = null, source = 'all') => {
    const params = { start_date: startDate, end_date: endDate, source: source || 'all' };
    if (medicineCode) params.medicine_code = medicineCode;
    if (medicineName) params.medicine_name = medicineName;
    return api.get('/mis-reports/drugs-dispensed', { params });
  },
  exportDrugsDispensed: (startDate, endDate, medicineCode = null, medicineName = null, source = 'all', clinicName = null) => {
    const params = { start_date: startDate, end_date: endDate, source: source || 'all' };
    if (medicineCode) params.medicine_code = medicineCode;
    if (medicineName) params.medicine_name = medicineName;
    if (clinicName != null && String(clinicName).trim() !== '') {
      params.clinic_name = String(clinicName).trim();
    }
    return api.get('/mis-reports/drugs-dispensed/export', {
      params,
      responseType: 'blob'
    });
  },
};

export const wardsAPI = {
  getAll: (activeOnly = true, departmentType = null) => {
    const params = new URLSearchParams();
    if (activeOnly) params.append('active_only', 'true');
    if (departmentType) params.append('department_type', departmentType);
    return api.get(`/wards?${params.toString()}`);
  },
  get: (wardId) => api.get(`/wards/${wardId}`),
  create: (data) => api.post('/wards', data),
  update: (wardId, data) => api.put(`/wards/${wardId}`, data),
  delete: (wardId) => api.delete(`/wards/${wardId}`),
};

export const storesAPI = {
  getAll: (activeOnly = true) => {
    const params = new URLSearchParams();
    if (activeOnly) params.append('active_only', 'true');
    return api.get(`/stores?${params.toString()}`);
  },
  get: (storeId) => api.get(`/stores/${storeId}`),
  create: (data) => api.post('/stores', data),
  update: (storeId, data) => api.put(`/stores/${storeId}`, data),
  delete: (storeId) => api.delete(`/stores/${storeId}`),
};

/** Inventory mode: store/department scoped KPIs, trends, top products */
export const inventoryAnalyticsAPI = {
  getDashboard: (params = {}) => api.get('/inventory-analytics/dashboard', { params }),
};

/** Inventory reports (requisitions + store stock); scope matches inventory dashboard */
export const inventoryReportsAPI = {
  getRequisitions: (params = {}) => api.get('/inventory-reports/requisitions', { params }),
  getStoreStock: (params = {}) => api.get('/inventory-reports/store-stock', { params }),
  downloadRequisitionsCsv: (params = {}) =>
    api.get('/inventory-reports/requisitions', {
      params: { ...params, export_csv: true },
      responseType: 'blob',
    }),
  downloadStoreStockCsv: (params = {}) =>
    api.get('/inventory-reports/store-stock', {
      params: { ...params, export_csv: true },
      responseType: 'blob',
    }),
};

// Module Settings endpoints
export const moduleSettingsAPI = {
  getAll: (category = null) => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    return api.get(`/module-settings?${params.toString()}`);
  },
  get: (moduleKey) => api.get(`/module-settings/${moduleKey}`),
  getStatus: (moduleKey) => api.get(`/module-settings/status/${moduleKey}`),
  getStatusBatch: (moduleKeys) => {
    const keys = Array.isArray(moduleKeys) ? moduleKeys.join(',') : moduleKeys;
    return api.get(`/module-settings/status/batch?module_keys=${keys}`);
  },
  update: (moduleKey, data) => api.put(`/module-settings/${moduleKey}`, data),
  toggle: (moduleKey) => api.put(`/module-settings/${moduleKey}/toggle`),
  setPermissions: (moduleKey, permissions) => api.put(`/module-settings/${moduleKey}/set-permissions`, permissions),
};

export const facilitySettingsAPI = {
  getPublic: () => api.get('/facility-settings/public'),
  update: (data) => api.put('/facility-settings/', data),
  getMyTheme: () => api.get('/facility-settings/my-theme'),
  updateMyTheme: (data) => api.put('/facility-settings/my-theme', data),
};

export const licenseAPI = {
  getPublicStatus: () => api.get('/license/public-status'),
  activate: (document, setupToken) =>
    api.post('/license/activate', { document, setup_token: setupToken }),
  pullFromPortal: () => api.post('/license/pull-from-portal', {}),
  getStatus: () => api.get('/license/status'),
  getActivationSummary: () => api.get('/license/activation-summary'),
  analyzeDocument: (document) => api.post('/license/analyze', { document }),
};

export const departmentStaffAssignmentsAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.department_id) params.append('department_id', filters.department_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.active_only !== undefined) params.append('active_only', filters.active_only);
    return api.get(`/department-staff-assignments?${params.toString()}`);
  },
  create: (data) => api.post('/department-staff-assignments', data),
  update: (assignmentId, data) => api.put(`/department-staff-assignments/${assignmentId}`, data),
  delete: (assignmentId) => api.delete(`/department-staff-assignments/${assignmentId}`),
};

export const storeStaffAssignmentsAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.store_id) params.append('store_id', filters.store_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.active_only !== undefined) params.append('active_only', filters.active_only);
    return api.get(`/store-staff-assignments?${params.toString()}`);
  },
  create: (data) => api.post('/store-staff-assignments', data),
  update: (assignmentId, data) => api.put(`/store-staff-assignments/${assignmentId}`, data),
  delete: (assignmentId) => api.delete(`/store-staff-assignments/${assignmentId}`),
};

export default api;

