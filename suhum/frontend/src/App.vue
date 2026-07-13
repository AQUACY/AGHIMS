<template>
  <router-view />
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useThemeStore } from './stores/theme';
import { useFacilityStore } from './stores/facility';

const themeStore = useThemeStore();
const facilityStore = useFacilityStore();

function syncDocumentTitle() {
  const name = facilityStore.displayName?.trim();
  document.title = name ? `${name} — Suhum` : 'Suhum';
}

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic().then(syncDocumentTitle);
});

watch(() => facilityStore.displayName, syncDocumentTitle);
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Roboto', '-apple-system', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  overflow-x: hidden;
}

#app {
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 100vh;
}

.glass-card {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(46, 139, 87, 0.3);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(46, 139, 87, 0.25);
  transition: all 0.3s ease;
  color: #1a1a1a !important;
}

.glass-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.4);
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 255, 255, 0.9) !important;
}

.body--dark .glass-card {
  background: rgba(30, 30, 30, 0.85) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  box-shadow: 0 8px 32px 0 rgba(15, 81, 50, 0.4);
  color: rgba(255, 255, 255, 0.95) !important;
}

.body--dark .glass-card:hover {
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.5);
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(35, 35, 35, 0.9) !important;
}

.app-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  overflow: hidden;
}

.light-gradient {
  background: linear-gradient(-45deg, #FFD700, #FF6B35, #2E8B57, #FFD700, #FF6B35);
  background-size: 400% 400%;
}

.dark-gradient {
  background: linear-gradient(-45deg, #1a1a1a, #8B4513, #0F5132, #1a1a1a, #8B4513);
  background-size: 400% 400%;
}

.glass-header {
  background: rgba(46, 139, 87, 0.25) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.3);
}

.body--dark .glass-header {
  background: rgba(15, 81, 50, 0.4) !important;
  border-bottom: 1px solid rgba(255, 215, 0, 0.25);
}

.glass-button {
  background: rgba(46, 139, 87, 0.9) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.5) !important;
  border-radius: 12px;
  color: white !important;
  transition: all 0.3s ease;
  font-weight: 500;
}

.glass-button:hover {
  background: rgba(46, 139, 87, 1) !important;
  transform: scale(1.05);
}

.glass-text {
  color: #1a1a1a !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.95) !important;
}

.q-page-container,
.q-page {
  background: transparent !important;
}

.q-table {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(46, 139, 87, 0.3);
  color: #1a1a1a !important;
}

.body--dark .q-table {
  background: rgba(30, 30, 30, 0.85) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  color: rgba(255, 255, 255, 0.95) !important;
}

/* Filled inputs — visible box + underline so fields read as editable */
.q-field--filled .q-field__control {
  background: #f3f7f5 !important;
  backdrop-filter: none;
  border-radius: 8px 8px 0 0 !important;
  border: 1px solid rgba(46, 139, 87, 0.28) !important;
  border-bottom: 2px solid rgba(46, 139, 87, 0.5) !important;
}

.q-field--filled .q-field__control:hover {
  background: #eaf3ee !important;
  border-color: rgba(46, 139, 87, 0.42) !important;
  border-bottom-color: rgba(46, 139, 87, 0.72) !important;
}

.q-field--filled.q-field--focused .q-field__control,
.q-field--filled.q-field--highlighted .q-field__control {
  background: #ffffff !important;
  border-color: rgba(46, 139, 87, 0.55) !important;
  border-bottom-color: var(--q-primary) !important;
}

.q-field--filled .q-field__control:before {
  border-bottom: none !important;
  background: transparent !important;
}

.q-field--filled.q-field--focused .q-field__control:after,
.q-field--filled.q-field--highlighted .q-field__control:after {
  transform: scale3d(1, 1, 1) !important;
  opacity: 1 !important;
  height: 2px !important;
  background: var(--q-primary) !important;
}

.q-field--filled .q-field__label {
  color: #424242 !important;
  font-weight: 500;
}

.q-field--filled .q-field__native,
.q-field--filled .q-field__input {
  color: #1a1a1a !important;
}

.q-field--filled.q-field--readonly .q-field__control,
.q-field--filled.q-field--disabled .q-field__control {
  background: #ececec !important;
  border-bottom-color: rgba(0, 0, 0, 0.2) !important;
  opacity: 0.85;
}

.body--dark .q-field--filled .q-field__control {
  background: rgba(38, 42, 40, 0.95) !important;
  border: 1px solid rgba(255, 215, 0, 0.22) !important;
  border-bottom: 2px solid rgba(255, 215, 0, 0.45) !important;
}

.body--dark .q-field--filled .q-field__control:hover {
  background: rgba(48, 52, 50, 0.98) !important;
  border-color: rgba(255, 215, 0, 0.35) !important;
  border-bottom-color: rgba(255, 215, 0, 0.65) !important;
}

.body--dark .q-field--filled.q-field--focused .q-field__control,
.body--dark .q-field--filled.q-field--highlighted .q-field__control {
  background: rgba(32, 36, 34, 1) !important;
  border-bottom-color: var(--q-primary) !important;
}

.body--dark .q-field--filled .q-field__label {
  color: rgba(255, 255, 255, 0.75) !important;
}

.body--dark .q-field--filled .q-field__native,
.body--dark .q-field--filled .q-field__input {
  color: rgba(255, 255, 255, 0.95) !important;
}

/* Section cards on edit pages — subtle contrast from inputs */
.q-page .q-card--flat.q-card--bordered {
  background: rgba(255, 255, 255, 0.96) !important;
}

.body--dark .q-page .q-card--flat.q-card--bordered {
  background: rgba(28, 32, 30, 0.96) !important;
}

.body--dark .text-grey-7,
.body--dark .text-grey-6 {
  color: rgba(255, 255, 255, 0.7) !important;
}

.text-grey-7 {
  color: #616161 !important;
}

.text-grey-6 {
  color: #757575 !important;
}
</style>
