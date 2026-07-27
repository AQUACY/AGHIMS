import { defineStore } from 'pinia';
import { claimsAPI } from '../services/api';
import { Notify } from 'quasar';

export const useClaimsStore = defineStore('claims', {
  state: () => ({
    claims: [],
    loading: false,
  }),

  actions: {
    async createClaim(claimData) {
      try {
        const response = await claimsAPI.create(claimData);
        Notify.create({
          type: 'positive',
          message: 'Claim created successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to create claim',
          position: 'top',
        });
        throw error;
      }
    },

    async finalizeClaim(claimId) {
      try {
        const response = await claimsAPI.finalize(claimId);
        Notify.create({
          type: 'positive',
          message: 'Claim finalized successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to finalize claim',
          position: 'top',
        });
        throw error;
      }
    },

    async reopenClaim(claimId) {
      try {
        const response = await claimsAPI.reopen(claimId);
        Notify.create({
          type: 'positive',
          message: 'Claim reopened successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to reopen claim',
          position: 'top',
        });
        throw error;
      }
    },

    async exportClaim(claimId) {
      try {
        const response = await claimsAPI.exportSingle(claimId);
        if (response.status < 200 || response.status >= 300) {
          const msg = await this._blobErrorDetail(response.data);
          Notify.create({ type: 'negative', message: msg || 'Export failed', position: 'top' });
          return;
        }
        const blob = new Blob([response.data], { type: 'application/xml' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `NHIS_CLA${claimId}.xml`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        Notify.create({ type: 'positive', message: 'Claim exported successfully', position: 'top' });
      } catch (error) {
        const msg = await this._blobErrorDetail(error.response?.data);
        Notify.create({
          type: 'negative',
          message: msg || error.response?.data?.detail || error.message || 'Failed to export claim',
          position: 'top',
        });
        throw error;
      }
    },

    async _blobErrorDetail(blob) {
      const { parseExportErrorDetail, exportErrorMessage } = await import('../utils/exportErrorDetail');
      const detail = await parseExportErrorDetail(blob);
      return exportErrorMessage(detail);
    },

    async exportByDateRange(startDate, endDate) {
      try {
        const response = await claimsAPI.exportByDateRange(startDate, endDate);
        if (response.status < 200 || response.status >= 300) {
          const msg = await this._blobErrorDetail(response.data);
          Notify.create({ type: 'negative', message: msg || 'Export failed', position: 'top' });
          return;
        }
        const blob = new Blob([response.data], { type: 'application/zip' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const filename = `NHIS_CLA${startDate.replace(/-/g, '')}${endDate.replace(/-/g, '')}.zip`;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        Notify.create({ type: 'positive', message: 'Claims exported (ZIP). Extract to get the XML file.', position: 'top' });
      } catch (error) {
        const msg = await this._blobErrorDetail(error.response?.data);
        Notify.create({
          type: 'negative',
          message: msg || error.response?.data?.detail || error.message || 'Failed to export claims',
          position: 'top',
        });
        throw error;
      }
    },
  },
});

