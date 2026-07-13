import { defineStore } from 'pinia';
import { moduleSettingsAPI } from '../services/api';

export const useModuleSettingsStore = defineStore('moduleSettings', {
  state: () => ({
    modules: {},
    loading: false,
    lastFetch: null,
  }),

  getters: {
    isModuleActive: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      return module ? module.is_active : true; // Default to active if not found (backward compatibility)
    },

    canRead: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      if (!module) return true; // Default to allowed
      return module.is_active && module.allow_read;
    },

    canCreate: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      if (!module) return true; // Default to allowed
      return module.is_active && module.allow_create;
    },

    canUpdate: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      if (!module) return true; // Default to allowed
      return module.is_active && module.allow_update;
    },

    canDelete: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      if (!module) return true; // Default to allowed
      return module.is_active && module.allow_delete;
    },

    getModuleStatus: (state) => (moduleKey) => {
      const module = state.modules[moduleKey];
      if (!module) {
        return {
          is_active: true,
          allow_read: true,
          allow_create: true,
          allow_update: true,
          allow_delete: true,
        };
      }
      return {
        is_active: module.is_active,
        allow_read: module.allow_read,
        allow_create: module.allow_create,
        allow_update: module.allow_update,
        allow_delete: module.allow_delete,
      };
    },
  },

  actions: {
    async fetchModuleStatus(moduleKeys) {
      try {
        this.loading = true;
        const keys = Array.isArray(moduleKeys) ? moduleKeys : [moduleKeys];
        const response = await moduleSettingsAPI.getStatusBatch(keys.join(','));
        
        // Update state with fetched modules
        Object.keys(response.data).forEach((key) => {
          this.modules[key] = response.data[key];
        });
        
        this.lastFetch = new Date();
        return response.data;
      } catch (error) {
        console.error('Error fetching module status:', error);
        // On error, default to active (backward compatibility)
        const keys = Array.isArray(moduleKeys) ? moduleKeys : [moduleKeys];
        keys.forEach((key) => {
          if (!this.modules[key]) {
            this.modules[key] = {
              is_active: true,
              allow_read: true,
              allow_create: true,
              allow_update: true,
              allow_delete: true,
            };
          }
        });
        return {};
      } finally {
        this.loading = false;
      }
    },

    async fetchAllModules() {
      try {
        this.loading = true;
        const response = await moduleSettingsAPI.getAll();
        const modules = {};
        response.data.forEach((module) => {
          modules[module.module_key] = {
            is_active: module.is_active,
            allow_read: module.allow_read,
            allow_create: module.allow_create,
            allow_update: module.allow_update,
            allow_delete: module.allow_delete,
          };
        });
        this.modules = modules;
        this.lastFetch = new Date();
        return modules;
      } catch (error) {
        console.error('Error fetching all modules:', error);
        return {};
      } finally {
        this.loading = false;
      }
    },

    async updateModule(moduleKey, data) {
      try {
        const response = await moduleSettingsAPI.update(moduleKey, data);
        // Update local state
        if (this.modules[moduleKey]) {
          Object.assign(this.modules[moduleKey], {
            is_active: response.data.is_active,
            allow_read: response.data.allow_read,
            allow_create: response.data.allow_create,
            allow_update: response.data.allow_update,
            allow_delete: response.data.allow_delete,
          });
        }
        return response.data;
      } catch (error) {
        console.error('Error updating module:', error);
        throw error;
      }
    },

    async toggleModule(moduleKey) {
      try {
        const response = await moduleSettingsAPI.toggle(moduleKey);
        // Update local state
        if (this.modules[moduleKey]) {
          this.modules[moduleKey].is_active = response.data.is_active;
        }
        return response.data;
      } catch (error) {
        console.error('Error toggling module:', error);
        throw error;
      }
    },

    clearCache() {
      this.modules = {};
      this.lastFetch = null;
    },
  },
});
