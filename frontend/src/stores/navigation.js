import { defineStore } from 'pinia';

const FAVORITES_KEY = 'hms_nav_favorites';
const RECENTS_KEY = 'hms_nav_recents';
const MAX_RECENTS = 8;

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export const useNavigationStore = defineStore('navigation', {
  state: () => ({
    favoriteIds: readJson(FAVORITES_KEY, []),
    recentIds: readJson(RECENTS_KEY, []),
    collapsed: localStorage.getItem('hms_sidebar_collapsed') === '1',
  }),

  getters: {
    isFavorite: (state) => (id) => state.favoriteIds.includes(id),
  },

  actions: {
    toggleFavorite(id) {
      if (this.favoriteIds.includes(id)) {
        this.favoriteIds = this.favoriteIds.filter((x) => x !== id);
      } else {
        this.favoriteIds = [...this.favoriteIds, id];
      }
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(this.favoriteIds));
    },

    recordVisit(id) {
      if (!id) return;
      this.recentIds = [id, ...this.recentIds.filter((x) => x !== id)].slice(0, MAX_RECENTS);
      localStorage.setItem(RECENTS_KEY, JSON.stringify(this.recentIds));
    },

    toggleCollapsed() {
      this.collapsed = !this.collapsed;
      localStorage.setItem('hms_sidebar_collapsed', this.collapsed ? '1' : '0');
    },

    setCollapsed(value) {
      this.collapsed = !!value;
      localStorage.setItem('hms_sidebar_collapsed', this.collapsed ? '1' : '0');
    },
  },
});
