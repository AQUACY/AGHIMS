import axios from 'axios';

// API_BASE_URL is set in quasar.config.js build.env
// In production: Use the current hostname (server IP) with port 8000
// In development: 'http://localhost:8000/api'
const getApiBaseUrl = () => {
  // If API_BASE_URL is explicitly set in environment, use it
  if (process.env.API_BASE_URL && process.env.API_BASE_URL !== 'http://localhost:8000/api') {
    return process.env.API_BASE_URL;
  }
  
  // Always use the current hostname with port 8000
  // This works for both localhost and network IP access
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  
  // If accessing from dev server (port 9000 or 3000), use the same hostname with port 8000
  // This allows network access to work (e.g., 10.10.16.50:9000 -> 10.10.16.50:8000)
  if (window.location.port === '9000' || window.location.port === '3000') {
    // Development mode - use same hostname with port 8000
    return `${protocol}//${hostname}:8000/api`;
  }
  
  // Production mode - use current hostname with port 8000
  return `${protocol}//${hostname}:8000/api`;
};

const API_BASE_URL = getApiBaseUrl();

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
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      // Only redirect if not already on login page to avoid redirect loops
      if (window.location.pathname !== '/login') {
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
            // If we can't decode, proceed with logout
            console.warn('Could not decode token to check age:', e);
          }
        }
        
        // Token is old enough or we couldn't check - proceed with logout
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        // Use a small delay to allow any ongoing operations to complete
        setTimeout(() => {
          window.location.href = '/login';
        }, 100);
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
  getInvestigationsByPatientCard: (cardNumber, encounterId, investigationType = null) => {
    const url = `/consultation/investigation/patient/${cardNumber}/encounter/${encounterId}`;
    const params = investigationType ? { investigation_type: investigationType } : {};
    return api.get(url, { params });
  },
  getInvestigationsByType: (investigationType, filters = {}) => {
    const url = `/consultation/investigation/list/${investigationType}`;
    return api.get(url, { params: filters });
  },
  getInvestigation: (investigationId) => {
    return api.get(`/consultation/investigation/${investigationId}`);
  },
  updateInvestigationDetails: (investigationId, data) => 
    api.put(`/consultation/investigation/${investigationId}/update-details`, data),
  revertInvestigationStatus: (investigationId) => 
    api.put(`/consultation/investigation/${investigationId}/revert-status`),
  revertInvestigationToRequested: (investigationId, reason) => 
    api.put(`/consultation/investigation/${investigationId}/revert-to-requested`, { reason }),
  getLabResult: (investigationId) => 
    api.get(`/consultation/lab-result/investigation/${investigationId}`),
  createLabResult: (formData) => 
    api.post('/consultation/lab-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadLabResultAttachment: (investigationId) => 
    api.get(`/consultation/lab-result/${investigationId}/download`, {
      responseType: 'blob',
    }),
  getScanResult: (investigationId) => 
    api.get(`/consultation/scan-result/investigation/${investigationId}`),
  createScanResult: (formData) => 
    api.post('/consultation/scan-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadScanResultAttachment: (investigationId) => 
    api.get(`/consultation/scan-result/${investigationId}/download`, {
      responseType: 'blob',
    }),
  getXrayResult: (investigationId) => 
    api.get(`/consultation/xray-result/investigation/${investigationId}`),
  createXrayResult: (formData) => 
    api.post('/consultation/xray-result', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  downloadXrayResultAttachment: (investigationId) => 
    api.get(`/consultation/xray-result/${investigationId}/download`, {
      responseType: 'blob',
    }),
  getAdmissionRecommendations: () => api.get('/consultation/admissions'),
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
  getDrgCodesFromIcd10: (icd10Code) => {
    return api.get(`/price-list/icd10/${icd10Code}/drg-codes`);
  },
  search: (searchTerm, serviceType, fileType) => 
    api.get('/price-list/search', { 
      params: { 
        search_term: searchTerm || undefined,
        service_type: serviceType || undefined,
        file_type: fileType || undefined
      } 
    }),
  getServiceTypes: () => api.get('/price-list/service-types'),
  getProceduresByServiceType: (serviceType) => 
    api.get('/price-list/procedures/by-service-type', {
      params: { service_type: serviceType }
    }),
  updateItem: (fileType, id, data) => api.put(`/price-list/item/${fileType}/${id}`, data),
};

// Claims endpoints
export const claimsAPI = {
  create: (data) => api.post('/claims/', data),
  getEligibleEncounters: (type = null) => {
    const params = type ? { claim_type: type } : {};
    return api.get('/claims/eligible-encounters', { params });
  },
  get: (claimId) => api.get(`/claims/${claimId}`),
  getAll: () => api.get('/claims/'),
  update: (claimId, data) => api.put(`/claims/${claimId}`, data),
  updateDetailed: (claimId, data) => api.put(`/claims/${claimId}/detailed`, data),
  getEditDetails: (claimId) => api.get(`/claims/${claimId}/edit-details`),
  finalize: (claimId) => api.put(`/claims/${claimId}/finalize`),
  reopen: (claimId) => api.put(`/claims/${claimId}/reopen`),
  exportSingle: (claimId) => 
    api.get(`/claims/export/${claimId}`, { responseType: 'blob' }),
  exportByDateRange: (startDate, endDate) => 
    api.get('/claims/export/date-range', { 
      params: { start_date: startDate, end_date: endDate },
      responseType: 'blob'
    }),
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
};

export default api;

