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
        <span class="mode-chip">Inventory</span>
        <LicenseTitleLink />
        <q-space />
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

    <q-drawer
      v-model="drawerOpen"
      show-if-above
      :width="300"
      :breakpoint="1024"
      class="glass-drawer"
    >
      <q-list class="glass-nav-list">
        <q-item-label header class="text-weight-bold q-py-md" style="opacity: 0.9;">
          Inventory Navigation
        </q-item-label>

        <q-item
          clickable
          v-ripple
          :to="{ name: 'InventoryModeDashboard' }"
          exact
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="inventory_2" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Dashboard</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="authStore.canAccessInventoryMode"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeRequisitions' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="shopping_cart" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Requisitions</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="authStore.canAccessInventoryMode"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeReports' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="assessment" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Reports</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="authStore.canAccessInventoryMode"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeWardStock' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="warehouse" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Department/Ward Stock</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeDebits' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="remove_shopping_cart" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Inventory Debits</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="showStoreStockNav"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeStoreStock' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="store" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Store Stock Management</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Admin'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeStoreManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="storefront" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Store Management</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Admin'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeWardManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="meeting_room" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Department Management</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccess(['Admin', 'Pharmacy Head', 'Store Manager'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryModePriceListManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="price_check" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Price List Management</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccess(['Admin'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeStaffManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Staff Management</q-item-label>
          </q-item-section>
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
          <q-item-section>
            <q-item-label>Module Management</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccessAdminOrSuper"
          clickable
          v-ripple
          :to="{ name: 'InventoryFacilitySetup' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="business" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Facility branding</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccessAuditLogs"
          clickable
          v-ripple
          :to="{ name: 'InventoryModeAuditLogs' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="history" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Audit Trail Logs</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';
import { useQuasar } from 'quasar';
import LicenseTitleLink from '../components/LicenseTitleLink.vue';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);
const isSuperAdmin = computed(() => authStore.isSuperAdmin);
const canAccessAdminOrSuper = computed(() => authStore.canAccess(['Admin']) || authStore.isSuperAdmin);
const canAccessAuditLogs = computed(() => authStore.canAccess(['Admin', 'Auditor']));

const canAccess = (roles) => authStore.canAccess(roles);

const showStoreStockNav = computed(() => {
  if (authStore.isSuperAdmin) return true;
  return (
    authStore.canAccess([
      'Admin',
      'Management',
      'Store Manager',
      'Department Head',
      'Pharmacy Head',
      'Pharmacy',
    ]) ||
    Boolean(authStore.user?.has_store_manager_assignment) ||
    Boolean(authStore.user?.has_store_department_head_assignment)
  );
});

const switchMode = () => {
  router.push('/choose-mode');
};

const goToProfile = () => {
  router.push('/inventory-mode/profile');
};

const handleLogout = () => {
  $q.dialog({
    title: 'Confirm Logout',
    message: 'Are you sure you want to logout?',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    authStore.logout();
    router.push('/login');
  });
};
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
