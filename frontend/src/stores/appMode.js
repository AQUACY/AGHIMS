import { defineStore } from 'pinia';

const STORAGE_KEY = 'app_mode';

export const APP_MODES = {
  HMS: 'hms',
  COMPANION: 'companion',
  INVENTORY: 'inventory',
};

export const APP_MODE_MODULE_KEYS = {
  [APP_MODES.HMS]: 'mode_hms',
  [APP_MODES.COMPANION]: 'mode_companion',
  [APP_MODES.INVENTORY]: 'mode_inventory',
};

export const useAppModeStore = defineStore('appMode', {
  state: () => ({
    mode: localStorage.getItem(STORAGE_KEY) || APP_MODES.HMS,
  }),

  getters: {
    isHms: (state) => state.mode === APP_MODES.HMS,
    isCompanion: (state) => state.mode === APP_MODES.COMPANION,
    isInventory: (state) => state.mode === APP_MODES.INVENTORY,
    currentMode: (state) => state.mode,
  },

  actions: {
    setMode(mode) {
      if (![APP_MODES.HMS, APP_MODES.COMPANION, APP_MODES.INVENTORY].includes(mode)) return;
      this.mode = mode;
      localStorage.setItem(STORAGE_KEY, mode);
    },
    setHms() {
      this.setMode(APP_MODES.HMS);
    },
    setCompanion() {
      this.setMode(APP_MODES.COMPANION);
    },
    setInventory() {
      this.setMode(APP_MODES.INVENTORY);
    },
  },
});
