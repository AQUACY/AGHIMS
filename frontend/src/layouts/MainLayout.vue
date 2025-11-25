<template>
  <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'"></div>
  <q-layout view="hHh lpR fFf" class="layout-glass">
    <q-header elevated class="glass-header text-white">
      <q-toolbar>
        <!-- Hamburger Menu (All Screen Sizes) -->
        <q-btn
          flat
          dense
          round
          icon="menu"
          class="q-mr-sm"
          @click="drawerOpen = !drawerOpen"
        >
          <q-tooltip>{{ drawerOpen ? 'Hide Sidebar' : 'Show Sidebar' }}</q-tooltip>
        </q-btn>
        <q-toolbar-title class="text-weight-bold">
          <img src="../../public/logos/ghana-health-service-logo.png" alt="AGHIMS" width="32px" height="32px" /> 
          ASESEWA GOVERNMENT HOSPITAL
        </q-toolbar-title>
        <q-space />
        <!-- Session Timer -->
        <div v-if="sessionTimeLeft" class="q-mr-md row items-center q-gutter-xs">
          <q-icon name="schedule" size="sm" />
          <span class="text-caption text-weight-medium" :class="sessionTimeLeftMinutes < 5 ? 'text-negative' : 'text-white'">
            {{ formatTimeLeft(sessionTimeLeft) }}
          </span>
          <q-tooltip v-if="sessionTimeLeftMinutes > 65">
            You're using an old token. Please log out and log back in to get a 1-hour session.
          </q-tooltip>
        </div>
        <q-btn
          flat
          :label="authStore.userName"
          class="q-mr-md text-weight-medium glass-button"
          @click="goToProfile"
          style="text-transform: none;"
        >
          <q-tooltip>Click to view profile and change password</q-tooltip>
        </q-btn>
        <q-btn
          flat
          round
          dense
          :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
          class="q-mr-sm glass-button"
          @click="themeStore.toggleTheme()"
        >
          <q-tooltip>Toggle {{ themeStore.isDark ? 'Light' : 'Dark' }} Mode</q-tooltip>
        </q-btn>
        <q-btn
          flat
          icon="logout"
          label="Logout"
          class="glass-button"
          @click="handleLogout"
        />
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawerOpen"
      show-if-above
      :width="300"
      :breakpoint="1024"
      class="glass-drawer"
    >
      <!-- Patient Search Section - Collapsible -->
      <q-expansion-item
        v-model="searchExpanded"
        icon="search"
        label="Search Patient"
        header-class="text-weight-bold glass-text"
        class="q-ma-xs"
      >
        <q-card class="glass-card" flat>
          <q-card-section class="q-pa-sm">
            <!-- Search by Card Number -->
            <q-input
              v-model="searchCardNumber"
              filled
              dense
              label="Card Number"
              class="q-mb-xs"
              @keyup.enter="searchByCardNumber"
              clearable
            >
              <template v-slot:append>
                <q-icon 
                  name="search" 
                  class="cursor-pointer" 
                  @click="searchByCardNumber"
                  :class="{ 'text-primary': searchCardNumber }"
                />
              </template>
            </q-input>
            
            <!-- Search by CCC/Insurance Number -->
            <q-input
              v-model="searchCccNumber"
              filled
              dense
              label="Ghana Card/Insurance #"
              class="q-mb-xs"
              @keyup.enter="searchByCcc"
              clearable
            >
              <template v-slot:append>
                <q-icon 
                  name="search" 
                  class="cursor-pointer" 
                  @click="searchByCcc"
                  :class="{ 'text-primary': searchCccNumber }"
                />
              </template>
            </q-input>
            
            <!-- Search by Name -->
            <q-input
              v-model="searchPatientName"
              filled
              dense
              label="Patient Name"
              class="q-mb-xs"
              @keyup.enter="searchByName"
              clearable
            >
              <template v-slot:append>
                <q-icon 
                  name="search" 
                  class="cursor-pointer" 
                  @click="searchByName"
                  :class="{ 'text-primary': searchPatientName }"
                />
              </template>
            </q-input>
            
            <!-- Search by Contact Number -->
            <q-input
              v-model="searchContactNumber"
              filled
              dense
              label="Contact Number"
              class="q-mb-xs"
              @keyup.enter="searchByContact"
              clearable
            >
              <template v-slot:append>
                <q-icon 
                  name="search" 
                  class="cursor-pointer" 
                  @click="searchByContact"
                  :class="{ 'text-primary': searchContactNumber }"
                />
              </template>
            </q-input>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <q-separator class="q-my-sm" />

      <q-list class="glass-nav-list">
        <q-item-label header class="text-weight-bold q-py-md" style="opacity: 0.9;">
          Navigation
        </q-item-label>

        <q-item
          clickable
          v-ripple
          :to="{ name: 'Dashboard' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="dashboard" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Dashboard</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Records', 'Admin', 'PA', 'Doctor'])"
          clickable
          v-ripple
          :to="{ name: 'PatientRegistration' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="person_add" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Patient Registration</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          clickable
          v-ripple
          :to="{ name: 'EncountersCalendar' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="calendar_month" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Appointment Calendar</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Nurse', 'Doctor', 'PA', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Vitals' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="favorite" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Vitals</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Doctor', 'PA', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Consultation' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="medical_services" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Consultation</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Billing', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Billing' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="receipt" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Billing</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Pharmacy', 'Pharmacy Head', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Pharmacy' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="medication" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Pharmacy</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccess(['Pharmacy', 'Pharmacy Head', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'InventoryDebitManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="inventory_2" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Inventory Debits</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Lab', 'Admin', 'Lab Head'])"
          clickable
          v-ripple
          :to="{ name: 'Lab' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="science" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Lab</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Lab Head', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'LabTemplates' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="description" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Lab Templates</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Scan', 'Scan Head', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Scan' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="biotech" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Scan</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Xray', 'Xray Head', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Xray' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="radio_button_checked" />
          </q-item-section>
          <q-item-section>
            <q-item-label>X-ray</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Claims', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'Claims' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="description" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Claims</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Nurse', 'Doctor', 'PA', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'IPD' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="local_hospital" />
          </q-item-section>
          <q-item-section>
            <q-item-label>IPD</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="canAccess(['Admin', 'Pharmacy Head'])"
          clickable
          v-ripple
          :to="{ name: 'PriceListManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="price_check" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Price List Management</q-item-label>
          </q-item-section>
        </q-item>

        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'StaffManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="people" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Staff Management</q-item-label>
          </q-item-section>
        </q-item>
        
        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'PatientUpload' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="file_upload" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Patient Upload</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'Icd10DrgMapping' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="medical_information" />
          </q-item-section>
          <q-item-section>
            <q-item-label>ICD-10 DRG Mapping</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'AdditionalServicesManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="add_circle" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Additional Services</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'BloodTransfusionTypesManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="bloodtype" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Blood Transfusion Types</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="canAccess(['Lab', 'Admin'])"
          clickable
          v-ripple
          :to="{ name: 'BloodTransfusionLabManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="science" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Blood Transfusion Requests</q-item-label>
          </q-item-section>
        </q-item>
        <q-item
          v-if="authStore.userRole === 'Admin'"
          clickable
          v-ripple
          :to="{ name: 'DatabaseManagement' }"
          class="glass-nav-item"
          active-class="glass-nav-active"
        >
          <q-item-section avatar>
            <q-icon name="storage" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Database Management</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useQuasar } from 'quasar';
import { patientsAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const drawerOpen = ref(true);

// Session timer
const sessionTimeLeft = ref(null);
const sessionTimerInterval = ref(null);
const refreshingToken = ref(false);

// Idle timeout tracking - DISABLED: No idle timeout enforcement
// Users can stay logged in indefinitely, tokens will auto-refresh
const lastActivityTime = ref(Date.now());
const idleCheckInterval = ref(null);

// Computed session time in minutes
const sessionTimeLeftMinutes = computed(() => {
  if (!sessionTimeLeft.value) return 0;
  return Math.floor(sessionTimeLeft.value / 60000);
});

// Format time left as HH:MM:SS or MM:SS (for sessions under 1 hour)
const formatTimeLeft = (ms) => {
  if (!ms || ms <= 0) return '00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  // If more than 1 hour, show HH:MM:SS
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  // Otherwise show MM:SS
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// Update session timer
const updateSessionTimer = () => {
  if (!authStore.token) {
    sessionTimeLeft.value = null;
    return;
  }
  
  const expiration = authStore.getTokenExpiration();
  if (!expiration) {
    // If we can't decode expiration, don't log out immediately
    // This could be due to token format issues, not necessarily expiration
    console.warn('Could not decode token expiration, but token exists');
    sessionTimeLeft.value = null;
    return;
  }
  
  const now = Date.now();
  const timeLeft = expiration - now;
  
  // Check if PC clock is significantly ahead of server (more than 1 hour)
  // This indicates a clock synchronization issue, not a real token expiration
  const clockSkew = -timeLeft; // Negative timeLeft means clock is ahead
  const clockSkewHours = clockSkew / (60 * 60 * 1000);
  
  // If clock is more than 1 hour ahead, it's clearly a clock sync issue
  // Don't logout - just show a warning and use a large grace period
  if (clockSkewHours > 1) {
    console.warn('PC clock is significantly ahead of server (', clockSkewHours.toFixed(2), 'hours). This is a clock synchronization issue, not token expiration.');
    // Set a fake positive time left to prevent logout
    // Use the token's expected duration (1 hour) as the time left
    sessionTimeLeft.value = 60 * 60 * 1000; // 1 hour in milliseconds
    return;
  }
  
  // For smaller clock skews, use a dynamic grace period
  // If clock is ahead by less than 1 hour, use a grace period that accounts for it
  const GRACE_PERIOD_MS = Math.max(5 * 60 * 1000, Math.min(clockSkew, 60 * 60 * 1000)); // 5 minutes to 1 hour
  const timeLeftWithGrace = timeLeft + GRACE_PERIOD_MS;
  
  // NO IDLE TIMEOUT ENFORCEMENT - Users can stay logged in indefinitely
  // Token will auto-refresh when it expires
  
  // Always set the time left, even if it's a large value (old 7-day token)
  // Use the actual timeLeft (without grace period) for display
  sessionTimeLeft.value = timeLeft;
  
  // Auto-refresh token when 5 minutes or less remaining OR when token has expired
  // Token expiration is 1 hour, so refresh when 5 minutes or less remain, or if expired
  const minutesLeft = timeLeft / (60 * 1000);
  if (!refreshingToken.value) {
    // Refresh if token is about to expire (5 minutes or less) or has expired (with grace period)
    if ((minutesLeft <= 5 && minutesLeft > 0) || timeLeftWithGrace <= 0) {
      // Refresh token automatically - don't logout users
      refreshToken();
    }
  }
};

// Refresh token - automatically refreshes when token expires (1 hour period)
const refreshToken = async () => {
  if (refreshingToken.value) return;
  
  refreshingToken.value = true;
  try {
    const success = await authStore.refreshToken();
    if (success) {
      // Update timer with new expiration
      updateSessionTimer();
      // Silent refresh - no notification to avoid interrupting user workflow
      console.log('Token refreshed successfully');
    } else {
      // If refresh failed, try again after a short delay
      console.warn('Token refresh failed, will retry...');
      setTimeout(() => {
        if (authStore.isAuthenticated) {
          refreshToken();
        }
      }, 5000); // Retry after 5 seconds
    }
  } catch (error) {
    console.error('Failed to refresh token:', error);
    // If refresh failed, try again after a short delay
    setTimeout(() => {
      if (authStore.isAuthenticated) {
        refreshToken();
      }
    }, 5000); // Retry after 5 seconds
  } finally {
    refreshingToken.value = false;
  }
};

// Check for idle timeout - DISABLED: No idle timeout enforcement
const checkIdleTimeout = () => {
  // Idle timeout checking is disabled - users can stay logged in indefinitely
  // Token will auto-refresh when it expires
  return;
};

// Track user activity (for reference only - no idle timeout enforcement)
const updateActivity = () => {
  lastActivityTime.value = Date.now();
};

// Start session timer
const startSessionTimer = () => {
  // Clear any existing interval
  if (sessionTimerInterval.value) {
    clearInterval(sessionTimerInterval.value);
  }
  
  // Reset activity tracking
  lastActivityTime.value = Date.now();
  
  // Add a small delay before first check to allow token to be fully set
  setTimeout(() => {
    // Update immediately after delay
    updateSessionTimer();
    
    // Update every second
    sessionTimerInterval.value = setInterval(() => {
      updateSessionTimer();
    }, 1000);
  }, 1000); // 1 second delay to allow token to be properly set
  
  // Idle check interval is disabled - no idle timeout enforcement
};

// Stop session timer
const stopSessionTimer = () => {
  if (sessionTimerInterval.value) {
    clearInterval(sessionTimerInterval.value);
    sessionTimerInterval.value = null;
  }
  if (idleCheckInterval.value) {
    clearInterval(idleCheckInterval.value);
    idleCheckInterval.value = null;
  }
};

// Patient search fields
const searchCardNumber = ref('');
const searchPatientName = ref('');
const searchCccNumber = ref('');
const searchContactNumber = ref('');
const searchingByCard = ref(false);
const searchingByName = ref(false);
const searchingByCcc = ref(false);
const searchingByContact = ref(false);
const searchExpanded = ref(false);

// Search by card number
const searchByCardNumber = async () => {
  if (!searchCardNumber.value || !searchCardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  searchingByCard.value = true;
  try {
    const response = await patientsAPI.getByCard(searchCardNumber.value.trim());
    console.log('Card search response:', response);
    console.log('Response data:', response.data);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    // Handle both array and single object responses
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
      // Single object returned - convert to array
      patients = [response.data];
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.data && typeof response.data.data === 'object' && !Array.isArray(response.data.data)) {
      // Single object in data property
      patients = [response.data.data];
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    console.log('Extracted patients:', patients);
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      return;
    }
    
    // Always go to search results page
    await router.push({
      name: 'PatientSearchResults',
      query: { 
        searchType: 'card',
        searchTerm: searchCardNumber.value.trim(),
        patients: JSON.stringify(patients) 
      }
    });
    // Clear search field
    searchCardNumber.value = '';
  } catch (error) {
    console.error('Card search error:', error);
    console.error('Error response:', error.response);
    console.error('Error data:', error.response?.data);
    
    // Check if it's a 404 or empty response
    if (error.response?.status === 404 || error.response?.status === 200) {
      // API returned empty list or not found - show appropriate message
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
    } else {
      // Actual error occurred
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Failed to search patients',
      });
    }
  } finally {
    searchingByCard.value = false;
  }
};

// Search by CCC/Insurance number
const searchByCcc = async () => {
  if (!searchCccNumber.value || !searchCccNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a Ghana card/insurance number',
    });
    return;
  }

  searchingByCcc.value = true;
  try {
    const response = await patientsAPI.searchByCcc(searchCccNumber.value.trim());
    console.log('CCC search response:', response);
    console.log('Response data:', response.data);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
      patients = [response.data];
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.data && typeof response.data.data === 'object' && !Array.isArray(response.data.data)) {
      patients = [response.data.data];
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    console.log('Extracted patients:', patients);
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that Ghana card/insurance number',
      });
      return;
    }
    
    // Always go to search results page
    await router.push({
      name: 'PatientSearchResults',
      query: { 
        searchType: 'ccc',
        searchTerm: searchCccNumber.value.trim(),
        patients: JSON.stringify(patients) 
      }
    });
    // Clear search field
    searchCccNumber.value = '';
  } catch (error) {
    console.error('CCC search error:', error);
    console.error('Error response:', error.response);
    console.error('Error data:', error.response?.data);
    
    // Check if it's a 404 or empty response
    if (error.response?.status === 404 || error.response?.status === 200) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that Ghana card/insurance number',
      });
    } else {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Failed to search patients',
      });
    }
  } finally {
    searchingByCcc.value = false;
  }
};

// Search by name
const searchByName = async () => {
  if (!searchPatientName.value || !searchPatientName.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a patient name',
    });
    return;
  }

  searchingByName.value = true;
  try {
    const response = await patientsAPI.searchByName(searchPatientName.value.trim());
    console.log('Name search response:', response);
    console.log('Response data:', response.data);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    // Handle both array and single object responses
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
      // Single object returned - convert to array
      patients = [response.data];
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.data && typeof response.data.data === 'object' && !Array.isArray(response.data.data)) {
      // Single object in data property
      patients = [response.data.data];
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    console.log('Extracted patients:', patients);
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that name',
      });
      return;
    }
    
    // Always go to search results page
    await router.push({
      name: 'PatientSearchResults',
      query: { 
        searchType: 'name',
        searchTerm: searchPatientName.value.trim(),
        patients: JSON.stringify(patients) 
      }
    });
    // Clear search field
    searchPatientName.value = '';
  } catch (error) {
    console.error('Name search error:', error);
    console.error('Error response:', error.response);
    console.error('Error data:', error.response?.data);
    
    // Check if it's a 404 or empty response
    if (error.response?.status === 404 || error.response?.status === 200) {
      // API returned empty list or not found - show appropriate message
      $q.notify({
        type: 'info',
        message: 'No patients found with that name',
      });
    } else {
      // Actual error occurred
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Failed to search patients',
      });
    }
  } finally {
    searchingByName.value = false;
  }
};

const searchByContact = async () => {
  if (!searchContactNumber.value || !searchContactNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a contact number',
    });
    return;
  }

  searchingByContact.value = true;
  try {
    const response = await patientsAPI.searchByContact(searchContactNumber.value.trim());
    console.log('Contact search response:', response);
    console.log('Response data:', response.data);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object') {
      // If it's a single object, wrap it in an array
      patients = [response.data];
    }
    
    console.log('Parsed patients:', patients);
    
    if (patients.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No patients found with this contact number',
        position: 'top',
      });
      return;
    }
    
    // Navigate to search results page with patient data
    router.push({
      name: 'PatientSearchResults',
      query: {
        searchType: 'contact',
        searchTerm: searchContactNumber.value.trim(),
        patients: JSON.stringify(patients) 
      }
    });
    // Clear search field
    searchContactNumber.value = '';
  } catch (error) {
    console.error('Contact search error:', error);
    console.error('Error response:', error.response);
    console.error('Error data:', error.response?.data);
    
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to search patients',
      position: 'top',
    });
  } finally {
    searchingByContact.value = false;
  }
};

const canAccess = (roles) => authStore.canAccess(roles);

const goToProfile = () => {
  router.push('/profile');
};

const handleLogout = () => {
  $q.dialog({
    title: 'Confirm Logout',
    message: 'Are you sure you want to logout?',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    stopSessionTimer();
    authStore.logout();
    router.push('/login');
  });
};

// Start timer when component mounts
onMounted(() => {
  if (authStore.isAuthenticated && authStore.token) {
    startSessionTimer();
  }
  
  // Add event listeners for user activity
  const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
  activityEvents.forEach(event => {
    document.addEventListener(event, updateActivity, { passive: true });
  });
});

// Stop timer when component unmounts
onUnmounted(() => {
  stopSessionTimer();
  
  // Remove event listeners
  const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
  activityEvents.forEach(event => {
    document.removeEventListener(event, updateActivity);
  });
  
  // Close warning dialog if open
  if (idleWarningDialog.value) {
    idleWarningDialog.value.hide();
    idleWarningDialog.value = null;
  }
});

// Watch for authentication changes
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth && authStore.token) {
    startSessionTimer();
  } else {
    stopSessionTimer();
    sessionTimeLeft.value = null;
  }
});

// Also watch for token changes
watch(() => authStore.token, (token) => {
  if (token && authStore.isAuthenticated) {
    startSessionTimer();
  } else {
    stopSessionTimer();
    sessionTimeLeft.value = null;
  }
});
</script>

<style scoped>
.layout-glass {
  position: relative;
}

.glass-nav-list {
  padding: 8px;
}

.glass-nav-item {
  margin: 4px 0;
  border-radius: 12px;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
}

.glass-nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(4px);
}

.glass-nav-active {
  background: rgba(46, 139, 87, 0.3) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.5);
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.3);
}

.body--dark .glass-nav-item {
  background: rgba(255, 255, 255, 0.03);
}

.body--dark .glass-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.body--dark .glass-nav-active {
  background: rgba(46, 139, 87, 0.25) !important;
  border: 1px solid rgba(255, 215, 0, 0.4);
  box-shadow: 0 4px 16px rgba(46, 139, 87, 0.4);
}

.q-drawer {
  border-right: none;
}
</style>

