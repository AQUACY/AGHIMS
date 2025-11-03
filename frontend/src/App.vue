<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue';
import { useThemeStore } from './stores/theme';

const themeStore = useThemeStore();

onMounted(() => {
  themeStore.initTheme();
});
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

/* Glassmorphism base styles */
.glass {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}

.glass-dark {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
}

.glass-card {
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(46, 139, 87, 0.3);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(46, 139, 87, 0.25);
  transition: all 0.3s ease;
}

.glass-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.4);
  border-color: rgba(255, 215, 0, 0.5);
}

.body--dark .glass-card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 215, 0, 0.2);
  box-shadow: 0 8px 32px 0 rgba(15, 81, 50, 0.4);
}

.body--dark .glass-card:hover {
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.5);
  border-color: rgba(255, 215, 0, 0.4);
}

/* Animated gradient background */
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
  /* Ghana Health Service Colors: Yellow, Red, Green */
  background: linear-gradient(-45deg, #FFD700, #FF6B35, #2E8B57, #FFD700, #FF6B35);
  background-size: 400% 400%;
  animation: gradientShift 20s ease infinite;
}

.dark-gradient {
  /* Ghana Health Service Colors - Darker variants */
  background: linear-gradient(-45deg, #1a1a1a, #8B4513, #0F5132, #1a1a1a, #8B4513);
  background-size: 400% 400%;
  animation: gradientShift 20s ease infinite;
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* Glass header */
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
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.4);
}

/* Glass drawer - GHS themed */
.glass-drawer {
  background: rgba(255, 255, 255, 0.1) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid rgba(46, 139, 87, 0.25);
}

.body--dark .glass-drawer {
  background: rgba(15, 81, 50, 0.2) !important;
  border-right: 1px solid rgba(255, 215, 0, 0.2);
}

/* Glass buttons - GHS themed */
.glass-button {
  background: rgba(46, 139, 87, 0.3) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.4) !important;
  border-radius: 12px;
  color: white !important;
  transition: all 0.3s ease;
  font-weight: 500;
}

.glass-button:hover {
  background: rgba(46, 139, 87, 0.5) !important;
  border-color: rgba(255, 215, 0, 0.6) !important;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(46, 139, 87, 0.4);
}

.body--dark .glass-button {
  background: rgba(46, 139, 87, 0.25) !important;
  border: 1px solid rgba(255, 215, 0, 0.3) !important;
}

.body--dark .glass-button:hover {
  background: rgba(46, 139, 87, 0.4) !important;
  border-color: rgba(255, 215, 0, 0.5) !important;
}

/* Smooth transitions */
* {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

/* Page container glass effect */
.q-page-container {
  background: transparent !important;
}

.q-page {
  background: transparent !important;
}

/* Glass tables and data tables - GHS themed */
.glass-table {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(46, 139, 87, 0.25);
  border-radius: 16px;
}

.body--dark .glass-table {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 215, 0, 0.2);
}

/* Glass dialogs - GHS themed */
.q-dialog .q-card {
  background: rgba(255, 255, 255, 0.18) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(46, 139, 87, 0.3);
  box-shadow: 0 8px 32px rgba(46, 139, 87, 0.3);
}

.body--dark .q-dialog .q-card {
  background: rgba(26, 26, 26, 0.6) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  box-shadow: 0 8px 32px rgba(46, 139, 87, 0.4);
}

/* Glass text styles */
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-text-muted {
  color: rgba(255, 255, 255, 0.7);
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.95);
}

.body--dark .glass-text-muted {
  color: rgba(255, 255, 255, 0.8);
}

/* Glass inputs - global */
.q-field--filled .q-field__control {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 12px;
}

.body--dark .q-field--filled .q-field__control {
  background: rgba(255, 255, 255, 0.05);
}

/* Glass tables - GHS themed */
.q-table {
  background: rgba(255, 255, 255, 0.12) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(46, 139, 87, 0.2);
}

.body--dark .q-table {
  background: rgba(26, 26, 26, 0.4) !important;
  border: 1px solid rgba(255, 215, 0, 0.15);
}
</style>

