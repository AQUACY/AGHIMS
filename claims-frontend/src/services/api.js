import axios from 'axios';

const getApiBaseUrl = () => {
  if (process.env.API_BASE_URL) {
    return process.env.API_BASE_URL;
  }

  const protocol = window.location.protocol;
  const hostname = window.location.hostname;

  if (window.location.port === '9001' || window.location.port === '9000') {
    return `${protocol}//${hostname}:8000/api`;
  }

  return `${protocol}//${hostname}:8000/api`;
};

const API_BASE_URL = getApiBaseUrl();

export { getApiBaseUrl, API_BASE_URL };

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (config.data && typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (window.location.pathname === '/login') {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await api.post('/auth/refresh');
        const { access_token } = response.data;
        localStorage.setItem('auth_token', access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
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
  refreshToken: () => api.post('/auth/refresh'),
};

export const encountersAPI = {
  get: (encounterId) => api.get(`/encounters/${encounterId}`),
};

export const consultationAPI = {
  getDiagnoses: (encounterId) => api.get(`/consultation/diagnosis/encounter/${encounterId}`),
  getPrescriptions: (encounterId) => api.get(`/consultation/prescription/encounter/${encounterId}`),
  getInvestigations: (encounterId) => api.get(`/consultation/investigation/encounter/${encounterId}`),
  getWardAdmission: (wardAdmissionId) => api.get(`/consultation/ward-admissions/${wardAdmissionId}`),
  getAllInpatientDiagnoses: (wardAdmissionId) =>
    api.get(`/consultation/ward-admissions/${wardAdmissionId}/diagnoses/all`),
  getInpatientSurgeries: (wardAdmissionId) =>
    api.get(`/consultation/ward-admissions/${wardAdmissionId}/surgeries`),
  updateInpatientSurgery: (wardAdmissionId, surgeryId, surgeryData) =>
    api.put(`/consultation/ward-admissions/${wardAdmissionId}/surgeries/${surgeryId}`, surgeryData),
  getWardAdmissionsByPatientCard: (cardNumber, includeDischarged = false) =>
    api.get(`/consultation/ward-admissions/patient/${cardNumber}`, {
      params: { include_discharged: includeDischarged },
    }),
  getAllInpatientInvestigations: (wardAdmissionId) =>
    api.get(`/consultation/ward-admissions/${wardAdmissionId}/investigations/all`),
};

export const priceListAPI = {
  searchIcd10: (searchTerm, limit = 50) => {
    const params = { limit };
    if (searchTerm) params.search_term = searchTerm;
    return api.get('/price-list/icd10/search', { params });
  },
  getDrgCodesFromIcd10: (icd10Code) => api.get(`/price-list/icd10/${icd10Code}/drg-codes`),
  getIcd10CodesFromDrg: (drgCode) => {
    if (!drgCode || !String(drgCode).trim()) return Promise.resolve({ data: [] });
    return api.get(`/price-list/drg-codes/${encodeURIComponent(drgCode.trim())}/icd10-codes`);
  },
  search: (searchTerm, serviceType, fileType) =>
    api.get('/price-list/search', {
      params: {
        search_term: searchTerm || undefined,
        service_type: serviceType || undefined,
        file_type: fileType || undefined,
      },
    }),
};

export const claimsAPI = {
  create: (data) => api.post('/claims/', data),
  getEligibleEncounters: (
    type = null,
    startDate = null,
    endDate = null,
    claimStatus = null,
    cardNumber = null,
    claimId = null,
    specialty = null,
    skip = 0,
    limit = 50
  ) => {
    const params = { skip, limit };
    if (type) params.claim_type = type;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (claimStatus) params.claim_status = claimStatus;
    if (cardNumber) params.card_number = cardNumber;
    if (claimId) params.claim_id = claimId;
    if (specialty) params.specialty = specialty;
    return api.get('/claims/eligible-encounters', { params });
  },
  getSpecialties: (claimType = null) => {
    const params = {};
    if (claimType) params.claim_type = claimType;
    return api.get('/claims/specialties', { params });
  },
  get: (claimId) => api.get(`/claims/${claimId}`),
  updateDetailed: (claimId, data) => api.put(`/claims/${claimId}/detailed`, data),
  getEditDetails: (claimId) => api.get(`/claims/${claimId}/edit-details`),
  fetchCcc: (claimId, memberNo = null, otac = null) =>
    api.post(`/claims/${claimId}/fetch-ccc`, {
      ...(memberNo ? { member_no: memberNo } : {}),
      ...(otac ? { otac } : {}),
    }),
  fetchGhimsImportCcc: (itemId, memberNo = null) =>
    api.post(`/claims/ghims-import/items/${itemId}/fetch-ccc`, memberNo ? { member_no: memberNo } : {}),
  finalize: (claimId) => api.put(`/claims/${claimId}/finalize`),
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
  uploadClaimitReport: (formData) =>
    api.post('/claims/claimit-report/upload', formData, {
      timeout: 120000,
      headers: { 'Content-Type': undefined },
    }),
  getClaimitBatches: () => api.get('/claims/claimit-report/batches'),
  getClaimitBatch: (batchId) => api.get(`/claims/claimit-report/batches/${batchId}`),
  setClaimitErrorComplete: (batchId, errorId, completed) =>
    api.patch(`/claims/claimit-report/batches/${batchId}/errors/${errorId}/complete`, { completed }),
  uploadGhimsXml: (formData) =>
    api.post('/claims/ghims-import/upload', formData, {
      timeout: 120000,
      headers: { 'Content-Type': undefined },
    }),
  getGhimsImportBatches: () => api.get('/claims/ghims-import/batches'),
  getGhimsImportBatch: (batchId) => api.get(`/claims/ghims-import/batches/${batchId}`),
  deleteGhimsImportBatch: (batchId) => api.delete(`/claims/ghims-import/batches/${batchId}`),
  getGhimsImportItem: (itemId) => api.get(`/claims/ghims-import/items/${itemId}`),
  updateGhimsImportItem: (itemId, payload) =>
    api.put(`/claims/ghims-import/items/${itemId}`, { payload }),
  finalizeGhimsImportItem: (itemId) => api.patch(`/claims/ghims-import/items/${itemId}/finalize`),
  flagGhimsImportItem: (itemId) => api.patch(`/claims/ghims-import/items/${itemId}/flag`),
  reopenGhimsImportItem: (itemId) => api.patch(`/claims/ghims-import/items/${itemId}/reopen`),
  exportGhimsImportItems: (itemIds) =>
    api.post('/claims/ghims-import/export', { item_ids: itemIds }, { responseType: 'blob' }),
};

export const facilitySettingsAPI = {
  getPublic: () => api.get('/facility-settings/public'),
};

export default api;
