<template>
  <router-view />
  <Toaster
    position="top-right"
    :theme="themeStore.isDark ? 'dark' : 'light'"
    :toast-options="{
      class: 'hms-toast',
      duration: 4000,
    }"
  />
</template>

<script setup>
import { onMounted } from 'vue';
import { Toaster } from 'vue-sonner';
import 'vue-sonner/style.css';
import { useThemeStore } from './stores/theme';
import { useFacilityStore } from './stores/facility';

const themeStore = useThemeStore();
const facilityStore = useFacilityStore();

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
});
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--hms-font-sans);
  overflow-x: hidden;
  background-color: var(--hms-bg-primary);
  color: var(--hms-text-primary);
}

#app,
#q-app {
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 100vh;
}

/* ——— Ambient background ——— */
.app-background {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}

.light-gradient,
.dark-gradient {
  background:
    radial-gradient(ellipse 80% 60% at 10% -10%, rgba(59, 130, 246, 0.18), transparent 55%),
    radial-gradient(ellipse 60% 50% at 90% 10%, rgba(6, 182, 212, 0.12), transparent 50%),
    radial-gradient(ellipse 50% 40% at 50% 100%, rgba(59, 130, 246, 0.08), transparent 55%),
    var(--hms-bg-primary);
}

.body--light .light-gradient,
.body--light .dark-gradient {
  background:
    radial-gradient(ellipse 70% 50% at 0% 0%, rgba(59, 130, 246, 0.06), transparent 55%),
    radial-gradient(ellipse 50% 40% at 100% 0%, rgba(6, 182, 212, 0.04), transparent 50%),
    var(--hms-bg-primary);
}

/* ——— Legacy glass aliases → design system ——— */
.glass,
.glass-dark,
.glass-card,
.hms-glass {
  background: var(--hms-glass-bg) !important;
  backdrop-filter: blur(var(--hms-glass-blur)) saturate(var(--hms-glass-saturate));
  -webkit-backdrop-filter: blur(var(--hms-glass-blur)) saturate(var(--hms-glass-saturate));
  border: 1px solid var(--hms-border) !important;
  border-radius: var(--hms-radius-2xl);
  box-shadow: var(--hms-shadow-md), var(--hms-shadow-inner);
  color: var(--hms-text-primary) !important;
  transition:
    transform var(--hms-duration-normal) var(--hms-ease-out),
    box-shadow var(--hms-duration-normal) var(--hms-ease-out),
    border-color var(--hms-duration-normal) var(--hms-ease-out),
    background-color var(--hms-duration-normal) var(--hms-ease-out);
}

.glass-card:hover {
  transform: translateY(-2px);
  border-color: var(--hms-border-strong) !important;
  box-shadow: var(--hms-shadow-lg), var(--hms-shadow-inner);
}

.glass-header {
  background: var(--hms-glass-bg-strong) !important;
  backdrop-filter: blur(24px) saturate(var(--hms-glass-saturate));
  -webkit-backdrop-filter: blur(24px) saturate(var(--hms-glass-saturate));
  border-bottom: 1px solid var(--hms-border) !important;
  box-shadow: var(--hms-shadow-sm) !important;
  color: var(--hms-text-primary) !important;
  min-height: var(--hms-header-height);
}

.glass-drawer {
  background: var(--hms-panel-bg) !important;
  border-right: 1px solid var(--hms-border) !important;
}

.glass-drawer .q-drawer__content {
  background: var(--hms-panel-bg) !important;
}

.glass-button {
  background: var(--hms-accent) !important;
  backdrop-filter: none;
  border: 1px solid transparent !important;
  border-radius: var(--hms-radius-lg) !important;
  color: #fff !important;
  font-weight: 600;
  box-shadow: var(--hms-shadow-sm);
  transition:
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out);
}

.glass-button:hover {
  background: var(--hms-accent-hover) !important;
  transform: translateY(-1px);
  box-shadow: var(--hms-shadow-glow-accent);
}

.q-page-container,
.q-page {
  background: transparent !important;
}

.glass-table,
.q-table {
  background: var(--hms-glass-bg) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--hms-border) !important;
  border-radius: var(--hms-radius-2xl);
  color: var(--hms-text-primary) !important;
  overflow: hidden;
}

.q-table thead th {
  background: var(--hms-surface) !important;
  color: var(--hms-text-secondary) !important;
  font-weight: 600;
  font-size: var(--hms-text-xs);
  letter-spacing: var(--hms-tracking-wide);
  text-transform: uppercase;
}

.q-dialog .q-card {
  background: var(--hms-glass-bg-strong) !important;
  backdrop-filter: blur(24px) saturate(var(--hms-glass-saturate));
  -webkit-backdrop-filter: blur(24px) saturate(var(--hms-glass-saturate));
  border: 1px solid var(--hms-border-strong) !important;
  box-shadow: var(--hms-shadow-lg) !important;
  color: var(--hms-text-primary) !important;
  border-radius: var(--hms-radius-2xl) !important;
}

.glass-text {
  color: var(--hms-text-primary) !important;
  text-shadow: none;
}

.glass-text-muted {
  color: var(--hms-text-secondary) !important;
}

.q-field--filled .q-field__control {
  background: var(--hms-surface) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
}

.q-field--filled .q-field__control:hover {
  background: var(--hms-surface-hover) !important;
  border-color: var(--hms-border-strong);
}

.q-field--filled .q-field__native,
.q-field--filled .q-field__input,
.q-field--filled .q-field__label {
  color: var(--hms-text-primary) !important;
}

.body--dark .q-field--filled .q-field__label {
  color: var(--hms-text-secondary) !important;
}

/* Soften Quasar primary buttons that still use color="primary" without glass-button */
.q-btn.bg-primary {
  border-radius: var(--hms-radius-lg) !important;
}

.notifications-dialog-card {
  width: min(720px, 92vw);
  max-width: 800px;
}

.body--dark .text-grey-7,
.body--dark .text-grey-6,
.body--dark .text-grey {
  color: var(--hms-text-secondary) !important;
}

.body--dark .text-grey-8,
.body--dark .text-grey-9 {
  color: var(--hms-text-muted) !important;
}

/* Sidebar nav items */
.glass-nav-item {
  border-radius: var(--hms-radius-lg) !important;
  margin: 2px 8px;
  color: var(--hms-text-secondary) !important;
  transition: background-color var(--hms-duration-fast) var(--hms-ease-out);
}

.glass-nav-item:hover {
  background: var(--hms-surface-hover) !important;
  color: var(--hms-text-primary) !important;
}

.glass-nav-active {
  background: var(--hms-accent-muted) !important;
  color: var(--hms-accent) !important;
}

.glass-nav-active .q-icon {
  color: var(--hms-accent) !important;
}

/* Sonner toast polish */
.hms-toast {
  font-family: var(--hms-font-sans) !important;
  border-radius: var(--hms-radius-lg) !important;
}

/* Header command trigger */
.command-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid var(--hms-border) !important;
  border-radius: var(--hms-radius-full) !important;
  background: var(--hms-surface) !important;
  color: var(--hms-text-muted) !important;
  text-transform: none !important;
  padding: 0 0.9rem !important;
  min-height: 2.15rem !important;
  min-width: min(280px, 36vw);
  font-size: var(--hms-text-sm);
  font-family: inherit;
  cursor: pointer;
  margin-right: 0.45rem;
  transition:
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    border-color var(--hms-duration-fast) var(--hms-ease-out),
    color var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out);
}

.command-trigger:hover {
  background: var(--hms-panel-bg) !important;
  color: var(--hms-text-secondary) !important;
  border-color: var(--hms-border-strong) !important;
  box-shadow: var(--hms-shadow-sm);
}

@media (max-width: 720px) {
  .command-trigger {
    min-width: 0;
    padding: 0 0.65rem !important;
  }
  .command-trigger .command-label,
  .command-trigger .command-kbd {
    display: none;
  }
}

.command-kbd {
  margin-left: 0.15rem;
  font-family: var(--hms-font-mono);
  font-size: 0.65rem;
  border: 1px solid var(--hms-border);
  border-radius: 4px;
  padding: 0.1rem 0.35rem;
  opacity: 0.8;
}

/* Sleek app header chrome */
.hms-app-header .hms-toolbar {
  min-height: var(--hms-header-height);
  padding: 0 0.75rem;
  gap: 0.35rem;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
  margin-right: 0.5rem;
}

.header-logo {
  border-radius: 8px;
  flex-shrink: 0;
}

.header-title {
  font-weight: 700;
  font-size: var(--hms-text-base);
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
  max-width: 220px;
}

.header-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  border-radius: var(--hms-radius-full);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
}

.header-chip.accent {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}

.header-chip.healthcare {
  background: var(--hms-healthcare-muted);
  color: var(--hms-healthcare);
}

.session-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border-radius: var(--hms-radius-full);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-xs);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  margin-right: 0.25rem;
}

.header-icon-btn {
  color: var(--hms-text-secondary) !important;
}

.header-icon-btn:hover {
  color: var(--hms-text-primary) !important;
  background: var(--hms-surface) !important;
}

.header-ghost-btn {
  color: var(--hms-text-secondary) !important;
  border-radius: var(--hms-radius-lg) !important;
  font-weight: 600 !important;
  padding: 0 0.65rem !important;
  min-height: 2rem !important;
}

.header-ghost-btn:hover {
  color: var(--hms-text-primary) !important;
  background: var(--hms-surface) !important;
}

.header-logout:hover {
  color: var(--hms-critical) !important;
  background: rgba(239, 68, 68, 0.12) !important;
}

/* Form / page section headings on legacy Quasar cards */
.glass-card .text-h6.glass-text,
.q-card .text-h6.glass-text {
  font-size: var(--hms-text-lg) !important;
  font-weight: 650 !important;
  letter-spacing: var(--hms-tracking-tight);
}

@media print {
  .q-layout > .q-header,
  .q-layout > .q-drawer,
  .q-layout > .q-footer,
  .q-toolbar,
  .app-background,
  nav,
  header:not(.print-header),
  aside {
    display: none !important;
  }

  body,
  #app,
  #q-app {
    background: white !important;
  }

  .lab-result-viewer,
  .lab-result-container {
    position: relative !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 20px !important;
    background: white !important;
  }

  .q-btn,
  button:not(.print-header button),
  .no-print {
    display: none !important;
  }

  .print-header {
    display: block !important;
  }

  .q-dialog,
  .q-menu {
    display: none !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .glass-card,
  .glass-button,
  .glass-nav-item {
    transition: none !important;
  }

  .glass-card:hover,
  .glass-button:hover {
    transform: none !important;
  }
}
</style>
