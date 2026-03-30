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
    userRole: (state) => state.user?.role || null, // Primary role (for layout)
    userName: (state) => state.user?.full_name || state.user?.username || null,
    isSuperAdmin: (state) => {
      const role = (state.user?.role || '').toLowerCase();
      return Boolean(state.user?.is_super_admin) || role === 'super admin' || role === 'superadmin';
    },
    allUserRoles: (state) => {
      // Get all roles (primary + additional)
      if (!state.user) return [];
      const roles = [state.user.role];
      if (state.user.additional_roles && Array.isArray(state.user.additional_roles)) {
        roles.push(...state.user.additional_roles);
      }
      return roles;
    },
    canAccess: (state) => (roles) => {
      if (!state.user) {
        console.warn('canAccess: No user in state');
        return false;
      }
      const userRole = state.user.role;
      const additionalRoles = state.user.additional_roles || [];
      
      // Get all user roles (primary + additional)
      const allUserRoles = [userRole, ...additionalRoles];
      
      // Trim whitespace and compare (handles any whitespace issues)
      const normalizedUserRoles = allUserRoles.map(r => r ? r.trim() : '');
      const normalizedRoles = roles.map(r => r ? r.trim() : '');
      
      // Check if any user role (primary or additional) matches any allowed role
      const hasAccess = normalizedUserRoles.some(userRole => 
        normalizedRoles.includes(userRole) || userRole === 'Admin'
      );
      
      if (!hasAccess) {
        console.warn('canAccess: Access denied', {
          userRole,
          additionalRoles,
          allUserRoles: normalizedUserRoles,
          allowedRoles: roles,
          normalizedRoles,
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
        // Don't logout immediately on fetchUser failure - might be a temporary network issue
        // Only logout if it's a 401 and token is not very new
        // This prevents immediate logout on clock sync issues
        if (error.response?.status === 401) {
          // Check if token was just issued (within last 10 seconds) - might be clock sync issue
          if (this.token) {
            try {
              const parts = this.token.split('.');
              if (parts.length === 3) {
                const base64Url = parts[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(
                  atob(base64)
                    .split('')
                    .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
                );
                const payload = JSON.parse(jsonPayload);
                
                // Check if token was issued very recently (within last 10 seconds)
                if (payload.iat) {
                  const tokenAge = Date.now() - (payload.iat * 1000);
                  if (tokenAge < 10000) {
                    // Token is very new, might be clock sync issue - don't logout
                    console.warn('401 error on fetchUser but token is very new (age:', tokenAge, 'ms), might be clock sync - not logging out');
                    return;
                  }
                }
              }
            } catch (e) {
              // If we can't decode, proceed with logout
              console.warn('Could not decode token to check age:', e);
            }
          }
          
          // Token is old enough or we couldn't check - proceed with logout
          console.warn('401 error on fetchUser, logging out');
          this.logout();
        } else {
          // For non-401 errors, don't logout - might be network issues
          console.warn('Non-401 error on fetchUser, not logging out:', error.response?.status || error.message);
        }
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
        // Validate token format (should have 3 parts separated by dots)
        const parts = this.token.split('.');
        if (parts.length !== 3) {
          console.error('Invalid token format: token should have 3 parts');
          return null;
        }
        
        // Decode JWT token (base64url)
        const base64Url = parts[1];
        if (!base64Url) {
          console.error('Invalid token: missing payload');
          return null;
        }
        
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
        console.warn('Token payload missing exp field');
        return null;
      } catch (error) {
        console.error('Error decoding token:', error);
        // Don't throw - return null to indicate we couldn't decode
        // This prevents immediate logout on token decode errors
        return null;
      }
    },
  },
});

