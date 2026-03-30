<template>
  <div class="choose-mode-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="choose-mode-container">
      <div class="text-h5 text-center q-mb-md text-weight-bold glass-text ">
        Choose application mode
      </div>
      <div class="text-subtitle2 text-center q-mb-lg glass-text">
        Select how you want to use the system
      </div>
      <q-banner
        v-if="allModesInactiveForRegularUser"
        class="glass-card q-mb-md full-width mode-support-banner"
      >
        <template v-slot:avatar>
          <q-icon name="warning" color="negative" />
        </template>
        All application modes are currently inactive for this facility. Please contact support service or Super Admin.
      </q-banner>
      <div class="mode-cards row q-col-gutter-x-xs q-col-gutter-y-lg justify-center">
        <q-card
          class="mode-card glass-card col-12 col-sm-6 col-md-4 q-ma-sm"
          flat
          :clickable="canSelectMode(APP_MODES.HMS)"
          :class="{ 'mode-disabled': !canSelectMode(APP_MODES.HMS) }"
          @click="selectMode('hms')"
        >
          <q-card-section class="text-center">
            <q-icon name="medical_services" size="64px" class="q-mb-md" />
            <div class="text-h6 q-mb-sm glass-text">HMS Mode</div>
            <div class="text-body2 glass-text-muted">
              Full Hospital Management System — patient registration, encounters, billing, pharmacy, lab, and all modules.
            </div>
            <q-btn
              unelevated
              label="Enter HMS"
              class="glass-button q-mt-lg"
              :disable="!canSelectMode(APP_MODES.HMS)"
              no-caps
            />
            <div v-if="!canSelectMode(APP_MODES.HMS)" class="text-caption text-negative q-mt-sm">
              Mode inactive - contact support
            </div>
          </q-card-section>
        </q-card>
        <q-card
          class="mode-card glass-card col-12 col-sm-6 col-md-4"
          flat
          :clickable="canSelectMode(APP_MODES.COMPANION)"
          :class="{ 'mode-disabled': !canSelectMode(APP_MODES.COMPANION) }"
          @click="selectMode('companion')"
        >
          <q-card-section class="text-center">
            <q-icon name="handshake" size="64px" class="q-mb-md" />
            <div class="text-h6 q-mb-sm glass-text">Copayment</div>
            <div class="text-body2 glass-text-muted">
              Companion and copayment workflows — dedicated interface and menus for this module.
            </div>
            <q-btn
              unelevated
              label="Enter Companion"
              class="glass-button q-mt-lg"
              :disable="!canSelectMode(APP_MODES.COMPANION)"
              no-caps
            />
            <div v-if="!canSelectMode(APP_MODES.COMPANION)" class="text-caption text-negative q-mt-sm">
              Mode inactive - contact support
            </div>
          </q-card-section>
        </q-card>
        <q-card
          class="mode-card glass-card col-12 col-sm-6 col-md-4"
          flat
          :clickable="canSelectMode(APP_MODES.INVENTORY)"
          :class="{ 'mode-disabled': !canSelectMode(APP_MODES.INVENTORY) }"
          @click="selectMode('inventory')"
        >
          <q-card-section class="text-center">
            <q-icon name="inventory_2" size="64px" class="q-mb-md" />
            <div class="text-h6 q-mb-sm glass-text">Inventory Mode</div>
            <div class="text-body2 glass-text-muted">
              Inventory and store stock workflows only - focused interface for stock operations.
            </div>
            <q-btn
              unelevated
              label="Enter Inventory"
              class="glass-button q-mt-lg"
              :disable="!canSelectMode(APP_MODES.INVENTORY)",.
              no-caps
            />
            <div v-if="!canSelectMode(APP_MODES.INVENTORY)" class="text-caption text-negative q-mt-sm">
              Mode inactive - contact support
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
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

const isSuperAdmin = computed(() => authStore.isSuperAdmin);

const isModeActive = (mode) => {
  const moduleKey = APP_MODE_MODULE_KEYS[mode];
  if (!moduleKey) return true;
  return moduleSettingsStore.isModuleActive(moduleKey);
};

const canSelectMode = (mode) => {
  if (isSuperAdmin.value) return true;
  if (!modeStatusLoaded.value) return false;
  return isModeActive(mode);
};
const allModesInactiveForRegularUser = computed(() => {
  if (isSuperAdmin.value) return false;
  return !isModeActive(APP_MODES.HMS) && !isModeActive(APP_MODES.COMPANION) && !isModeActive(APP_MODES.INVENTORY);
});

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
  } else {
    router.push('/companion');
  }
};

onMounted(async () => {
  try {
    modeStatusLoaded.value = false;
    await moduleSettingsStore.fetchModuleStatus(Object.values(APP_MODE_MODULE_KEYS));
  } catch (error) {
    console.error('Failed to load app mode status:', error);
  } finally {
    modeStatusLoaded.value = true;
  }
});
</script>

<style scoped>
.choose-mode-background {
  position: relative;
  top: 0;
  left: 0;
  width: 100%;
  min-height: 100vh;
  overflow-y: auto;
  z-index: 0;
}

.choose-mode-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  min-height: 100vh;
  padding: 32px 24px 40px;
  position: relative;
  z-index: 1;
}

.mode-cards {
  max-width: 1200px;
  width: 100%;
  padding: 14px 12px 18px;
  row-gap: 18px;
}

.mode-card {
  min-height: 320px;
  display: flex;
  align-items: stretch;
  height: 100%;
}

.mode-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mode-support-banner {
  max-width: 1200px;
}

.mode-card .q-card__section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
