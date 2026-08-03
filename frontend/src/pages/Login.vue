<template>
  <div class="login-shell" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <motion.div
      class="login-panel"
      :initial="reduceMotion ? false : { opacity: 0, y: 16 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }"
    >
      <div class="login-brand">
        <img
          src="/logos/ghana-health-service-logo.png"
          :alt="facilityStore.displayName"
          width="48"
          height="48"
          class="login-logo"
        />
        <h1 class="login-title">{{ facilityStore.displayName }}</h1>
        <p class="login-subtitle">Sign in to continue to the clinical workspace</p>
        <HmsBadge v-if="facilityStore.facilityCodeDisplay" tone="healthcare">
          {{ facilityStore.facilityCodeDisplay }}
        </HmsBadge>
      </div>

      <HmsCard strong class="login-card" :padding="true">
        <form class="login-form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="field-label">Username</span>
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              required
              class="field-input"
              placeholder="Enter username"
            />
          </label>

          <label class="field">
            <span class="field-label">Password</span>
            <div class="field-password">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                class="field-input"
                placeholder="Enter password"
              />
              <button
                type="button"
                class="field-toggle"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="18" />
                <Eye v-else :size="18" />
              </button>
            </div>
          </label>

          <HmsButton type="submit" variant="primary" size="lg" block :loading="loading">
            Sign in
          </HmsButton>
        </form>

        <div class="login-footer">
          <router-link class="license-link" to="/license-setup">License activation</router-link>
          <button type="button" class="theme-link" @click="themeStore.toggleTheme()">
            {{ themeStore.isDark ? 'Light mode' : 'Dark mode' }}
          </button>
        </div>
      </HmsCard>
    </motion.div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import { Eye, EyeOff } from 'lucide-vue-next';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsCard from '../components/ui/HmsCard.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';

const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

const username = ref('');
const password = ref('');
const loading = ref(false);
const showPassword = ref(false);

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
});

const onSubmit = async () => {
  loading.value = true;
  const success = await authStore.login(username.value, password.value);
  loading.value = false;

  if (success) {
    router.push('/choose-mode');
  }
};
</script>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  position: relative;
}

.login-panel {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.login-brand {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.login-logo {
  border-radius: 12px;
  box-shadow: var(--hms-shadow-md);
}

.login-title {
  font-size: var(--hms-text-2xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
  line-height: var(--hms-leading-tight);
}

.login-subtitle {
  font-size: var(--hms-text-base);
  color: var(--hms-text-secondary);
  max-width: 28ch;
}

.login-card {
  width: 100%;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-label {
  font-size: var(--hms-text-sm);
  font-weight: 600;
  color: var(--hms-text-secondary);
}

.field-input {
  width: 100%;
  height: 2.75rem;
  padding: 0 0.9rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-primary);
  font-size: var(--hms-text-base);
  font-family: inherit;
  outline: none;
  transition:
    border-color var(--hms-duration-fast) var(--hms-ease-out),
    background-color var(--hms-duration-fast) var(--hms-ease-out);
}

.field-input:focus {
  border-color: var(--hms-accent);
  background: var(--hms-surface-hover);
}

.field-input::placeholder {
  color: var(--hms-text-muted);
}

.field-password {
  position: relative;
}

.field-password .field-input {
  padding-right: 2.75rem;
}

.field-toggle {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: var(--hms-text-muted);
  cursor: pointer;
  padding: 0.35rem;
  border-radius: var(--hms-radius-md);
  display: inline-flex;
}

.field-toggle:hover {
  color: var(--hms-text-primary);
  background: var(--hms-surface);
}

.login-footer {
  margin-top: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.license-link,
.theme-link {
  font-size: var(--hms-text-sm);
  color: var(--hms-accent);
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
}

.license-link:hover,
.theme-link:hover {
  text-decoration: underline;
}
</style>
