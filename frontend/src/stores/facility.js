import { defineStore } from 'pinia';
import { facilitySettingsAPI } from '../services/api';
import { clearLicensePublicCache } from '../utils/licensePublicCache';
import { applyFacilityBranding, clearFacilityBranding, normalizeBrandHex } from '../utils/facilityBranding';

export const DEFAULT_FACILITY_DISPLAY_NAME = 'KDG Health App';

function emptyColors() {
  return {
    bgColorLight: null,
    bgColorDark: null,
    accentColor: null,
    textColorLight: null,
    textColorDark: null,
  };
}

function colorsFromPayload(data) {
  return {
    bgColorLight: normalizeBrandHex(data?.bg_color_light),
    bgColorDark: normalizeBrandHex(data?.bg_color_dark),
    accentColor: normalizeBrandHex(data?.accent_color),
    textColorLight: normalizeBrandHex(data?.text_color_light),
    textColorDark: normalizeBrandHex(data?.text_color_dark),
  };
}

export const useFacilityStore = defineStore('facility', {
  state: () => ({
    displayName: DEFAULT_FACILITY_DISPLAY_NAME,
    facilityCode: '',
    // Login / public defaults (facility-level, not applied while signed in)
    publicColors: emptyColors(),
    // Personal theme for the signed-in user
    personalColors: emptyColors(),
    personalThemeLoaded: false,
    loaded: false,
  }),

  getters: {
    facilityCodeDisplay: (state) => {
      const c = (state.facilityCode || '').trim();
      return c || null;
    },
    /** Active colors: personal when loaded for a session, else public (login). */
    bgColorLight: (state) =>
      state.personalThemeLoaded ? state.personalColors.bgColorLight : state.publicColors.bgColorLight,
    bgColorDark: (state) =>
      state.personalThemeLoaded ? state.personalColors.bgColorDark : state.publicColors.bgColorDark,
    accentColor: (state) =>
      state.personalThemeLoaded ? state.personalColors.accentColor : state.publicColors.accentColor,
    textColorLight: (state) =>
      state.personalThemeLoaded
        ? state.personalColors.textColorLight
        : state.publicColors.textColorLight,
    textColorDark: (state) =>
      state.personalThemeLoaded
        ? state.personalColors.textColorDark
        : state.publicColors.textColorDark,
    hasBrandColors: (state) => {
      const c = state.personalThemeLoaded ? state.personalColors : state.publicColors;
      return !!(
        c.bgColorLight ||
        c.bgColorDark ||
        c.accentColor ||
        c.textColorLight ||
        c.textColorDark
      );
    },
  },

  actions: {
    applyIdentity(data) {
      if (!data) return;
      this.displayName =
        (data.display_name || DEFAULT_FACILITY_DISPLAY_NAME).trim() || DEFAULT_FACILITY_DISPLAY_NAME;
      this.facilityCode = (data.facility_code || '').trim();
    },

    applyPublicPayload(data) {
      if (!data) return;
      this.applyIdentity(data);
      this.publicColors = colorsFromPayload(data);
      if (!this.personalThemeLoaded) {
        this.applyBranding();
      }
    },

    applyPersonalPayload(data) {
      this.personalColors = colorsFromPayload(data);
      this.personalThemeLoaded = true;
      this.applyBranding();
    },

    applyBranding(isDark) {
      const c = this.personalThemeLoaded ? this.personalColors : this.publicColors;
      applyFacilityBranding({
        bgColorLight: c.bgColorLight,
        bgColorDark: c.bgColorDark,
        accentColor: c.accentColor,
        textColorLight: c.textColorLight,
        textColorDark: c.textColorDark,
        isDark,
      });
    },

    clearPersonalTheme() {
      this.personalColors = emptyColors();
      this.personalThemeLoaded = false;
      this.applyBranding();
    },

    async fetchPublic() {
      try {
        const response = await facilitySettingsAPI.getPublic();
        this.applyPublicPayload(response.data);
      } catch (error) {
        console.error('Facility settings fetch failed:', error);
        this.displayName = DEFAULT_FACILITY_DISPLAY_NAME;
        this.facilityCode = '';
        this.publicColors = emptyColors();
        if (!this.personalThemeLoaded) {
          clearFacilityBranding();
        }
      } finally {
        this.loaded = true;
      }
    },

    async fetchMyTheme() {
      try {
        const response = await facilitySettingsAPI.getMyTheme();
        this.applyPersonalPayload(response.data);
      } catch (error) {
        console.error('Personal theme fetch failed:', error);
        // Signed in but no prefs / error → use defaults (do not fall back to another user's facility colors)
        this.personalColors = emptyColors();
        this.personalThemeLoaded = true;
        clearFacilityBranding();
      }
    },

    async saveIdentity(payload) {
      const response = await facilitySettingsAPI.update({
        display_name: payload.display_name,
        facility_code: payload.facility_code,
      });
      this.applyIdentity(response.data);
      clearLicensePublicCache();
      return response.data;
    },

    async saveMyTheme(payload) {
      const response = await facilitySettingsAPI.updateMyTheme(payload);
      this.applyPersonalPayload(response.data);
      return response.data;
    },

    /** @deprecated use saveIdentity / saveMyTheme */
    async save(payload) {
      if (payload.display_name != null) {
        await this.saveIdentity({
          display_name: payload.display_name,
          facility_code: payload.facility_code,
        });
      }
      if (
        'bg_color_light' in payload ||
        'bg_color_dark' in payload ||
        'accent_color' in payload ||
        'text_color_light' in payload ||
        'text_color_dark' in payload
      ) {
        await this.saveMyTheme({
          bg_color_light: payload.bg_color_light ?? null,
          bg_color_dark: payload.bg_color_dark ?? null,
          accent_color: payload.accent_color ?? null,
          text_color_light: payload.text_color_light ?? null,
          text_color_dark: payload.text_color_dark ?? null,
        });
      }
      return {
        display_name: this.displayName,
        facility_code: this.facilityCode || null,
        bg_color_light: this.personalColors.bgColorLight,
        bg_color_dark: this.personalColors.bgColorDark,
        accent_color: this.personalColors.accentColor,
        text_color_light: this.personalColors.textColorLight,
        text_color_dark: this.personalColors.textColorDark,
      };
    },
  },
});
