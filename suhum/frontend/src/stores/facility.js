import { defineStore } from 'pinia';
import { facilitySettingsAPI } from '../services/api';

export const DEFAULT_FACILITY_DISPLAY_NAME = 'Suhum';

export const useFacilityStore = defineStore('facility', {
  state: () => ({
    displayName: DEFAULT_FACILITY_DISPLAY_NAME,
    facilityCode: '',
    loaded: false,
  }),

  getters: {
    facilityCodeDisplay: (state) => {
      const c = (state.facilityCode || '').trim();
      return c || null;
    },
  },

  actions: {
    applyPayload(data) {
      if (!data) return;
      this.displayName =
        (data.facility_name || DEFAULT_FACILITY_DISPLAY_NAME).trim() || DEFAULT_FACILITY_DISPLAY_NAME;
      this.facilityCode = (data.facility_code || '').trim();
    },

    async fetchPublic() {
      try {
        const response = await facilitySettingsAPI.getPublic();
        this.applyPayload(response.data);
      } catch {
        this.displayName = DEFAULT_FACILITY_DISPLAY_NAME;
        this.facilityCode = '';
      } finally {
        this.loaded = true;
      }
    },
  },
});
