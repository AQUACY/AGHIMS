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
      if (!state.user) {
        console.warn('canAccess: No user in state');
        return false;
      }
      const userRole = state.user.role;
      // Trim whitespace and compare (handles any whitespace issues)
      const normalizedUserRole = userRole ? userRole.trim() : '';
      const normalizedRoles = roles.map(r => r ? r.trim() : '');
      const hasAccess = normalizedRoles.includes(normalizedUserRole) || normalizedUserRole === 'Admin';
      if (!hasAccess) {
        console.warn('canAccess: Access denied', {
          userRole,
          normalizedUserRole,
          allowedRoles: roles,
          normalizedRoles,
          rolesIncludes: normalizedRoles.includes(normalizedUserRole),
          isAdmin: normalizedUserRole === 'Admin',
          roleComparison: normalizedRoles.map(r => `"${r}" === "${normalizedUserRole}": ${r === normalizedUserRole}`)
        });
      }
      return hasAccess;
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

    async refreshToken() {
      try {
        const response = await authAPI.refreshToken();
        const { access_token } = response.data;
        
        this.token = access_token;
        localStorage.setItem('auth_token', access_token);
        
        return true;
      } catch (error) {
        console.error('Failed to refresh token:', error);
        // If refresh fails, logout user
        this.logout();
        return false;
      }
    },

    getTokenExpiration() {
      if (!this.token) return null;
      
      try {
        // Decode JWT token (base64url)
        const base64Url = this.token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
          atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        );
        const payload = JSON.parse(jsonPayload);
        
        // Return expiration timestamp (in seconds, convert to milliseconds)
        if (payload.exp) {
          return payload.exp * 1000; // Convert to milliseconds
        }
        return null;
      } catch (error) {
        console.error('Error decoding token:', error);
        return null;
      }
    },
  },
});

