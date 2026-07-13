import { defineStore } from 'pinia';
import { encountersAPI, vitalsAPI, consultationAPI } from '../services/api';
import { Notify } from 'quasar';

export const useEncountersStore = defineStore('encounters', {
  state: () => ({
    currentEncounter: null,
    encounterVitals: null,
    encounterDiagnoses: [],
    encounterPrescriptions: [],
    encounterInvestigations: [],
  }),

  actions: {
    async getEncounter(encounterId) {
      try {
        const response = await encountersAPI.get(encounterId);
        this.currentEncounter = response.data;
        await this.loadEncounterData(encounterId);
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to fetch encounter',
          position: 'top',
        });
        throw error;
      }
    },

    async loadEncounterData(encounterId) {
      try {
        // Load vitals
        try {
          const vitalsResponse = await vitalsAPI.getByEncounter(encounterId);
          this.encounterVitals = vitalsResponse.data;
        } catch (e) {
          this.encounterVitals = null;
        }

        // Load diagnoses
        const diagnosesResponse = await consultationAPI.getDiagnoses(encounterId);
        this.encounterDiagnoses = diagnosesResponse.data;

        // Load prescriptions
        const prescriptionsResponse = await consultationAPI.getPrescriptions(encounterId);
        this.encounterPrescriptions = prescriptionsResponse.data;

        // Load investigations
        const investigationsResponse = await consultationAPI.getInvestigations(encounterId);
        this.encounterInvestigations = investigationsResponse.data;
      } catch (error) {
        console.error('Error loading encounter data:', error);
      }
    },

    async updateStatus(encounterId, newStatus, suppressNotification = false) {
      try {
        const response = await encountersAPI.updateStatus(encounterId, newStatus);
        if (this.currentEncounter?.id === encounterId) {
          this.currentEncounter.status = newStatus;
        }
        if (!suppressNotification) {
          Notify.create({
            type: 'positive',
            message: 'Encounter status updated',
            position: 'top',
          });
        }
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to update encounter status',
          position: 'top',
        });
        throw error;
      }
    },

    async updateEncounter(encounterId, updateData) {
      try {
        const response = await encountersAPI.update(encounterId, updateData);
        if (this.currentEncounter?.id === encounterId) {
          this.currentEncounter = response.data;
        }
        Notify.create({
          type: 'positive',
          message: 'Encounter updated successfully',
          position: 'top',
        });
        return response.data;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to update encounter',
          position: 'top',
        });
        throw error;
      }
    },

    async deleteEncounter(encounterId) {
      try {
        await encountersAPI.delete(encounterId);
        Notify.create({
          type: 'positive',
          message: 'Encounter archived successfully',
          position: 'top',
        });
        return true;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to archive encounter',
          position: 'top',
        });
        throw error;
      }
    },

    clearCurrent() {
      this.currentEncounter = null;
      this.encounterVitals = null;
      this.encounterDiagnoses = [];
      this.encounterPrescriptions = [];
      this.encounterInvestigations = [];
    },
  },
});

