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
        const blob = new Blob([response.data], { type: 'application/xml' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `NHIS_CLA${claimId}.xml`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        
        Notify.create({
          type: 'positive',
          message: 'Claim exported successfully',
          position: 'top',
        });
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to export claim',
          position: 'top',
        });
        throw error;
      }
    },

    async exportByDateRange(startDate, endDate) {
      try {
        const response = await claimsAPI.exportByDateRange(startDate, endDate);
        const blob = new Blob([response.data], { type: 'application/xml' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const filename = `NHIS_CLA${startDate.replace(/-/g, '')}${endDate.replace(/-/g, '')}.xml`;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        
        Notify.create({
          type: 'positive',
          message: 'Claims exported successfully',
          position: 'top',
        });
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to export claims',
          position: 'top',
        });
        throw error;
      }
    },
  },
});

