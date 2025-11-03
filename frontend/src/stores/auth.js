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
    userRole: (state) => state.user?.role || null,
    userName: (state) => state.user?.full_name || state.user?.username || null,
    canAccess: (state) => (roles) => {
      if (!state.user) return false;
      return roles.includes(state.user.role) || state.user.role === 'Admin';
    },
  },

  actions: {
    async login(username, password) {
      try {
        const response = await authAPI.login(username, password);
        const { access_token } = response.data;
        
        this.token = access_token;
        localStorage.setItem('auth_token', access_token);
        
        // Fetch user info
        await this.fetchUser();
        
        this.isAuthenticated = true;
        Notify.create({
          type: 'positive',
          message: 'Login successful',
          position: 'top',
        });
        
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
        console.error('Failed to fetch user:', error);
        this.logout();
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
        if (userStr) {
          this.user = JSON.parse(userStr);
        } else {
          this.fetchUser();
        }
      }
    },
  },
});

