import { defineStore } from 'pinia';
import { Dark } from 'quasar';
import { useFacilityStore } from './facility';

export const useThemeStore = defineStore('theme', {
  state: () => {
    const savedTheme = localStorage.getItem('theme');
    // Dark-first: default to dark unless user explicitly chose light
    let isDark = true;

    if (savedTheme === 'dark') {
      isDark = true;
    } else if (savedTheme === 'light') {
      isDark = false;
    }

    return {
      isDark,
    };
  },

  getters: {
    currentTheme: (state) => (state.isDark ? 'dark' : 'light'),
  },

  actions: {
    toggleTheme() {
      this.isDark = !this.isDark;
      localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
      this.applyTheme();
    },

    setTheme(theme) {
      this.isDark = theme === 'dark';
      localStorage.setItem('theme', theme);
      this.applyTheme();
    },

    applyTheme() {
      Dark.set(this.isDark);
      document.body.classList.toggle('body--light', !this.isDark);
      document.documentElement.classList.toggle('body--light', !this.isDark);
      document.documentElement.classList.toggle('body--dark', this.isDark);
      // Re-apply facility brand colors for the active mode (or clear to defaults)
      try {
        useFacilityStore().applyBranding(this.isDark);
      } catch {
        /* pinia may not be ready during very early boot */
      }
    },

    initTheme() {
      this.applyTheme();
    },
  },
});
