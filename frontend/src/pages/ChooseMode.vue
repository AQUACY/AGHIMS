<template>
  <div class="choose-shell" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="choose-inner">
      <header class="choose-header">
        <img
          src="/logos/ghana-health-service-logo.png"
          alt=""
          width="40"
          height="40"
          class="choose-logo"
        />
        <h1 class="choose-title">Choose application mode</h1>
        <p class="choose-subtitle">Select how you want to use the system</p>
      </header>

      <div
        v-if="allModesInactiveForRegularUser"
        class="support-banner hms-glass"
        role="alert"
      >
        <AlertTriangle :size="18" class="support-icon" />
        <p>
          All application modes are currently inactive for this facility. Please contact support
          or a Super Admin.
        </p>
      </div>

      <div class="mode-grid">
        <motion.button
          v-for="(mode, index) in modes"
          :key="mode.id"
          type="button"
          class="mode-card hms-glass"
          :class="{ disabled: !mode.enabled }"
          :disabled="!mode.enabled && modeStatusLoaded"
          :initial="reduceMotion ? false : { opacity: 0, y: 12 }"
          :animate="{ opacity: 1, y: 0 }"
          :whileHover="reduceMotion || !mode.enabled ? undefined : { y: -4, scale: 1.015 }"
          :whilePress="reduceMotion || !mode.enabled ? undefined : { scale: 0.985 }"
          :transition="{ delay: index * 0.05, duration: 0.3, ease: [0.16, 1, 0.3, 1] }"
          @click="selectMode(mode.id)"
        >
          <div class="mode-icon" :style="{ color: mode.color, background: mode.bg }">
            <component :is="mode.icon" :size="26" />
          </div>
          <h2 class="mode-name">{{ mode.title }}</h2>
          <p class="mode-desc">{{ mode.description }}</p>
          <span class="mode-cta" :class="{ muted: !mode.enabled }">
            {{ mode.enabled ? mode.cta : mode.disabledReason }}
          </span>
        </motion.button>
      </div>

      <div class="choose-footer">
        <button type="button" class="footer-link" @click="themeStore.toggleTheme()">
          {{ themeStore.isDark ? 'Light mode' : 'Dark mode' }}
        </button>
        <button type="button" class="footer-link" @click="logout">Sign out</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import {
  Stethoscope,
  Handshake,
  Package,
  FileText,
  AlertTriangle,
} from 'lucide-vue-next';
import { useAppModeStore, APP_MODES, APP_MODE_MODULE_KEYS } from '../stores/appMode';
import { useThemeStore } from '../stores/theme';
import { useModuleSettingsStore } from '../stores/moduleSettings';
import { useAuthStore } from '../stores/auth';
import { useQuasar } from 'quasar';

const router = useRouter();
const $q = useQuasar();
const appModeStore = useAppModeStore();
const themeStore = useThemeStore();
const moduleSettingsStore = useModuleSettingsStore();
const authStore = useAuthStore();
const modeStatusLoaded = ref(false);
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

const isSuperAdmin = computed(() => authStore.isSuperAdmin);

const isModeActive = (mode) => {
  const moduleKey = APP_MODE_MODULE_KEYS[mode];
  if (!moduleKey) return true;
  return moduleSettingsStore.isModuleActive(moduleKey);
};

const CLAIMS_ROLES = ['Claims', 'Admin', 'Doctor', 'PA'];

const canSelectClaimsRole = computed(() => isSuperAdmin.value || authStore.canAccess(CLAIMS_ROLES));

const canSelectMode = (mode) => {
  if (isSuperAdmin.value) return true;
  if (!modeStatusLoaded.value) return false;
  if (!isModeActive(mode)) return false;
  if (mode === APP_MODES.INVENTORY && !authStore.canAccessInventoryMode) return false;
  if (mode === APP_MODES.CLAIMS && !canSelectClaimsRole.value) return false;
  return true;
};

const allModesInactiveForRegularUser = computed(() => {
  if (isSuperAdmin.value) return false;
  return (
    !isModeActive(APP_MODES.HMS) &&
    !isModeActive(APP_MODES.COMPANION) &&
    !isModeActive(APP_MODES.INVENTORY)
  );
});

const modes = computed(() => [
  {
    id: APP_MODES.HMS,
    title: 'HMS Mode',
    description:
      'Full Hospital Management System — registration, encounters, billing, pharmacy, lab, and clinical modules.',
    cta: 'Enter HMS',
    icon: Stethoscope,
    color: 'var(--hms-accent)',
    bg: 'var(--hms-accent-muted)',
    enabled: canSelectMode(APP_MODES.HMS),
    disabledReason: 'Mode inactive — contact support',
  },
  {
    id: APP_MODES.COMPANION,
    title: 'Copayment',
    description:
      'Companion and copayment workflows — dedicated interface and menus for this module.',
    cta: 'Enter Companion',
    icon: Handshake,
    color: 'var(--hms-healthcare)',
    bg: 'var(--hms-healthcare-muted)',
    enabled: canSelectMode(APP_MODES.COMPANION),
    disabledReason: 'Mode inactive — contact support',
  },
  {
    id: APP_MODES.INVENTORY,
    title: 'Inventory Mode',
    description:
      'Stores and stock for department IC/deputies, store roles, Management, Pharmacy, and Admin.',
    cta: 'Enter Inventory',
    icon: Package,
    color: 'var(--hms-warning)',
    bg: 'rgba(245, 158, 11, 0.15)',
    enabled: canSelectMode(APP_MODES.INVENTORY),
    disabledReason: 'Mode inactive — contact support',
  },
  {
    id: APP_MODES.CLAIMS,
    title: 'Claims Mode',
    description:
      'NHIA claims — generate and edit claims, correct ClaimIT errors, and import GHIMS XML.',
    cta: 'Enter Claims',
    icon: FileText,
    color: 'var(--hms-info)',
    bg: 'rgba(56, 189, 248, 0.15)',
    enabled: canSelectMode(APP_MODES.CLAIMS),
    disabledReason: !canSelectClaimsRole.value
      ? 'Your role does not have Claims access'
      : 'Claims module inactive — contact support',
  },
]);

const selectMode = (mode) => {
  if (!isSuperAdmin.value && !modeStatusLoaded.value) {
    $q.notify({
      type: 'info',
      message: 'Loading mode availability, please wait...',
      position: 'top',
    });
    return;
  }

  if (!canSelectMode(mode)) {
    $q.notify({
      type: 'warning',
      message: 'This mode is currently inactive for this facility.',
      position: 'top',
    });
    return;
  }
  appModeStore.setMode(mode);
  if (mode === APP_MODES.HMS) {
    router.push('/');
  } else if (mode === APP_MODES.INVENTORY) {
    router.push('/inventory-mode');
  } else if (mode === APP_MODES.CLAIMS) {
    router.push('/claims');
  } else {
    router.push('/companion');
  }
};

const logout = () => {
  authStore.logout();
  router.push('/login');
};

onMounted(async () => {
  themeStore.initTheme();
  try {
    if (authStore.isAuthenticated && authStore.user?.can_access_inventory_mode === undefined) {
      try {
        await authStore.fetchUser();
      } catch (e) {
        void 0;
      }
    }
    modeStatusLoaded.value = false;
    await moduleSettingsStore.fetchModuleStatus([...Object.values(APP_MODE_MODULE_KEYS)]);
  } catch (error) {
    console.error('Failed to load app mode status:', error);
  } finally {
    modeStatusLoaded.value = true;
  }
});
</script>

<style scoped>
.choose-shell {
  min-height: 100vh;
  padding: 2rem 1.25rem 3rem;
}

.choose-inner {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.75rem;
}

.choose-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.65rem;
}

.choose-logo {
  border-radius: 10px;
  box-shadow: var(--hms-shadow-sm);
}

.choose-title {
  margin: 0;
  font-size: var(--hms-text-3xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.choose-subtitle {
  margin: 0;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-base);
}

.support-banner {
  width: 100%;
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 1rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  color: var(--hms-text-primary);
  font-size: var(--hms-text-sm);
}

.support-icon {
  color: var(--hms-critical);
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.mode-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.mode-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  gap: 0.65rem;
  padding: 1.35rem 1.4rem 1.25rem;
  border-radius: var(--hms-radius-2xl);
  border: 1px solid var(--hms-border);
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  transition:
    transform var(--hms-duration-normal) var(--hms-ease-out),
    border-color var(--hms-duration-normal) var(--hms-ease-out),
    box-shadow var(--hms-duration-normal) var(--hms-ease-out);
}

.mode-card:hover:not(.disabled) {
  transform: translateY(-2px);
  border-color: var(--hms-border-strong);
  box-shadow: var(--hms-shadow-lg), var(--hms-shadow-inner);
}

.mode-card:focus-visible {
  outline: 2px solid var(--hms-accent);
  outline-offset: 2px;
}

.mode-card.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mode-icon {
  width: 3rem;
  height: 3rem;
  border-radius: var(--hms-radius-xl);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.mode-name {
  margin: 0;
  font-size: var(--hms-text-xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.mode-desc {
  margin: 0;
  flex: 1;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
  line-height: var(--hms-leading-relaxed);
}

.mode-cta {
  margin-top: 0.5rem;
  font-size: var(--hms-text-sm);
  font-weight: 700;
  color: var(--hms-accent);
}

.mode-cta.muted {
  color: var(--hms-critical);
  font-weight: 600;
}

.choose-footer {
  display: flex;
  gap: 1.25rem;
}

.footer-link {
  border: none;
  background: none;
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  cursor: pointer;
  padding: 0;
}

.footer-link:hover {
  color: var(--hms-accent);
  text-decoration: underline;
}

@media (max-width: 768px) {
  .mode-grid {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .mode-card:hover:not(.disabled) {
    transform: none;
  }
}
</style>
