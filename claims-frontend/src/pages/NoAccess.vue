<template>
  <div class="login-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="login-container">
      <q-card class="login-card glass-card" flat>
        <q-card-section class="text-center">
          <q-icon name="business" size="64px" color="primary" class="q-mb-md" />
          <div class="text-h5 text-weight-bold q-mb-md">{{ facilityStore.displayName }}</div>
          <p class="text-body1 q-mb-md">
            This portal is for staff with the <strong>Claims</strong> role who are vetting claims from home.
          </p>
          <p class="text-body2 text-grey-8 q-mb-lg">
            Your account does not have Claims access. Please use the main hospital application on the
            premises for your usual duties.
          </p>
          <q-btn
            unelevated
            label="Back to login"
            class="glass-button"
            :to="{ name: 'Login' }"
          />
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';

const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
  authStore.logout();
});
</script>

<style scoped>
.login-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  position: relative;
  z-index: 1;
}

.login-card {
  width: 100%;
  max-width: 520px;
  padding: 8px;
}
</style>
