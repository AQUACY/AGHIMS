<template>
  <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'"></div>
  <q-layout view="hHh lpR fFf">
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
          <q-tooltip>{{ drawerOpen ? 'Hide menu' : 'Show menu' }}</q-tooltip>
        </q-btn>
        <q-toolbar-title class="text-weight-bold row items-center no-wrap q-gutter-sm">
          <img
            src="/logos/ghana-health-service-logo.png"
            :alt="facilityStore.displayName"
            width="32"
            height="32"
            @error="onLogoError"
          />
          <span class="ellipsis">{{ facilityStore.displayName }}</span>
          <q-badge
            v-if="facilityStore.facilityCodeDisplay"
            color="amber-8"
            text-color="black"
            class="text-caption"
          >
            {{ facilityStore.facilityCodeDisplay }}
          </q-badge>
        </q-toolbar-title>
        <q-badge color="teal-8" text-color="white" class="q-mr-md">Claims</q-badge>
        <q-space />
        <q-btn
          flat
          :label="authStore.userName"
          class="q-mr-md text-weight-medium glass-button"
          style="text-transform: none;"
        />
        <q-btn
          flat
          round
          dense
          :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
          class="q-mr-sm glass-button"
          @click="themeStore.toggleTheme()"
        />
        <q-btn flat icon="logout" label="Logout" class="glass-button" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="drawerOpen" show-if-above bordered class="glass-drawer">
      <q-list padding>
        <q-item-label header class="text-weight-bold">Claims module</q-item-label>
        <q-item clickable v-ripple :to="{ name: 'Claims' }" exact>
          <q-item-section avatar><q-icon name="dashboard" /></q-item-section>
          <q-item-section><q-item-label>Home</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'ClaimsList' }">
          <q-item-section avatar><q-icon name="description" /></q-item-section>
          <q-item-section><q-item-label>Claims list</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'ClaimItCorrectErrors' }">
          <q-item-section avatar><q-icon name="error_outline" /></q-item-section>
          <q-item-section><q-item-label>Correct errors</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'GhimsXmlImport' }">
          <q-item-section avatar><q-icon name="upload_file" /></q-item-section>
          <q-item-section><q-item-label>Import GHIMS XML</q-item-label></q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';

const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);

function onLogoError(e) {
  e.target.style.display = 'none';
}

function handleLogout() {
  authStore.logout();
  router.push({ name: 'Login' });
}
</script>

<style scoped>
.glass-drawer {
  background: rgba(255, 255, 255, 0.92) !important;
}

.body--dark .glass-drawer {
  background: rgba(25, 25, 25, 0.92) !important;
}
</style>
