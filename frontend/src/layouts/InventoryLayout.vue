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
        <q-toolbar-title class="text-weight-bold row items-center no-wrap q-gutter-sm">
          <img src="../../public/logos/ghana-health-service-logo.png" :alt="facilityStore.displayName" width="32px" height="32px" />
          <span class="ellipsis">{{ facilityStore.displayName }} — Inventory</span>
          <q-badge
            v-if="facilityStore.facilityCodeDisplay"
            color="amber-8"
            text-color="black"
            class="text-caption"
          >
            {{ facilityStore.facilityCodeDisplay }}
          </q-badge>
        </q-toolbar-title>
        <q-badge color="amber-8" text-color="black" class="q-mr-md">
          Current Mode: Inventory
        </q-badge>
        <q-space />
        <q-btn
          flat
          icon="swap_horiz"
          label="Switch Mode"
          class="q-mr-sm glass-button"
          @click="switchMode"
        >
          <q-tooltip>Switch application mode</q-tooltip>
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

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);
const isSuperAdmin = computed(() => authStore.isSuperAdmin);
const canAccessAdminOrSuper = computed(() => authStore.canAccess(['Admin']) || authStore.isSuperAdmin);

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

.q-drawer {
  border-right: none;
}
</style>
