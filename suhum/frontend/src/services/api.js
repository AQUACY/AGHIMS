import axios from 'axios';

const getApiBaseUrl = () => {
  if (process.env.API_BASE_URL && process.env.API_BASE_URL !== 'http://localhost:8111/api') {
    return process.env.API_BASE_URL;
  }
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  if (window.location.port === '9002') {
    return `${protocol}//${hostname}:8111/api`;
  }
  return `${protocol}//${hostname}:8111/api`;
};

const API_BASE_URL = getApiBaseUrl();

export { getApiBaseUrl, API_BASE_URL };

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data && typeof FormData !== 'undefined' && config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

export const authAPI = {
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  getMe: () => api.get('/auth/me'),
  listUsers: () => api.get('/auth/users'),
  createUser: (data) => api.post('/auth/users', data),
  updateUser: (userId, data) => api.put(`/auth/users/${userId}`, data),
  deleteUser: (userId) => api.delete(`/auth/users/${userId}`),
};

export const facilitySettingsAPI = {
  getPublic: () => api.get('/auth/facility-public'),
};

export const priceListAPI = {
  upload: (fileType, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/price-list/upload/${fileType}`, formData);
  },
  exportCSV: (fileType) => api.get(`/price-list/export/${fileType}/csv`, { responseType: 'blob' }),
  exportProductCSV: () => api.get('/price-list/export/product/csv', { responseType: 'blob' }),
  createItem: (fileType, data) => api.post(`/price-list/item/${fileType}`, data),
  uploadIcd10Mapping: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/price-list/upload/icd10-mapping', formData);
  },
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
  getIcd10DrgMappings: (skip = 0, limit = 100, search = null, isActive = null, unmappedOnly = false) => {
    const params = { skip, limit };
    if (search) params.search = search;
    if (isActive !== null) params.is_active = isActive;
    if (unmappedOnly) params.unmapped_only = true;
    return api.get('/price-list/icd10-mappings', { params });
  },
  createIcd10DrgMapping: (data) => api.post('/price-list/icd10-mappings', data),
  updateIcd10DrgMapping: (mappingId, data) => api.put(`/price-list/icd10-mappings/${mappingId}`, data),
  deleteIcd10DrgMapping: (mappingId) => api.delete(`/price-list/icd10-mappings/${mappingId}`),
  exportIcd10DrgMapping: (params = {}) =>
    api.get('/price-list/export/icd10-mapping/csv', { params, responseType: 'blob' }),
  searchDrgCodes: (searchTerm, limit = 50) => {
    const params = { limit };
    if (searchTerm) params.search_term = searchTerm;
    return api.get('/price-list/drg-codes/search', { params });
  },
  search: (searchTerm, serviceType, fileType) =>
    api.get('/price-list/search', {
      params: {
        search_term: searchTerm || undefined,
        service_type: serviceType || undefined,
        file_type: fileType || undefined,
      },
    }),
  getServiceTypes: () => api.get('/price-list/service-types'),
  getProceduresByServiceType: (serviceType) =>
    api.get('/price-list/procedures/by-service-type', { params: { service_type: serviceType } }),
  getSurgeries: () => api.get('/price-list/surgeries'),
  updateItem: (fileType, id, data) => api.put(`/price-list/item/${fileType}/${id}`, data),
};

export const ghimsAPI = {
  fetchImportCcc: (itemId, memberNo = null, otac = null) =>
    api.post(`/ghims-import/items/${itemId}/fetch-ccc`, {
      ...(memberNo ? { member_no: memberNo } : {}),
      ...(otac ? { otac } : {}),
    }),
  uploadXml: (formData) =>
    api.post('/ghims-import/upload', formData, { timeout: 120000 }),
  getBatches: () => api.get('/ghims-import/batches'),
  getBatch: (batchId, params = {}) => api.get(`/ghims-import/batches/${batchId}`, { params }),
  getBatchClaimTotals: (batchId) => api.get(`/ghims-import/batches/${batchId}/claim-totals`),
  deleteBatch: (batchId) => api.delete(`/ghims-import/batches/${batchId}`),
  getItem: (itemId) => api.get(`/ghims-import/items/${itemId}`),
  updateItem: (itemId, payload) => api.put(`/ghims-import/items/${itemId}`, { payload }),
  finalizeItem: (itemId) => api.patch(`/ghims-import/items/${itemId}/finalize`),
  flagItem: (itemId, comment) => api.patch(`/ghims-import/items/${itemId}/flag`, { comment }),
  reopenItem: (itemId) => api.patch(`/ghims-import/items/${itemId}/reopen`),
  bulkUpdateStatus: (itemIds, action, comment = null) =>
    api.patch('/ghims-import/items/bulk-status', { item_ids: itemIds, action, comment }),
  exportItems: (itemIds) =>
    api.post('/ghims-import/export', { item_ids: itemIds }, { responseType: 'blob' }),
};

// Alias for pages copied from claims-frontend
export const claimsAPI = {
  fetchGhimsImportCcc: ghimsAPI.fetchImportCcc,
  uploadGhimsXml: ghimsAPI.uploadXml,
  getGhimsImportBatches: ghimsAPI.getBatches,
  getGhimsImportBatch: ghimsAPI.getBatch,
  getGhimsImportBatchClaimTotals: ghimsAPI.getBatchClaimTotals,
  deleteGhimsImportBatch: ghimsAPI.deleteBatch,
  getGhimsImportItem: ghimsAPI.getItem,
  updateGhimsImportItem: ghimsAPI.updateItem,
  finalizeGhimsImportItem: ghimsAPI.finalizeItem,
  flagGhimsImportItem: ghimsAPI.flagItem,
  reopenGhimsImportItem: ghimsAPI.reopenItem,
  bulkUpdateGhimsImportItemsStatus: ghimsAPI.bulkUpdateStatus,
  exportGhimsImportItems: ghimsAPI.exportItems,
};

export const vettingGuideAPI = {
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/vetting-guide/upload', formData, { timeout: 120000 });
  },
  listUploads: () => api.get('/vetting-guide/uploads'),
  getForClaim: (claimId) => api.get(`/vetting-guide/for-claim/${encodeURIComponent(claimId)}`),
  getCoverage: () => api.get('/vetting-guide/coverage'),
  getBatchMatches: (batchId) => api.get(`/vetting-guide/batch/${batchId}/matches`),
};
