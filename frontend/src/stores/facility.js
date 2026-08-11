import { defineStore } from 'pinia';
import { facilitySettingsAPI } from '../services/api';
import { clearLicensePublicCache } from '../utils/licensePublicCache';
import { applyFacilityBranding, clearFacilityBranding, normalizeBrandHex } from '../utils/facilityBranding';

export const DEFAULT_FACILITY_DISPLAY_NAME = 'KDG Health App';

export const useFacilityStore = defineStore('facility', {
  state: () => ({
    displayName: DEFAULT_FACILITY_DISPLAY_NAME,
    facilityCode: '',
    bgColorLight: null,
    bgColorDark: null,
    accentColor: null,
    textColorLight: null,
    textColorDark: null,
    loaded: false,
  }),

  getters: {
    facilityCodeDisplay: (state) => {
      const c = (state.facilityCode || '').trim();
      return c || null;
    },
    hasBrandColors: (state) =>
      !!(
        state.bgColorLight ||
        state.bgColorDark ||
        state.accentColor ||
        state.textColorLight ||
        state.textColorDark
      ),
  },

  actions: {
    applyPayload(data) {
      if (!data) return;
      this.displayName =
        (data.display_name || DEFAULT_FACILITY_DISPLAY_NAME).trim() || DEFAULT_FACILITY_DISPLAY_NAME;
      this.facilityCode = (data.facility_code || '').trim();
      this.bgColorLight = normalizeBrandHex(data.bg_color_light);
      this.bgColorDark = normalizeBrandHex(data.bg_color_dark);
      this.accentColor = normalizeBrandHex(data.accent_color);
      this.textColorLight = normalizeBrandHex(data.text_color_light);
      this.textColorDark = normalizeBrandHex(data.text_color_dark);
      this.applyBranding();
    },

    applyBranding(isDark) {
      applyFacilityBranding({
        bgColorLight: this.bgColorLight,
        bgColorDark: this.bgColorDark,
        accentColor: this.accentColor,
        textColorLight: this.textColorLight,
        textColorDark: this.textColorDark,
        isDark,
      });
    },

    async fetchPublic() {
      try {
        const response = await facilitySettingsAPI.getPublic();
        this.applyPayload(response.data);
      } catch (error) {
        console.error('Facility settings fetch failed:', error);
        this.displayName = DEFAULT_FACILITY_DISPLAY_NAME;
        this.facilityCode = '';
        this.bgColorLight = null;
        this.bgColorDark = null;
        this.accentColor = null;
        this.textColorLight = null;
        this.textColorDark = null;
        clearFacilityBranding();
      } finally {
        this.loaded = true;
      }
    },

    async save(payload) {
      const response = await facilitySettingsAPI.update(payload);
      this.applyPayload(response.data);
      clearLicensePublicCache();
      return response.data;
    },
  },
});
