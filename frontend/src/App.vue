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
  background: rgba(255, 255, 255, 0.85) !important; /* More opaque for better contrast in light mode */
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(46, 139, 87, 0.3);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(46, 139, 87, 0.25);
  transition: all 0.3s ease;
  color: #1a1a1a !important; /* Dark text for light mode cards */
}

.glass-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.4);
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 255, 255, 0.9) !important;
}

.body--dark .glass-card {
  background: rgba(30, 30, 30, 0.85) !important; /* More opaque for better contrast in dark mode */
  border: 1px solid rgba(255, 215, 0, 0.3);
  box-shadow: 0 8px 32px 0 rgba(15, 81, 50, 0.4);
  color: rgba(255, 255, 255, 0.95) !important; /* Light text for dark mode cards */
}

.body--dark .glass-card:hover {
  box-shadow: 0 12px 40px 0 rgba(46, 139, 87, 0.5);
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(35, 35, 35, 0.9) !important;
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
  /* animation: gradientShift 20s ease infinite; */
}

.dark-gradient {
  /* Ghana Health Service Colors - Darker variants */
  background: linear-gradient(-45deg, #1a1a1a, #8B4513, #0F5132, #1a1a1a, #8B4513);
  background-size: 400% 400%;
  /* animation: gradientShift 20s ease infinite; */
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

/* Glass buttons - GHS themed with better contrast */
.glass-button {
  background: rgba(46, 139, 87, 0.9) !important; /* More opaque for better visibility */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.5) !important;
  border-radius: 12px;
  color: white !important;
  transition: all 0.3s ease;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(46, 139, 87, 0.3);
}

.glass-button:hover {
  background: rgba(46, 139, 87, 1) !important;
  border-color: rgba(255, 215, 0, 0.7) !important;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(46, 139, 87, 0.5);
}

.body--dark .glass-button {
  background: rgba(46, 139, 87, 0.7) !important;
  border: 1px solid rgba(255, 215, 0, 0.4) !important;
  box-shadow: 0 2px 8px rgba(46, 139, 87, 0.4);
}

.body--dark .glass-button:hover {
  background: rgba(46, 139, 87, 0.85) !important;
  border-color: rgba(255, 215, 0, 0.6) !important;
  box-shadow: 0 4px 12px rgba(46, 139, 87, 0.6);
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

/* Glass tables and data tables - GHS themed with better contrast */
.glass-table {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(46, 139, 87, 0.3);
  border-radius: 16px;
  color: #1a1a1a !important;
}

.body--dark .glass-table {
  background: rgba(30, 30, 30, 0.85) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  color: rgba(255, 255, 255, 0.95) !important;
}

/* Glass dialogs - GHS themed with better contrast */
.q-dialog .q-card {
  background: rgba(255, 255, 255, 0.95) !important; /* More opaque for better visibility */
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(46, 139, 87, 0.3);
  box-shadow: 0 8px 32px rgba(46, 139, 87, 0.3);
  color: #1a1a1a !important;
}

.body--dark .q-dialog .q-card {
  background: rgba(35, 35, 35, 0.95) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  box-shadow: 0 8px 32px rgba(46, 139, 87, 0.4);
  color: rgba(255, 255, 255, 0.95) !important;
}

/* Glass text styles - ensure proper contrast in both modes */
.glass-text {
  color: #1a1a1a !important; /* Dark text for light mode */
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

.glass-text-muted {
  color: #4a4a4a !important; /* Muted dark text for light mode */
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.95) !important; /* Light text for dark mode */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.body--dark .glass-text-muted {
  color: rgba(255, 255, 255, 0.8) !important; /* Muted light text for dark mode */
}

/* Glass inputs - global with better contrast */
.q-field--filled .q-field__control {
  background: rgba(255, 255, 255, 0.8) !important; /* More opaque for better visibility */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(46, 139, 87, 0.2);
}

.q-field--filled .q-field__control:hover {
  background: rgba(255, 255, 255, 0.9) !important;
  border-color: rgba(46, 139, 87, 0.3);
}

.body--dark .q-field--filled .q-field__control {
  background: rgba(40, 40, 40, 0.8) !important;
  border: 1px solid rgba(255, 215, 0, 0.2);
}

.body--dark .q-field--filled .q-field__control:hover {
  background: rgba(45, 45, 45, 0.9) !important;
  border-color: rgba(255, 215, 0, 0.3);
}

/* Glass tables - GHS themed with better contrast */
.q-table {
  background: rgba(255, 255, 255, 0.85) !important; /* More opaque for better visibility */
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(46, 139, 87, 0.3);
  color: #1a1a1a !important;
}

.q-table thead th {
  background: rgba(46, 139, 87, 0.1) !important;
  color: #1a1a1a !important;
  font-weight: 600;
}

.body--dark .q-table {
  background: rgba(30, 30, 30, 0.85) !important;
  border: 1px solid rgba(255, 215, 0, 0.3);
  color: rgba(255, 255, 255, 0.95) !important;
}

.body--dark .q-table thead th {
  background: rgba(46, 139, 87, 0.2) !important;
  color: rgba(255, 255, 255, 0.95) !important;
}

/* Better contrast for text-grey classes in dark mode */
.body--dark .text-grey-7,
.body--dark .text-grey-6,
.body--dark .text-grey {
  color: rgba(255, 255, 255, 0.7) !important; /* Lighter grey for better visibility in dark mode */
}

.body--dark .text-grey-8,
.body--dark .text-grey-9 {
  color: rgba(255, 255, 255, 0.5) !important;
}

/* Ensure text-grey classes have good contrast in light mode */
.text-grey-7 {
  color: #616161 !important; /* Darker grey for better visibility in light mode */
}

.text-grey-6 {
  color: #757575 !important;
}

.text-grey-8 {
  color: #424242 !important;
}

.text-grey-9 {
  color: #212121 !important;
}

/* Global print styles - Hide all navigation and page elements when printing lab results */
@media print {
  /* Hide all layout elements */
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
  
  /* Show only the lab result content */
  body {
    background: white !important;
    margin: 0;
    padding: 0;
  }
  
  #app {
    background: white !important;
  }
  
  /* Ensure lab result viewer is visible and properly positioned */
  .lab-result-viewer,
  .lab-result-container {
    position: relative !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 20px !important;
    background: white !important;
  }
  
  /* Hide all buttons and navigation elements */
  .q-btn,
  button:not(.print-header button),
  .row.items-center,
  .no-print {
    display: none !important;
  }
  
  /* Show only the print header and content */
  .print-header {
    display: block !important;
  }
  
  /* Hide dialog overlays when printing */
  .q-dialog,
  .q-menu {
    display: none !important;
  }
}
</style>

