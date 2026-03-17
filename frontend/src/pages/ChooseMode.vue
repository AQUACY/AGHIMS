<template>
  <div class="choose-mode-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="choose-mode-container">
      <div class="text-h5 text-center q-mb-md text-weight-bold glass-text">
        Choose application mode
      </div>
      <div class="text-subtitle2 text-center q-mb-lg glass-text">
        Select how you want to use the system
      </div>
      <div class="mode-cards row q-col-gutter-lg justify-center q-ma-md">
        <q-card
          class="mode-card glass-card col-12 col-sm-5 q-ma-md"
          flat
          clickable
          @click="selectMode('hms')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="medical_services" size="64px" class="q-mb-md" />
            <div class="text-h6 q-mb-sm glass-text">HMS Mode</div>
            <div class="text-body2 glass-text-muted">
              Full Hospital Management System — patient registration, encounters, billing, pharmacy, lab, and all modules.
            </div>
            <q-btn
              unelevated
              label="Enter HMS"
              class="glass-button q-mt-lg"
              no-caps
            />
          </q-card-section>
        </q-card>
        <q-card
          class="mode-card glass-card col-12 col-sm-5 q-ma-md"
          flat
          clickable
          @click="selectMode('companion')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="handshake" size="64px" class="q-mb-md" />
            <div class="text-h6 q-mb-sm glass-text">Companion / Copayment</div>
            <div class="text-body2 glass-text-muted">
              Companion and copayment workflows — dedicated interface and menus for this module.
            </div>
            <q-btn
              unelevated
              label="Enter Companion"
              class="glass-button q-mt-lg"
              no-caps
            />
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { useAppModeStore, APP_MODES } from '../stores/appMode';
import { useThemeStore } from '../stores/theme';

const router = useRouter();
const appModeStore = useAppModeStore();
const themeStore = useThemeStore();

const selectMode = (mode) => {
  appModeStore.setMode(mode);
  if (mode === APP_MODES.HMS) {
    router.push('/');
  } else {
    router.push('/companion');
  }
};
</script>

<style scoped>
.choose-mode-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}

.choose-mode-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 24px;
  position: relative;
  z-index: 1;
}

.mode-cards {
  max-width: 900px;
  width: 100%;
}

.mode-card {
  min-height: 280px;
  display: flex;
  align-items: stretch;
}

.mode-card .q-card__section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
