import { defineStore } from 'pinia';
import { patientsAPI } from '../services/api';
import { Notify } from 'quasar';

export const usePatientsStore = defineStore('patients', {
  state: () => ({
    currentPatient: null,
    searchResults: [],
  }),

  actions: {
    async createPatient(patientData) {
      try {
        const response = await patientsAPI.create(patientData);
        Notify.create({
          type: 'positive',
          message: 'Patient registered successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to register patient',
          position: 'top',
        });
        throw error;
      }
    },

    async getPatientByCard(cardNumber) {
      try {
        const response = await patientsAPI.getByCard(cardNumber);
        this.currentPatient = response.data;
        return response.data;
      } catch (error) {
        if (error.response?.status === 404) {
          this.currentPatient = null;
          return null;
        }
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to fetch patient',
          position: 'top',
        });
        throw error;
      }
    },

    async updatePatient(patientId, patientData) {
      try {
        const response = await patientsAPI.update(patientId, patientData);
        Notify.create({
          type: 'positive',
          message: 'Patient updated successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to update patient',
          position: 'top',
        });
        throw error;
      }
    },

    async createEncounter(patientId, serviceType, cccNumber = null, procedureGDrgCode = null, procedureName = null) {
      try {
        const response = await patientsAPI.createEncounter(patientId, serviceType, cccNumber, procedureGDrgCode, procedureName);
        Notify.create({
          type: 'positive',
          message: 'Encounter created successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to create encounter',
          position: 'top',
        });
        throw error;
      }
    },
  },
});

