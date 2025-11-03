<template>
  <div class="login-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="login-container">
      <q-card class="login-card glass-card" flat>
        <q-card-section>
          <div class="text-h5 text-center q-mb-md text-weight-bold" style="color: rgba(255, 255, 255, 0.95);">
            Hospital Management System
          </div>
          <div class="text-subtitle2 text-center q-mb-lg" style="color: rgba(255, 255, 255, 0.7);">
            Sign in to continue
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
              class="glass-input"
            />

            <q-input
              v-model="password"
              filled
              type="password"
              label="Password"
              lazy-rules
              :rules="[(val) => !!val || 'Please enter password']"
              class="glass-input"
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

const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();

const username = ref('');
const password = ref('');
const loading = ref(false);

onMounted(() => {
  themeStore.initTheme();
});

const onSubmit = async () => {
  loading.value = true;
  const success = await authStore.login(username.value, password.value);
  loading.value = false;
  
  if (success) {
    router.push('/');
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

.glass-input {
  background: rgba(255, 255, 255, 0.1) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 12px;
}

.glass-input :deep(.q-field__control) {
  background: rgba(255, 255, 255, 0.1) !important;
  color: rgba(255, 255, 255, 0.9) !important;
}

.glass-input :deep(.q-field__native) {
  color: rgba(255, 255, 255, 0.9) !important;
}

.glass-input :deep(.q-field__label) {
  color: rgba(255, 255, 255, 0.7) !important;
}

.glass-input :deep(.q-field__control:before) {
  border-color: rgba(46, 139, 87, 0.4) !important;
}

.glass-input :deep(.q-field__control:hover:before) {
  border-color: rgba(255, 215, 0, 0.6) !important;
}

.body--dark .glass-input {
  background: rgba(255, 255, 255, 0.05) !important;
}

.body--dark .glass-input :deep(.q-field__control) {
  background: rgba(255, 255, 255, 0.05) !important;
}
</style>

