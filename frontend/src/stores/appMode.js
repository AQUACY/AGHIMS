import { defineStore } from 'pinia';

const STORAGE_KEY = 'app_mode';

export const APP_MODES = {
  HMS: 'hms',
  COMPANION: 'companion',
};

export const useAppModeStore = defineStore('appMode', {
  state: () => ({
    mode: localStorage.getItem(STORAGE_KEY) || APP_MODES.HMS,
  }),

  getters: {
    isHms: (state) => state.mode === APP_MODES.HMS,
    isCompanion: (state) => state.mode === APP_MODES.COMPANION,
    currentMode: (state) => state.mode,
  },

  actions: {
    setMode(mode) {
      if (mode !== APP_MODES.HMS && mode !== APP_MODES.COMPANION) return;
      this.mode = mode;
      localStorage.setItem(STORAGE_KEY, mode);
    },
    setHms() {
      this.setMode(APP_MODES.HMS);
    },
    setCompanion() {
      this.setMode(APP_MODES.COMPANION);
    },
  },
});
