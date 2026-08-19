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
            src="../../public/logos/ghana-health-service-logo.png"
            :alt="facilityStore.displayName"
            class="header-logo"
            width="28"
            height="28"
          />
          <span class="header-title ellipsis">{{ facilityStore.displayName }}</span>
        </div>
        <span class="mode-chip">Companion</span>
        <LicenseTitleLink />
        <q-space />
        <div v-if="sessionTimeLeft" class="q-mr-sm row items-center q-gutter-xs">
          <q-icon name="schedule" size="sm" class="text-secondary" />
          <span
            class="text-caption text-weight-medium"
            :class="sessionTimeLeftMinutes < 5 ? 'text-negative' : 'text-secondary'"
          >
            {{ formatTimeLeft(sessionTimeLeft) }}
          </span>
        </div>
        <q-btn flat dense no-caps class="header-ghost-btn gt-sm" @click="switchMode">
          Switch mode
        </q-btn>
        <q-btn flat dense no-caps class="header-ghost-btn gt-md" @click="goToProfile">
          {{ authStore.userName }}
        </q-btn>
        <q-btn
          flat
          dense
          round
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
          dense
          round
          :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
          class="header-icon-btn"
          @click="themeStore.toggleTheme()"
        >
          <q-tooltip>Toggle {{ themeStore.isDark ? 'Light' : 'Dark' }} mode</q-tooltip>
        </q-btn>
        <q-btn flat dense no-caps class="header-ghost-btn header-logout" @click="handleLogout">
          Logout
        </q-btn>
      </q-toolbar>
    </q-header>

    <q-dialog v-model="showNotifications" style="min-width: 600px; max-width: 800px">
      <q-card>
        <q-card-section>
          <div class="row items-center">
            <div class="text-h6">Notifications</div>
            <q-space />
            <q-btn flat dense round icon="close" v-close-popup />
          </div>
        </q-card-section>
        <q-card-section>
          <NotificationsPanel @close="showNotifications = false" @count-updated="loadUnreadNotificationCount" />
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-drawer
      v-model="drawerOpen"
      show-if-above
      :width="300"
      :breakpoint="1024"
      class="glass-drawer"
    >
      <q-list class="glass-nav-list">
        <q-item
          clickable
          v-ripple
          :to="{ name: 'CompanionDashboard' }"
          exact
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="home" />
          </q-item-section>
          <q-item-label>Companion Home</q-item-label>
        </q-item>
        <q-item
          clickable
          v-ripple
          to="/companion/visits"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="list_alt" />
          </q-item-section>
          <q-item-label>Service list</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessRecords"
          clickable
          v-ripple
          to="/companion/visits/create"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="add_circle" />
          </q-item-section>
          <q-item-label>Create service</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessBilling"
          clickable
          v-ripple
          to="/companion/billing"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="receipt_long" />
          </q-item-section>
          <q-item-label>Billing</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessManagement"
          clickable
          v-ripple
          :to="{ name: 'CompanionManagementTransactions' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="receipt_long" />
          </q-item-section>
          <q-item-label>Transactions</q-item-label>
          <q-tooltip>Monetary transactions by date, client, service, user</q-tooltip>
        </q-item>
        <q-item
          v-if="canAccessUndertakings"
          clickable
          v-ripple
          :to="{ name: 'CompanionManagementUndertakings' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="verified_user" />
          </q-item-section>
          <q-item-label>Undertakings</q-item-label>
          <q-tooltip>Approve undertakings and part payments (Companion)</q-tooltip>
        </q-item>
        <q-item
          v-if="canAccessPriceList"
          clickable
          v-ripple
          :to="{ name: 'CompanionPriceListManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="price_check" />
          </q-item-section>
          <q-item-label>Price List Management</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessStaffManagement"
          clickable
          v-ripple
          :to="{ name: 'CompanionStaffManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-label>Staff Management</q-item-label>
        </q-item>
        <q-item
          clickable
          v-ripple
          to="/companion/profile"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="person" />
          </q-item-section>
          <q-item-label>Profile</q-item-label>
        </q-item>
        <q-item
          clickable
          v-ripple
          :to="{ name: 'CompanionMyThemeColors' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="palette" />
          </q-item-section>
          <q-item-label>My theme colors</q-item-label>
        </q-item>
        <q-item
          v-if="isSuperAdmin"
          clickable
          v-ripple
          :to="{ name: 'ModuleManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="settings_applications" />
          </q-item-section>
          <q-item-label>Module Management</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessAdminOrSuper"
          clickable
          v-ripple
          :to="{ name: 'CompanionFacilitySetup' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="business" />
          </q-item-section>
          <q-item-label>Facility branding</q-item-label>
        </q-item>
        <q-item
          v-if="canAccessAuditLogs"
          clickable
          v-ripple
          :to="{ name: 'CompanionAuditLogs' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="history" />
          </q-item-section>
          <q-item-label>Audit Trail Logs</q-item-label>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useAppModeStore } from '../stores/appMode';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';
import { useQuasar } from 'quasar';
import { notificationsAPI } from '../services/api';
import NotificationsPanel from '../components/NotificationsPanel.vue';
import LicenseTitleLink from '../components/LicenseTitleLink.vue';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const appModeStore = useAppModeStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);

const sessionTimeLeft = ref(null);
const sessionTimerInterval = ref(null);
const refreshingToken = ref(false);
const showNotifications = ref(false);
const unreadNotificationCount = ref(0);
const notificationPollInterval = ref(null);

const sessionTimeLeftMinutes = computed(() => {
  if (!sessionTimeLeft.value) return 0;
  return Math.floor(sessionTimeLeft.value / 60000);
});

const canAccessRecords = computed(() => authStore.canAccess(['Records', 'Admin']));
const canAccessBilling = computed(() => authStore.canAccess(['Billing', 'Doctor', 'PA', 'Admin']));
const canAccessManagement = computed(() => authStore.canAccess(['Management', 'Admin']));
const canAccessUndertakings = computed(() => authStore.canAccess(['Management', 'Admin', 'Billing']));
const canAccessAuditLogs = computed(() => authStore.canAccess(['Admin', 'Auditor']));
const canAccessPriceList = computed(() => authStore.canAccess(['Admin', 'Pharmacy Head', 'Store Manager']));
const canAccessStaffManagement = computed(() => authStore.canAccess(['Admin']));
const isSuperAdmin = computed(() => authStore.isSuperAdmin);
const canAccessAdminOrSuper = computed(() => authStore.canAccess(['Admin']) || authStore.isSuperAdmin);

const formatTimeLeft = (ms) => {
  if (!ms || ms <= 0) return '00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

const updateSessionTimer = () => {
  if (!authStore.token) {
    sessionTimeLeft.value = null;
    return;
  }
  const expiration = authStore.getTokenExpiration();
  if (!expiration) {
    sessionTimeLeft.value = null;
    return;
  }
  const now = Date.now();
  const timeLeft = expiration - now;
  const clockSkew = -timeLeft;
  const clockSkewHours = clockSkew / (60 * 60 * 1000);
  if (clockSkewHours > 1) {
    sessionTimeLeft.value = 60 * 60 * 1000;
    return;
  }
  const GRACE_PERIOD_MS = Math.max(5 * 60 * 1000, Math.min(clockSkew, 60 * 60 * 1000));
  const timeLeftWithGrace = timeLeft + GRACE_PERIOD_MS;
  sessionTimeLeft.value = timeLeft;
  const minutesLeft = timeLeft / (60 * 1000);
  if (!refreshingToken.value && ((minutesLeft <= 10 && minutesLeft > 0) || timeLeftWithGrace <= 0)) {
    refreshToken();
  }
};

const refreshToken = async () => {
  if (refreshingToken.value) return;
  refreshingToken.value = true;
  try {
    const success = await authStore.refreshToken();
    if (success) updateSessionTimer();
    else setTimeout(() => { if (authStore.isAuthenticated) refreshToken(); }, 5000);
  } catch (e) {
    setTimeout(() => { if (authStore.isAuthenticated) refreshToken(); }, 5000);
  } finally {
    refreshingToken.value = false;
  }
};

const startSessionTimer = () => {
  if (sessionTimerInterval.value) clearInterval(sessionTimerInterval.value);
  setTimeout(() => {
    updateSessionTimer();
    sessionTimerInterval.value = setInterval(updateSessionTimer, 1000);
  }, 1000);
};

const stopSessionTimer = () => {
  if (sessionTimerInterval.value) {
    clearInterval(sessionTimerInterval.value);
    sessionTimerInterval.value = null;
  }
};

const switchMode = () => {
  router.push('/choose-mode');
};

const goToProfile = () => {
  router.push('/companion/profile');
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

const loadUnreadNotificationCount = async () => {
  try {
    const response = await notificationsAPI.getUnreadCount();
    unreadNotificationCount.value = response.data.unread_count || 0;
  } catch (e) {
    console.error('Error loading notification count:', e);
  }
};

const startNotificationPolling = () => {
  if (notificationPollInterval.value) clearInterval(notificationPollInterval.value);
  notificationPollInterval.value = setInterval(() => {
    if (authStore.isAuthenticated) loadUnreadNotificationCount();
  }, 30000);
  loadUnreadNotificationCount();
};

const stopNotificationPolling = () => {
  if (notificationPollInterval.value) {
    clearInterval(notificationPollInterval.value);
    notificationPollInterval.value = null;
  }
};

onMounted(() => {
  if (authStore.isAuthenticated && authStore.token) {
    startSessionTimer();
    startNotificationPolling();
  }
});

onUnmounted(() => {
  stopSessionTimer();
  stopNotificationPolling();
});

watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth && authStore.token) {
    startSessionTimer();
    startNotificationPolling();
  } else {
    stopSessionTimer();
    stopNotificationPolling();
    sessionTimeLeft.value = null;
    unreadNotificationCount.value = 0;
  }
});

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

.mode-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: var(--hms-text-xs);
  font-weight: 650;
  color: var(--hms-accent);
  background: var(--hms-accent-muted);
  border: 1px solid var(--hms-border);
  white-space: nowrap;
}

.glass-nav-list {
  padding: 0.65rem;
}

.glass-nav-item {
  margin: 0.2rem 0;
  border-radius: var(--hms-radius-lg);
  transition:
    background var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out);
  background: transparent;
  color: var(--hms-text-primary);
}

.glass-nav-item:hover {
  background: var(--hms-surface-hover);
  transform: none;
}

.glass-nav-active {
  background: var(--hms-accent-muted) !important;
  border: 1px solid transparent;
  box-shadow: none;
  color: var(--hms-accent);
}

.q-drawer {
  border-right: none;
}
</style>
