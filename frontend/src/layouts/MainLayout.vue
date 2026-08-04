<template>
  <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'"></div>
  <q-layout view="hHh lpR fFf" class="layout-glass">
    <q-header class="glass-header hms-app-header">
      <q-toolbar class="hms-toolbar">
        <q-btn
          flat
          dense
          round
          icon="menu"
          class="header-icon-btn"
          @click="drawerOpen = !drawerOpen"
        >
          <q-tooltip>{{ drawerOpen ? 'Hide Sidebar' : 'Show Sidebar' }}</q-tooltip>
        </q-btn>

        <div class="header-brand">
          <img
            src="/logos/ghana-health-service-logo.png"
            :alt="facilityStore.displayName"
            width="28"
            height="28"
            class="header-logo"
          />
        </div>

        <q-space />

        <button type="button" class="command-trigger" @click="showCommandPalette = true">
          <q-icon name="search" size="xs" />
          <span class="command-label gt-xs">Search for anything…</span>
          <kbd class="command-kbd gt-sm">Ctrl K</kbd>
          <q-tooltip>Command palette (Ctrl+K)</q-tooltip>
        </button>

        <div v-if="sessionTimeLeft" class="session-chip">
          <q-icon name="schedule" size="xs" />
          <span :class="sessionTimeLeftMinutes < 5 ? 'text-negative' : ''">
            {{ formatTimeLeft(sessionTimeLeft) }}
          </span>
          <q-tooltip v-if="sessionTimeLeftMinutes > 65">
            You're using an old token. Please log out and log back in to get a 1-hour session.
          </q-tooltip>
        </div>

        <q-btn flat dense no-caps class="header-ghost-btn gt-sm" @click="switchMode">
          Switch mode
          <q-tooltip>Switch application mode</q-tooltip>
        </q-btn>

        <q-btn flat dense no-caps class="header-ghost-btn gt-md" @click="goToProfile">
          {{ authStore.userName }}
          <q-tooltip>Profile and password</q-tooltip>
        </q-btn>

        <q-btn
          flat
          round
          dense
          icon="notifications"
          class="header-icon-btn"
          @click="showNotifications = true"
        >
          <q-badge
            v-if="unreadNotificationCount > 0"
            color="negative"
            :label="unreadNotificationCount > 99 ? '99+' : unreadNotificationCount"
            floating
            rounded
          />
          <q-tooltip>Notifications ({{ unreadNotificationCount }} unread)</q-tooltip>
        </q-btn>

        <q-btn
          flat
          round
          dense
          :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
          class="header-icon-btn"
          @click="themeStore.toggleTheme()"
        >
          <q-tooltip>Toggle {{ themeStore.isDark ? 'Light' : 'Dark' }} Mode</q-tooltip>
        </q-btn>

        <q-btn flat dense no-caps class="header-ghost-btn header-logout" @click="handleLogout">
          Logout
        </q-btn>
      </q-toolbar>
    </q-header>

    <AppSidebar v-model="drawerOpen" />

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>

  <CommandPalette v-model="showCommandPalette" />

  <!-- Notifications Dialog -->
  <q-dialog v-model="showNotifications">
    <q-card class="notifications-dialog-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">Notifications</div>
        <q-space />
        <q-btn flat dense round icon="close" v-close-popup />
      </q-card-section>
      <q-card-section>
        <NotificationsPanel @close="showNotifications = false" @count-updated="loadUnreadNotificationCount" />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useAppModeStore } from '../stores/appMode';
import { useThemeStore } from '../stores/theme';
import { useModuleSettingsStore } from '../stores/moduleSettings';
import { useFacilityStore } from '../stores/facility';
import { useQuasar } from 'quasar';
import { notificationsAPI } from '../services/api';
import NotificationsPanel from '../components/NotificationsPanel.vue';
import CommandPalette from '../components/CommandPalette.vue';
import AppSidebar from '../components/layout/AppSidebar.vue';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const appModeStore = useAppModeStore();
const themeStore = useThemeStore();
const moduleSettingsStore = useModuleSettingsStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);
const showCommandPalette = ref(false);

// Session timer
const sessionTimeLeft = ref(null);
const sessionTimerInterval = ref(null);
const refreshingToken = ref(false);
const showNotifications = ref(false);
const unreadNotificationCount = ref(0);
const notificationPollInterval = ref(null);

// Idle timeout tracking - DISABLED: No idle timeout enforcement
// Users can stay logged in indefinitely, tokens will auto-refresh
// Activity tracking removed - not needed since we're not enforcing idle timeout

// Computed session time in minutes
const sessionTimeLeftMinutes = computed(() => {
  if (!sessionTimeLeft.value) return 0;
  return Math.floor(sessionTimeLeft.value / 60000);
});

// Format time left as HH:MM:SS or MM:SS (for sessions under 1 hour)
const formatTimeLeft = (ms) => {
  if (!ms || ms <= 0) return '00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  // If more than 1 hour, show HH:MM:SS
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  // Otherwise show MM:SS
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// Update session timer
const updateSessionTimer = () => {
  if (!authStore.token) {
    sessionTimeLeft.value = null;
    return;
  }
  
  const expiration = authStore.getTokenExpiration();
  if (!expiration) {
    // If we can't decode expiration, don't log out immediately
    // This could be due to token format issues, not necessarily expiration
    console.warn('Could not decode token expiration, but token exists');
    sessionTimeLeft.value = null;
    return;
  }
  
  const now = Date.now();
  const timeLeft = expiration - now;
  
  // Check if PC clock is significantly ahead of server (more than 1 hour)
  // This indicates a clock synchronization issue, not a real token expiration
  const clockSkew = -timeLeft; // Negative timeLeft means clock is ahead
  const clockSkewHours = clockSkew / (60 * 60 * 1000);
  
  // If clock is more than 1 hour ahead, it's clearly a clock sync issue
  // Don't logout - just show a warning and use a large grace period
  if (clockSkewHours > 1) {
    console.warn('PC clock is significantly ahead of server (', clockSkewHours.toFixed(2), 'hours). This is a clock synchronization issue, not token expiration.');
    // Set a fake positive time left to prevent logout
    // Use the token's expected duration (1 hour) as the time left
    sessionTimeLeft.value = 60 * 60 * 1000; // 1 hour in milliseconds
    return;
  }
  
  // For smaller clock skews, use a dynamic grace period
  // If clock is ahead by less than 1 hour, use a grace period that accounts for it
  const GRACE_PERIOD_MS = Math.max(5 * 60 * 1000, Math.min(clockSkew, 60 * 60 * 1000)); // 5 minutes to 1 hour
  const timeLeftWithGrace = timeLeft + GRACE_PERIOD_MS;
  
  // NO IDLE TIMEOUT ENFORCEMENT - Users can stay logged in indefinitely
  // Token will auto-refresh when it expires
  
  // Always set the time left, even if it's a large value (old 7-day token)
  // Use the actual timeLeft (without grace period) for display
  sessionTimeLeft.value = timeLeft;
  
  // Auto-refresh token when 10 minutes or less remaining OR when token has expired
  // Token expiration is 1 hour, so refresh proactively when 10 minutes remain
  const minutesLeft = timeLeft / (60 * 1000);
  if (!refreshingToken.value) {
    // Refresh proactively if token is about to expire (10 minutes or less) or has expired (with grace period)
    // This ensures users stay logged in seamlessly without interruption
    if ((minutesLeft <= 10 && minutesLeft > 0) || timeLeftWithGrace <= 0) {
      // Refresh token automatically - don't logout users
      refreshToken();
    }
  }
};

// Refresh token - automatically refreshes when token expires (1 hour period)
const refreshToken = async () => {
  if (refreshingToken.value) return;
  
  refreshingToken.value = true;
  try {
    const success = await authStore.refreshToken();
    if (success) {
      // Update timer with new expiration
      updateSessionTimer();
      // Silent refresh - no notification to avoid interrupting user workflow
      console.log('Token refreshed successfully');
    } else {
      // If refresh failed, try again after a short delay
      console.warn('Token refresh failed, will retry...');
      setTimeout(() => {
        if (authStore.isAuthenticated) {
          refreshToken();
        }
      }, 5000); // Retry after 5 seconds
    }
  } catch (error) {
    console.error('Failed to refresh token:', error);
    // If refresh failed, try again after a short delay
    setTimeout(() => {
      if (authStore.isAuthenticated) {
        refreshToken();
      }
    }, 5000); // Retry after 5 seconds
  } finally {
    refreshingToken.value = false;
  }
};

// Idle timeout is completely disabled - users can stay logged in indefinitely
// Token will auto-refresh proactively before expiration (when 10 minutes remain)

// Start session timer
const startSessionTimer = () => {
  // Clear any existing interval
  if (sessionTimerInterval.value) {
    clearInterval(sessionTimerInterval.value);
  }
  
  // Add a small delay before first check to allow token to be fully set
  setTimeout(() => {
    // Update immediately after delay
    updateSessionTimer();
    
    // Update every second
    sessionTimerInterval.value = setInterval(() => {
      updateSessionTimer();
    }, 1000);
  }, 1000); // 1 second delay to allow token to be properly set
};

// Stop session timer
const stopSessionTimer = () => {
  if (sessionTimerInterval.value) {
    clearInterval(sessionTimerInterval.value);
    sessionTimerInterval.value = null;
  }
  // Idle check interval removed - no longer needed
};

const switchMode = () => {
  router.push('/choose-mode');
};

const goToProfile = () => {
  router.push('/profile');
};

const handleLogout = () => {
  $q.dialog({
    title: 'Confirm Logout',
    message: 'Are you sure you want to logout?',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    stopSessionTimer();
    stopNotificationPolling();
    authStore.logout();
    router.push('/login');
  });
};

// Load unread notification count
const loadUnreadNotificationCount = async () => {
  try {
    const response = await notificationsAPI.getUnreadCount();
    unreadNotificationCount.value = response.data.unread_count || 0;
  } catch (error) {
    console.error('Error loading notification count:', error);
  }
};

// Start notification polling
const startNotificationPolling = () => {
  if (notificationPollInterval.value) {
    clearInterval(notificationPollInterval.value);
  }
  // Poll every 30 seconds
  notificationPollInterval.value = setInterval(() => {
    if (authStore.isAuthenticated) {
      loadUnreadNotificationCount();
    }
  }, 30000);
  // Load immediately
  loadUnreadNotificationCount();
};

// Stop notification polling
const stopNotificationPolling = () => {
  if (notificationPollInterval.value) {
    clearInterval(notificationPollInterval.value);
    notificationPollInterval.value = null;
  }
};

// Start timer when component mounts
// Fetch module statuses on mount
const loadModuleStatuses = async () => {
  // Load status for all main modules
  const mainModules = [
    'patients', 'encounters', 'vitals', 'consultation', 'billing',
    'pharmacy', 'lab', 'scan', 'xray', 'claims', 'ipd',
    'price_list', 'inventory', 'staff', 'audit_logs',
    'database', 'mis_reports', 'icd10_mapping', 'wards', 'stores',
    'blood_transfusion', 'additional_services'
  ];
  try {
    await moduleSettingsStore.fetchModuleStatus(mainModules);
  } catch (error) {
    console.error('Error loading module statuses:', error);
  }
};

onMounted(() => {
  loadModuleStatuses();
  // Only set up timer if authenticated
  // This prevents errors on login page where MainLayout might be loaded but not displayed
  if (authStore.isAuthenticated && authStore.token) {
    startSessionTimer();
    startNotificationPolling();
    // No activity tracking needed - idle timeout is disabled
  }
});

// Stop timer when component unmounts
onUnmounted(() => {
  stopSessionTimer();
  stopNotificationPolling();
  // No activity tracking listeners to remove - idle timeout is disabled
});

// Watch for authentication changes
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth && authStore.token) {
    startSessionTimer();
    startNotificationPolling();
    // No activity tracking needed - idle timeout is disabled
  } else {
    stopSessionTimer();
    stopNotificationPolling();
    sessionTimeLeft.value = null;
    unreadNotificationCount.value = 0;
  }
});

// Also watch for token changes
watch(() => authStore.token, (token) => {
  if (token && authStore.isAuthenticated) {
    startSessionTimer();
    startNotificationPolling();
  } else {
    stopSessionTimer();
    stopNotificationPolling();
    sessionTimeLeft.value = null;
    unreadNotificationCount.value = 0;
  }
});
</script>

<style scoped>
.layout-glass {
  position: relative;
}

.notifications-dialog-card {
  width: min(720px, 92vw);
  max-width: 800px;
}

.q-drawer {
  border-right: 1px solid var(--hms-border) !important;
}
</style>

