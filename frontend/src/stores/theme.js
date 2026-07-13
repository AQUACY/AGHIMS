import { defineStore } from 'pinia';
import { Dark } from 'quasar';

export const useThemeStore = defineStore('theme', {
  state: () => {
    // Check localStorage first, then system preference
    const savedTheme = localStorage.getItem('theme');
    let isDark = false;
    
    if (savedTheme === 'dark') {
      isDark = true;
    } else if (savedTheme === 'light') {
      isDark = false;
    } else {
      // Default to system preference
      isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    
    return {
      isDark,
    };
  },

  getters: {
    currentTheme: (state) => state.isDark ? 'dark' : 'light',
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
    },

    initTheme() {
      this.applyTheme();
    },
  },
});

