<template>
  <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'"></div>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="glass-header text-white">
      <q-toolbar>
        <q-btn flat dense round icon="menu" class="q-mr-sm" @click="drawerOpen = !drawerOpen" />
        <q-toolbar-title class="text-weight-bold ellipsis">
          {{ facilityStore.displayName }}
          <q-badge v-if="facilityStore.facilityCodeDisplay" color="amber-8" text-color="black" class="q-ml-sm">
            {{ facilityStore.facilityCodeDisplay }}
          </q-badge>
        </q-toolbar-title>
        <q-badge color="teal-8" text-color="white" class="q-mr-md">Suhum</q-badge>
        <q-space />
        <q-btn flat :label="authStore.userName" class="q-mr-md" style="text-transform: none;" />
        <q-btn
          flat round dense
          :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
          class="q-mr-sm"
          @click="themeStore.toggleTheme()"
        />
        <q-btn flat icon="logout" label="Logout" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="drawerOpen" show-if-above bordered class="glass-drawer">
      <q-list padding>
        <q-item-label header class="text-weight-bold">Suhum</q-item-label>
        <q-item clickable v-ripple :to="{ name: 'Home' }" exact>
          <q-item-section avatar><q-icon name="dashboard" /></q-item-section>
          <q-item-section><q-item-label>Home</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'PriceListManagement' }">
          <q-item-section avatar><q-icon name="price_check" /></q-item-section>
          <q-item-section><q-item-label>Price list</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'Icd10DrgMapping' }">
          <q-item-section avatar><q-icon name="hub" /></q-item-section>
          <q-item-section><q-item-label>ICD-10 DRG mapping</q-item-label></q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="{ name: 'GhimsXmlImport' }">
          <q-item-section avatar><q-icon name="upload_file" /></q-item-section>
          <q-item-section><q-item-label>Import GHIMS XML</q-item-label></q-item-section>
        </q-item>
        <q-item v-if="authStore.isAdmin" clickable v-ripple :to="{ name: 'UserManagement' }">
          <q-item-section avatar><q-icon name="group" /></q-item-section>
          <q-item-section><q-item-label>User management</q-item-label></q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';

const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const drawerOpen = ref(true);

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
});

function handleLogout() {
  authStore.logout();
  router.push({ name: 'Login' });
}
</script>

<style scoped>
.app-background {
  position: fixed;
  inset: 0;
  z-index: -1;
}
.light-gradient {
  background: linear-gradient(135deg, #e8f4f8 0%, #f5f7fa 50%, #e3f2fd 100%);
}
.dark-gradient {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.glass-header {
  background: rgba(0, 105, 92, 0.92) !important;
  backdrop-filter: blur(8px);
}
.glass-drawer {
  background: rgba(255, 255, 255, 0.95);
}
.body--dark .glass-drawer {
  background: rgba(30, 30, 46, 0.95);
}
</style>
