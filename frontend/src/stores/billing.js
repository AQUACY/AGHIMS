import { defineStore } from 'pinia';
import { billingAPI, priceListAPI } from '../services/api';
import { Notify } from 'quasar';

export const useBillingStore = defineStore('billing', {
  state: () => ({
    priceListItems: [],
    currentBill: null,
    encounterBills: [],
  }),

  actions: {
    async uploadPriceList(fileType, file) {
      try {
        const response = await priceListAPI.upload(fileType, file);
        Notify.create({
          type: 'positive',
          message: `Successfully uploaded ${response.data.count} items to ${response.data.file_type} table`,
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to upload price list',
          position: 'top',
        });
        throw error;
      }
    },

    async searchPriceItems(searchTerm, serviceType = null, fileType = null) {
      try {
        const response = await priceListAPI.search(searchTerm, serviceType, fileType);
        this.priceListItems = response.data;
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to search price items',
          position: 'top',
        });
        throw error;
      }
    },

    async updatePriceItem(fileType, id, data) {
      try {
        const response = await priceListAPI.updateItem(fileType, id, data);
        Notify.create({ type: 'positive', message: 'Price item updated', position: 'top' });
        return response.data;
      } catch (error) {
        Notify.create({ type: 'negative', message: error.response?.data?.detail || 'Failed to update item', position: 'top' });
        throw error;
      }
    },

    async createBill(billData) {
      try {
        const response = await billingAPI.createBill(billData);
        Notify.create({
          type: 'positive',
          message: 'Bill created successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to create bill',
          position: 'top',
        });
        throw error;
      }
    },

    async createReceipt(receiptData) {
      try {
        const response = await billingAPI.createReceipt(receiptData);
        Notify.create({
          type: 'positive',
          message: 'Receipt issued successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to issue receipt',
          position: 'top',
        });
        throw error;
      }
    },

    async getEncounterBills(encounterId) {
      try {
        const response = await billingAPI.getEncounterBills(encounterId);
        this.encounterBills = response.data;
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to fetch bills',
          position: 'top',
        });
        throw error;
      }
    },
  },
});

