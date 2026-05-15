<template>
  <div class="login-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="login-container">
      <q-card class="login-card glass-card" flat>
        <q-card-section>
          <div class="text-h5 text-center q-mb-md text-weight-bold">
            {{ facilityStore.displayName }}
          </div>
          <div class="text-subtitle2 text-center q-mb-lg">Claims portal — sign in to continue</div>
          <div v-if="facilityStore.facilityCodeDisplay" class="text-caption text-center q-mb-md">
            Facility code: <strong>{{ facilityStore.facilityCodeDisplay }}</strong>
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="onSubmit" class="q-gutter-md">
            <q-input
              v-model="username"
              filled
              label="Username"
              lazy-rules
              :rules="[(val) => !!val || 'Please enter username']"
            />
            <q-input
              v-model="password"
              filled
              type="password"
              label="Password"
              lazy-rules
              :rules="[(val) => !!val || 'Please enter password']"
            />
            <div class="q-mt-lg">
              <q-btn
                unelevated
                label="Login"
                type="submit"
                class="full-width glass-button"
                :loading="loading"
                style="font-weight: 600;"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </div>
  </div>
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

const username = ref('');
const password = ref('');
const loading = ref(false);

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
  if (authStore.isAuthenticated && authStore.hasClaimsRole) {
    router.replace({ name: 'Claims' });
  } else if (authStore.isAuthenticated) {
    router.replace({ name: 'NoAccess' });
  }
});

const onSubmit = async () => {
  loading.value = true;
  const success = await authStore.login(username.value, password.value);
  loading.value = false;
  if (!success) return;
  if (authStore.hasClaimsRole) {
    router.push({ name: 'Claims' });
  } else {
    authStore.logout();
    router.push({ name: 'NoAccess' });
  }
};
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
  max-width: 420px;
  padding: 8px;
}
</style>
