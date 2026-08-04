<script setup>
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import {
  Star,
  Clock,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Building2,
  ShieldCheck,
} from 'lucide-vue-next';
import { useAuthStore } from '../../stores/auth';
import { useAppModeStore } from '../../stores/appMode';
import { useModuleSettingsStore } from '../../stores/moduleSettings';
import { useNavigationStore } from '../../stores/navigation';
import { useFacilityStore } from '../../stores/facility';
import { patientsAPI } from '../../services/api';
import { HMS_NAV_GROUPS, CLAIMS_NAV_GROUPS, flattenNavItems } from '../../config/navConfig';

const props = defineProps({
  modelValue: { type: Boolean, default: true },
});

const emit = defineEmits(['update:modelValue']);

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const appModeStore = useAppModeStore();
const moduleSettingsStore = useModuleSettingsStore();
const navStore = useNavigationStore();
const facilityStore = useFacilityStore();

const searchExpanded = ref(false);
const searchCardNumber = ref('');
const searchCccNumber = ref('');
const searchPatientName = ref('');
const searchContactNumber = ref('');
const searching = ref(false);

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

const drawerWidth = computed(() => (navStore.collapsed ? 76 : 268));

const shortModeLabel = computed(() => {
  if (appModeStore.isClaims) return 'Claims';
  if (appModeStore.isCompanion) return 'Companion';
  if (appModeStore.isInventory) return 'Inventory';
  return 'HMS';
});

const canManageLicense = computed(
  () => authStore.isAuthenticated && (authStore.isSuperAdmin || authStore.canAccess(['Admin', 'Management']))
);

const allItems = computed(() =>
  flattenNavItems(appModeStore.isClaims ? CLAIMS_NAV_GROUPS : HMS_NAV_GROUPS)
);

const itemById = computed(() => {
  const map = new Map();
  for (const item of allItems.value) map.set(item.id, item);
  return map;
});

function canAccess(roles) {
  return authStore.canAccess(roles);
}

function isModuleActive(key) {
  return moduleSettingsStore.isModuleActive(key);
}

function isVisible(item) {
  if (item.allowSuperAdmin && authStore.isSuperAdmin) return true;
  if (item.roles && !canAccess(item.roles)) return false;
  return true;
}

function isInactive(item) {
  return item.moduleKey ? !isModuleActive(item.moduleKey) : false;
}

const visibleGroups = computed(() => {
  const groups = appModeStore.isClaims ? CLAIMS_NAV_GROUPS : HMS_NAV_GROUPS;
  return groups
    .map((g) => ({
      ...g,
      items: g.items.filter(isVisible),
    }))
    .filter((g) => g.items.length > 0);
});

const favoriteItems = computed(() =>
  navStore.favoriteIds.map((id) => itemById.value.get(id)).filter((item) => item && isVisible(item))
);

const recentItems = computed(() =>
  navStore.recentIds.map((id) => itemById.value.get(id)).filter((item) => item && isVisible(item))
);

watch(
  () => route.name,
  (name) => {
    if (!name) return;
    const match = allItems.value.find((i) => i.to?.name === name);
    if (match) navStore.recordVisit(match.id);
  },
  { immediate: true }
);

function navigate(item) {
  if (isInactive(item)) {
    $q.notify({
      type: 'warning',
      message: `${item.label} module is not active`,
      position: 'top',
    });
    return;
  }
  navStore.recordVisit(item.id);
  router.push(item.to).catch(() => {});
}

function isActive(item) {
  return item.to?.name && route.name === item.to.name;
}

function extractPatients(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    if (Array.isArray(data.data)) return data.data;
    if (Array.isArray(data.results)) return data.results;
    if (data.data && typeof data.data === 'object') return [data.data];
    return [data];
  }
  return [];
}

async function runPatientSearch(type, term, apiCall) {
  const value = term?.trim();
  if (!value) {
    $q.notify({ type: 'warning', message: 'Please enter a search value' });
    return;
  }
  searching.value = true;
  try {
    const response = await apiCall(value);
    const patients = extractPatients(response.data);
    if (patients.length === 0) {
      $q.notify({ type: 'info', message: 'No patients found' });
      return;
    }
    await router.push({
      name: 'PatientSearchResults',
      query: {
        searchType: type,
        searchTerm: value,
        patients: JSON.stringify(patients),
      },
    });
    searchCardNumber.value = '';
    searchCccNumber.value = '';
    searchPatientName.value = '';
    searchContactNumber.value = '';
  } catch (error) {
    if (error.response?.status === 404) {
      $q.notify({ type: 'info', message: 'No patients found' });
    } else {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Search failed',
      });
    }
  } finally {
    searching.value = false;
  }
}
</script>

<template>
  <q-drawer
    v-model="open"
    show-if-above
    :width="drawerWidth"
    :breakpoint="1024"
    bordered
    class="app-sidebar-drawer"
  >
    <aside class="sidebar" :class="{ collapsed: navStore.collapsed }">
      <!-- Brand: facility name (Zendenta product-name slot) -->
      <div class="brand-row">
        <div class="brand-main">
          <img
            src="/logos/ghana-health-service-logo.png"
            :alt="facilityStore.displayName"
            width="32"
            height="32"
            class="brand-logo"
          />
          <div v-if="!navStore.collapsed" class="brand-copy">
            <div class="brand-name" :title="facilityStore.displayName">
              {{ facilityStore.displayName }}
            </div>
          </div>
        </div>
        <button
          type="button"
          class="collapse-btn"
          :aria-label="navStore.collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="navStore.toggleCollapsed()"
        >
          <ChevronRight v-if="navStore.collapsed" :size="16" />
          <ChevronLeft v-else :size="16" />
        </button>
      </div>

      <!-- Code · Mode · License -->
      <div v-if="!navStore.collapsed" class="meta-card">
        <div class="meta-chips">
          <span v-if="facilityStore.facilityCodeDisplay" class="meta-chip code">
            {{ facilityStore.facilityCodeDisplay }}
          </span>
          <span class="meta-chip mode">{{ shortModeLabel }}</span>
          <router-link
            v-if="canManageLicense"
            :to="{ name: 'LicenseSetup' }"
            class="meta-chip license"
          >
            <ShieldCheck :size="12" />
            License
          </router-link>
          <span v-else class="meta-chip license muted">
            <ShieldCheck :size="12" />
            Licensed
          </span>
        </div>
      </div>
      <button
        v-else
        type="button"
        class="facility-collapsed"
        :title="facilityStore.displayName"
      >
        <Building2 :size="18" />
      </button>

      <!-- Patient search -->
      <div v-if="!appModeStore.isClaims && !navStore.collapsed" class="search-block">
        <button type="button" class="search-toggle" @click="searchExpanded = !searchExpanded">
          <Search :size="15" />
          <span>Search patient</span>
          <ChevronDown :size="14" :class="{ rotated: searchExpanded }" class="chevron" />
        </button>
        <div v-show="searchExpanded" class="search-fields">
          <q-input
            v-model="searchCardNumber"
            dense
            filled
            label="Card Number"
            class="q-mb-xs"
            :disable="searching"
            @keyup.enter="runPatientSearch('card', searchCardNumber, patientsAPI.getByCard)"
          >
            <template #append>
              <q-icon
                name="search"
                class="cursor-pointer"
                @click="runPatientSearch('card', searchCardNumber, patientsAPI.getByCard)"
              />
            </template>
          </q-input>
          <q-input
            v-model="searchCccNumber"
            dense
            filled
            label="Ghana Card/Insurance #"
            class="q-mb-xs"
            :disable="searching"
            @keyup.enter="runPatientSearch('ccc', searchCccNumber, patientsAPI.searchByCcc)"
          >
            <template #append>
              <q-icon
                name="search"
                class="cursor-pointer"
                @click="runPatientSearch('ccc', searchCccNumber, patientsAPI.searchByCcc)"
              />
            </template>
          </q-input>
          <q-input
            v-model="searchPatientName"
            dense
            filled
            label="Patient Name"
            class="q-mb-xs"
            :disable="searching"
            @keyup.enter="runPatientSearch('name', searchPatientName, patientsAPI.searchByName)"
          >
            <template #append>
              <q-icon
                name="search"
                class="cursor-pointer"
                @click="runPatientSearch('name', searchPatientName, patientsAPI.searchByName)"
              />
            </template>
          </q-input>
          <q-input
            v-model="searchContactNumber"
            dense
            filled
            label="Contact Number"
            :disable="searching"
            @keyup.enter="runPatientSearch('contact', searchContactNumber, patientsAPI.searchByContact)"
          >
            <template #append>
              <q-icon
                name="search"
                class="cursor-pointer"
                @click="runPatientSearch('contact', searchContactNumber, patientsAPI.searchByContact)"
              />
            </template>
          </q-input>
        </div>
      </div>

      <div class="sidebar-scroll">
        <!-- Favorites -->
        <section v-if="favoriteItems.length" class="nav-section">
          <div v-if="!navStore.collapsed" class="section-label">
            <Star :size="11" />
            Favorites
          </div>
          <div v-for="item in favoriteItems" :key="'fav-' + item.id" class="nav-row">
            <button
              type="button"
              class="nav-item"
              :class="{ active: isActive(item), inactive: isInactive(item) }"
              :title="navStore.collapsed ? item.label : undefined"
              @click="navigate(item)"
            >
              <q-icon :name="item.icon" size="18px" />
              <span v-if="!navStore.collapsed" class="nav-label">{{ item.label }}</span>
              <q-tooltip v-if="navStore.collapsed">{{ item.label }}</q-tooltip>
            </button>
          </div>
        </section>

        <!-- Recents -->
        <section v-if="recentItems.length" class="nav-section">
          <div v-if="!navStore.collapsed" class="section-label">
            <Clock :size="11" />
            Recently used
          </div>
          <div v-for="item in recentItems" :key="'recent-' + item.id" class="nav-row">
            <button
              type="button"
              class="nav-item"
              :class="{ active: isActive(item), inactive: isInactive(item) }"
              :title="navStore.collapsed ? item.label : undefined"
              @click="navigate(item)"
            >
              <q-icon :name="item.icon" size="18px" />
              <span v-if="!navStore.collapsed" class="nav-label">{{ item.label }}</span>
              <q-tooltip v-if="navStore.collapsed">{{ item.label }}</q-tooltip>
            </button>
          </div>
        </section>

        <!-- Grouped modules -->
        <section v-for="group in visibleGroups" :key="group.id" class="nav-section">
          <div v-if="!navStore.collapsed" class="section-label">{{ group.label }}</div>
          <div v-for="item in group.items" :key="item.id" class="nav-row">
            <button
              type="button"
              class="nav-item"
              :class="{ active: isActive(item), inactive: isInactive(item) }"
              :title="navStore.collapsed ? item.label : undefined"
              @click="navigate(item)"
            >
              <q-icon :name="item.icon" size="18px" />
              <span v-if="!navStore.collapsed" class="nav-label">{{ item.label }}</span>
              <q-tooltip v-if="navStore.collapsed">{{ item.label }}</q-tooltip>
              <q-tooltip v-if="isInactive(item)">Module not active</q-tooltip>
            </button>
            <button
              v-if="!navStore.collapsed"
              type="button"
              class="fav-btn"
              :class="{ on: navStore.isFavorite(item.id) }"
              :aria-label="navStore.isFavorite(item.id) ? 'Remove favorite' : 'Add favorite'"
              @click.stop="navStore.toggleFavorite(item.id)"
            >
              <Star :size="13" :fill="navStore.isFavorite(item.id) ? 'currentColor' : 'none'" />
            </button>
          </div>
        </section>
      </div>
    </aside>
  </q-drawer>
</template>

<style scoped>
.app-sidebar-drawer {
  background: var(--hms-panel-bg) !important;
  border-right: 1px solid var(--hms-border) !important;
}

.app-sidebar-drawer :deep(.q-drawer__content) {
  background: var(--hms-panel-bg) !important;
}

.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  overflow: hidden;
}

.brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 1rem 0.85rem 0.65rem;
}

.brand-main {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}

.brand-logo {
  border-radius: 8px;
  flex-shrink: 0;
}

.brand-name {
  font-size: var(--hms-text-base);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
  line-height: 1.2;
  max-width: 11.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-tag {
  margin-top: 0.1rem;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--hms-text-muted);
}

.collapse-btn {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--hms-radius-md);
  border: 1px solid var(--hms-border);
  background: transparent;
  color: var(--hms-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.collapse-btn:hover {
  color: var(--hms-text-primary);
  background: var(--hms-surface);
}

.meta-card {
  margin: 0 0.75rem 0.85rem;
  padding: 0.65rem 0.7rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}

.meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  padding: 0.22rem 0.55rem;
  border-radius: var(--hms-radius-full);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-decoration: none;
  line-height: 1.2;
}

.meta-chip.code {
  background: var(--hms-healthcare-muted);
  color: var(--hms-healthcare);
}

.meta-chip.mode {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}

.meta-chip.license {
  background: var(--hms-panel-bg);
  color: var(--hms-text-secondary);
  border: 1px solid var(--hms-border);
  cursor: pointer;
}

.meta-chip.license:hover {
  color: var(--hms-accent);
  border-color: rgba(59, 130, 246, 0.35);
}

.meta-chip.license.muted {
  cursor: default;
  opacity: 0.85;
}

.facility-collapsed {
  margin: 0 auto 0.65rem;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}

.search-block {
  padding: 0 0.75rem 0.65rem;
}

.search-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.7rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 600;
  cursor: pointer;
}

.search-toggle:hover {
  color: var(--hms-text-primary);
  border-color: var(--hms-border-strong);
}

.chevron {
  margin-left: auto;
  transition: transform var(--hms-duration-fast) var(--hms-ease-out);
}

.chevron.rotated {
  transform: rotate(180deg);
}

.search-fields {
  margin-top: 0.45rem;
  padding: 0.55rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}

.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0.15rem 0.55rem 1.25rem;
  scrollbar-width: thin;
}

.nav-section {
  margin-bottom: 0.85rem;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.55rem 0.7rem 0.35rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}

.nav-row {
  display: flex;
  align-items: center;
  gap: 0.1rem;
}

.nav-item {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.58rem 0.75rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 550;
  text-align: left;
  cursor: pointer;
  position: relative;
  transition:
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    color var(--hms-duration-fast) var(--hms-ease-out);
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0.7rem;
}

.nav-item:hover {
  background: var(--hms-surface);
  color: var(--hms-text-primary);
}

.nav-item.active {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  font-weight: 700;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 18%;
  bottom: 18%;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--hms-accent);
}

.sidebar.collapsed .nav-item.active::before {
  left: 3px;
}

.nav-item.inactive {
  opacity: 0.42;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-btn {
  flex-shrink: 0;
  width: 1.65rem;
  height: 1.65rem;
  border: none;
  border-radius: var(--hms-radius-md);
  background: transparent;
  color: var(--hms-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
}

.nav-row:hover .fav-btn,
.fav-btn.on {
  opacity: 1;
}

.fav-btn.on {
  color: var(--hms-warning);
}

.fav-btn:hover {
  background: var(--hms-surface);
  color: var(--hms-warning);
}
</style>
