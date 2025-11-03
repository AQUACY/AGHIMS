import { defineStore } from 'pinia';
import api from '../services/api';

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    stats: {
      todayPatients: 0,
      pendingEncounters: 0,
      unpaidBills: 0,
    },
    loading: false,
  }),

  actions: {
    async fetchStats() {
      this.loading = true;
      try {
        // Note: You may need to add these endpoints to your backend
        // For now, we'll use mock data or existing endpoints
        const today = new Date().toISOString().split('T')[0];
        
        // You can extend this to fetch actual stats from backend
        // For example: const response = await api.get('/dashboard/stats');
        
        // Mock data - replace with actual API calls when endpoints are available
        this.stats = {
          todayPatients: 12,
          pendingEncounters: 5,
          unpaidBills: 3,
        };
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        this.loading = false;
      }
    },
  },
});

