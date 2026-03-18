<template>
  <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'"></div>
  <q-layout view="hHh lpR fFf" class="layout-glass">
    <q-header elevated class="glass-header text-white">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          class="q-mr-sm"
          @click="drawerOpen = !drawerOpen"
        >
          <q-tooltip>{{ drawerOpen ? 'Hide Sidebar' : 'Show Sidebar' }}</q-tooltip>
        </q-btn>
        <q-toolbar-title class="text-weight-bold">
          <img src="../../public/logos/ghana-health-service-logo.png" alt="AGHIMS" width="32px" height="32px" />
          ASESEWA GOVERNMENT HOSPITAL — Companion
        </q-toolbar-title>
        <q-space />
        <div v-if="sessionTimeLeft" class="q-mr-md row items-center q-gutter-xs">
          <q-icon name="schedule" size="sm" />
          <span class="text-caption text-weight-medium" :class="sessionTimeLeftMinutes < 5 ? 'text-negative' : 'text-white'">
            {{ formatTimeLeft(sessionTimeLeft) }}
          </span>
        </div>
        <q-btn
          flat
          icon="swap_horiz"
          label="HMS Mode"
          class="q-mr-sm glass-button"
          @click="switchToHms"
        >
          <q-tooltip>Switch to full Hospital Management System</q-tooltip>
        </q-btn>
        <q-btn
          flat
          :label="authStore.userName"
          class="q-mr-md text-weight-medium glass-button"
          @click="goToProfile"
          style="text-transform: none;"
        >
          <q-tooltip>Click to view profile and change password</q-tooltip>
        </q-btn>
        <q-btn
          flat
          round
          dense
          icon="notifications"
          class="q-mr-sm glass-button"
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
          class="q-mr-sm glass-button"
          @click="themeStore.toggleTheme()"
        >
          <q-tooltip>Toggle {{ themeStore.isDark ? 'Light' : 'Dark' }} Mode</q-tooltip>
        </q-btn>
        <q-btn
          flat
          icon="logout"
          label="Logout"
          class="glass-button"
          @click="handleLogout"
        />
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
import { useAppModeStore, APP_MODES } from '../stores/appMode';
import { useThemeStore } from '../stores/theme';
import { useQuasar } from 'quasar';
import { notificationsAPI } from '../services/api';
import NotificationsPanel from '../components/NotificationsPanel.vue';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const appModeStore = useAppModeStore();
const themeStore = useThemeStore();
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

const switchToHms = () => {
  appModeStore.setMode(APP_MODES.HMS);
  router.push('/');
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

.glass-nav-list {
  padding: 8px;
}

.glass-nav-item {
  margin: 4px 0;
  border-radius: 12px;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
}

.glass-nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(4px);
}

.glass-nav-active {
  background: rgba(46, 139, 87, 0.3) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.5);
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.3);
}

.body--dark .glass-nav-item {
  background: rgba(255, 255, 255, 0.03);
}

.body--dark .glass-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.body--dark .glass-nav-active {
  background: rgba(46, 139, 87, 0.25) !important;
  border: 1px solid rgba(255, 215, 0, 0.4);
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.4);
}

.q-drawer {
  border-right: none;
}
</style>
