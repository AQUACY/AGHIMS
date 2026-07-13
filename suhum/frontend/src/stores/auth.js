import { defineStore } from 'pinia';
import { authAPI } from '../services/api';
import { Notify } from 'quasar';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('auth_token') || null,
    isAuthenticated: !!localStorage.getItem('auth_token'),
  }),

  getters: {
    userName: (state) => state.user?.full_name || state.user?.username || null,
    isAdmin: (state) => !!state.user?.is_admin,
  },

  actions: {
    async login(username, password) {
      try {
        const response = await authAPI.login(username, password);
        const { access_token } = response.data;
        this.token = access_token;
        localStorage.setItem('auth_token', access_token);
        await this.fetchUser();
        this.isAuthenticated = true;
        Notify.create({ type: 'positive', message: 'Login successful', position: 'top' });
        return true;
      } catch (error) {
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Login failed',
          position: 'top',
        });
        return false;
      }
    },

    async fetchUser() {
      try {
        const response = await authAPI.getMe();
        this.user = response.data;
        localStorage.setItem('user', JSON.stringify(response.data));
      } catch (error) {
        if (error.response?.status === 401) this.logout();
      }
    },

    logout() {
      this.user = null;
      this.token = null;
      this.isAuthenticated = false;
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
    },

    initAuth() {
      const token = localStorage.getItem('auth_token');
      const userStr = localStorage.getItem('user');
      if (token) {
        this.token = token;
        this.isAuthenticated = true;
        if (userStr) this.user = JSON.parse(userStr);
        else this.fetchUser();
      }
    },
  },
});
