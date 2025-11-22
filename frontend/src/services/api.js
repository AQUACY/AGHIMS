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
  createDoctorNoteEntry: (encounterId, data) => api.post(`/consultation/encounters/${encounterId}/doctor-notes`, data),
  updateDoctorNoteEntry: (noteId, data) => api.put(`/consultation/doctor-notes/${noteId}`, data),
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
    releaseInventoryDebit: (debitId) => api.put(`/consultation/inventory-debits/${debitId}/release`),
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
  searchPriceItems: (searchTerm = null, serviceType = null, fileType = null) => {
    const params = {};
    if (searchTerm) params.search_term = searchTerm;
    if (serviceType) params.service_type = serviceType;
    if (fileType) params.file_type = fileType;
    return api.get('/price-list/search', { params });
  },
  getDrgCodesFromIcd10: (icd10Code) => {
    return api.get(`/price-list/icd10/${icd10Code}/drg-codes`);
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
  getEligibleEncounters: (type = null, startDate = null, endDate = null, claimStatus = null, cardNumber = null) => {
    const params = {};
    if (type) params.claim_type = type;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (claimStatus) params.claim_status = claimStatus;
    if (cardNumber) params.card_number = cardNumber;
    return api.get('/claims/eligible-encounters', { params });
  },
  get: (claimId) => api.get(`/claims/${claimId}`),
  getAll: () => api.get('/claims/'),
  update: (claimId, data) => api.put(`/claims/${claimId}`, data),
  updateDetailed: (claimId, data) => api.put(`/claims/${claimId}/detailed`, data),
  getEditDetails: (claimId) => api.get(`/claims/${claimId}/edit-details`),
  finalize: (claimId) => api.put(`/claims/${claimId}/finalize`),
  reopen: (claimId) => api.put(`/claims/${claimId}/reopen`),
  regenerate: (claimId, data) => api.put(`/claims/${claimId}/regenerate`, data),
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

// Lab Templates API
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

export default api;

