import axios from 'axios';

const API_BASE_URL = process.env.API_BASE_URL || (process.env.NODE_ENV === 'production' ? '/backend/api' : 'http://localhost:8000/api');

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
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
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
  getConsultationNotes: (encounterId) => api.get(`/consultation/notes/encounter/${encounterId}`),
  saveConsultationNotes: (data) => api.post('/consultation/notes', data),
  getPrescriptionsByPatientCard: (cardNumber, encounterId) => 
    api.get(`/consultation/prescription/patient/${cardNumber}/encounter/${encounterId}`),
  confirmPrescription: (prescriptionId, data = null) => {
    // Send empty object if data is null to ensure request body is sent
    return api.put(`/consultation/prescription/${prescriptionId}/confirm`, data || {});
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
  updateInvestigationDetails: (investigationId, data) => 
    api.put(`/consultation/investigation/${investigationId}/update-details`, data),
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

