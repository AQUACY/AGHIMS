<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" to="/claims" />
      <div class="text-h4 q-ml-sm text-weight-bold glass-text">Claims</div>
    </div>

    <!-- Export by Date Range -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Export Claims by Date Range</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="exportStartDate"
            filled
            type="date"
            label="Start Date"
            class="col-12 col-md-4"
          />
          <q-input
            v-model="exportEndDate"
            filled
            type="date"
            label="End Date"
            class="col-12 col-md-4"
          />
          <q-btn
            color="primary"
            label="Export XML"
            @click="exportByDateRange"
            :loading="exporting"
            :disable="!exportStartDate || !exportEndDate"
            class="col-12 col-md-4 glass-button"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Claim Actions -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Finalized Encounters</div>
          <q-space />
          <q-btn
            :icon="filtersLocked ? 'lock' : 'lock_open'"
            :color="filtersLocked ? 'positive' : 'grey'"
            flat
            round
            dense
            size="sm"
            @click="toggleFiltersLock"
            class="q-mr-sm"
          >
            <q-tooltip>
              {{ filtersLocked ? 'Filters are locked - click to unlock' : 'Click to lock filters' }}
            </q-tooltip>
          </q-btn>
          <q-btn-toggle
            v-model="claimType"
            toggle-color="primary"
            :options="[
              { label: 'OPD', value: 'opd' },
              { label: 'IPD', value: 'ipd' },
              { label: 'Other', value: 'other' },
              { label: 'All', value: null }
            ]"
            size="sm"
          />
        </div>

        <div class="row q-gutter-md q-mb-sm">
          <q-select
            v-model="filterSpecialty"
            filled
            :options="specialtyOptions"
            label="Specialty"
            class="col-12 col-md-3"
            clearable
            emit-value
            map-options
            :hint="specialtyHint"
            dense
          />
        </div>
        
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="searchEncounterId"
            filled
            type="number"
            label="Search Encounter ID"
            class="col-12 col-md-2"
            @keyup.enter="searchEncounter"
          />
          <q-input
            v-model="filterCardNumber"
            filled
            label="Card Number"
            class="col-12 col-md-2"
            clearable
            @keyup.enter="loadFinalizedEncounters"
            hint="Partial match supported"
          />
          <q-input
            v-model="filterClaimId"
            filled
            label="Claim ID"
            class="col-12 col-md-2"
            clearable
            @keyup.enter="loadFinalizedEncounters"
            hint="e.g., CLA-XXXXX"
          />
          <q-input
            v-model="filterClaimCheckCode"
            filled
            label="CCC / Claim Check Code"
            class="col-12 col-md-2"
            clearable
            @keyup.enter="loadFinalizedEncounters"
            hint="Partial match supported"
          />
          <q-input
            v-model="filterStartDate"
            filled
            type="date"
            label="Start Date"
            class="col-12 col-md-2"
            clearable
          />
          <q-input
            v-model="filterEndDate"
            filled
            type="date"
            label="End Date"
            class="col-12 col-md-2"
            clearable
          />
          <q-select
            v-model="filterClaimStatus"
            filled
            :options="claimStatusOptions"
            label="Claim Status"
            class="col-12 col-md-2"
            clearable
            emit-value
            map-options
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchEncounter"
            class="col-12 col-md-1 glass-button"
          />
          <q-btn
            color="secondary"
            label="Clear Filters"
            @click="clearFilters"
            class="col-12 col-md-1 glass-button"
            outline
          />
        </div>

        <div class="row q-gutter-sm q-mb-sm items-center">
          <span class="text-caption text-weight-medium">Sort:</span>
          <q-select
            v-model="sortBy"
            :options="sortByOptions"
            emit-value
            map-options
            dense
            outlined
            class="col-12 col-sm-4 col-md-3"
            @update:model-value="onSortChange"
          />
          <q-space />
          <q-btn
            color="primary"
            label="Export selected"
            icon="download"
            :disable="selectedRows.length === 0"
            :loading="exportingSelected"
            @click="exportSelectedClaims"
            class="glass-button"
          />
          <span v-if="selectedRows.length > 0" class="text-caption text-grey">
            {{ selectedRows.length }} selected
          </span>
        </div>

        <q-table
          v-model:selected="selectedRows"
          :rows="sortedEncounters"
          :columns="columns"
          row-key="id"
          flat
          selection="multiple"
          :loading="loading"
          v-model:pagination="pagination"
          @request="onRequest"
          binary-state-sort
          server-side
          :rows-per-page-options="[50]"
        >
          <template v-slot:body-cell-row_num="props">
            <q-td :props="props">
              {{ (pagination.page - 1) * pagination.rowsPerPage + props.rowIndex + 1 }}
            </q-td>
          </template>
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!props.row.claim_id"
                size="sm"
                color="primary"
                label="Generate Claim"
                @click="generateClaim(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                v-else-if="props.row.claim_status === 'draft' || props.row.claim_status === 'reopened'"
                size="sm"
                color="secondary"
                label="Edit"
                @click="editClaim(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="props.row.claim_status === 'draft' || props.row.claim_status === 'reopened'"
                size="sm"
                color="orange"
                label="Finalize"
                @click="finalizeClaim(props.row.claim_id)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="props.row.claim_status === 'finalized'"
                size="sm"
                color="positive"
                label="Export XML"
                @click="exportSingleClaim(props.row.claim_id)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="props.row.claim_status === 'finalized'"
                size="sm"
                color="warning"
                label="Reopen"
                @click="reopenClaim(props.row.claim_id)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="props.row.claim_id && (props.row.claim_status === 'draft' || props.row.claim_status === 'reopened')"
                size="sm"
                color="info"
                label="Regenerate"
                @click="regenerateClaim(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="props.row.claim_status === 'finalized'"
                size="sm"
                color="primary"
                label="View"
                @click="viewClaim(props.row.claim_id)"
                class="q-mr-xs"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue';
import { useClaimsStore } from '../stores/claims';
import { encountersAPI, claimsAPI } from '../services/api';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';

const $router = useRouter();

const $q = useQuasar();
const claimsStore = useClaimsStore();

const exportStartDate = ref('');
const exportEndDate = ref('');
const exporting = ref(false);

// Helper function to get today's date in YYYY-MM-DD format
const getTodayDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const searchEncounterId = ref('');
const finalizedEncounters = ref([]);
const claimType = ref(null); // 'opd' | 'ipd' | null
const loading = ref(false);
const filterStartDate = ref(getTodayDate()); // Default to today
const filterEndDate = ref(getTodayDate()); // Default to today
const filterClaimStatus = ref(null);
const filterCardNumber = ref('');
const filterClaimId = ref('');
const filterClaimCheckCode = ref('');
const filterSpecialty = ref(null);
const specialtyOptions = ref([]);
const filtersLocked = ref(false);

// Pagination
const pagination = ref({
  page: 1,
  rowsPerPage: 50,
  rowsNumber: 0
});

// Multi-select for batch export
const selectedRows = ref([]);
const exportingSelected = ref(false);

// LocalStorage key for locked filters
const FILTERS_LOCK_KEY = 'claims_filters_locked';
const FILTERS_STORAGE_KEY = 'claims_filters';

const claimStatusOptions = [
  { label: 'All', value: null },
  { label: 'No Claim', value: 'no_claim' },
  { label: 'Draft', value: 'draft' },
  { label: 'Finalized', value: 'finalized' },
  { label: 'Reopened', value: 'reopened' },
];

const specialtyHint = computed(() => {
  if (claimType.value === 'ipd') return 'Filter by ward (IPD includes all wards)';
  if (claimType.value === 'opd' || claimType.value === 'other') return 'Filter by department/clinic';
  return 'Filter by specialty (department or ward)';
});

// Sort: default (server order), alphabetical by patient, or by encounter ID
const sortBy = ref('default');
const sortByOptions = [
  { label: 'Default (newest first)', value: 'default' },
  { label: 'Patient (A–Z)', value: 'patient_asc' },
  { label: 'Patient (Z–A)', value: 'patient_desc' },
  { label: 'Encounter ID (low → high)', value: 'id_asc' },
  { label: 'Encounter ID (high → low)', value: 'id_desc' },
];

const sortedEncounters = computed(() => {
  const list = finalizedEncounters.value || [];
  if (sortBy.value === 'default' || list.length === 0) return list;
  const copy = [...list];
  if (sortBy.value === 'patient_asc') {
    copy.sort((a, b) => (a.patient_name || '').localeCompare(b.patient_name || '', undefined, { sensitivity: 'base' }));
  } else if (sortBy.value === 'patient_desc') {
    copy.sort((a, b) => (b.patient_name || '').localeCompare(a.patient_name || '', undefined, { sensitivity: 'base' }));
  } else if (sortBy.value === 'id_asc') {
    copy.sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
  } else if (sortBy.value === 'id_desc') {
    copy.sort((a, b) => (b.id ?? 0) - (a.id ?? 0));
  }
  return copy;
});

const onSortChange = () => {
  // No need to reload; sortedEncounters computed will update the table
};

const columns = [
  { name: 'row_num', label: '#', align: 'left', sortable: false, style: 'width: 60px' },
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'patient_name', label: 'Patient', field: 'patient_name', align: 'left' },
  { name: 'patient_card_number', label: 'Card Number', field: 'patient_card_number', align: 'left' },
  { name: 'ccc_number', label: 'CCC Number', field: 'ccc_number', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'finalized_at', label: 'Finalized At', field: 'finalized_at', align: 'left', format: (val) => val ? new Date(val).toLocaleString() : '-' },
  { name: 'claim_status', label: 'Claim Status', field: 'claim_status', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    finalized: 'green',
    reopened: 'warning',
  };
  return colors[status] || 'grey';
};

const exportByDateRange = async () => {
  if (!exportStartDate.value || !exportEndDate.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select both start and end dates',
    });
    return;
  }

  exporting.value = true;
  try {
    await claimsStore.exportByDateRange(exportStartDate.value, exportEndDate.value);
  } catch (error) {
    // Error handled in store
  } finally {
    exporting.value = false;
  }
};

const searchEncounter = async () => {
  if (!searchEncounterId.value) {
    pagination.value.page = 1;
    loadFinalizedEncounters(1);
    return;
  }

  loading.value = true;
  try {
    const encounter = await encountersAPI.get(searchEncounterId.value);
    if (encounter.data.status === 'finalized') {
      finalizedEncounters.value = [{
        id: encounter.data.id,
        patient_name: 'Patient', // You may need to fetch patient info
        finalized_at: encounter.data.finalized_at,
        claim_id: null,
        claim_status: null,
      }];
      pagination.value.rowsNumber = 1;
      pagination.value.page = 1;
    } else {
      $q.notify({
        type: 'warning',
        message: 'Encounter is not finalized',
      });
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to fetch encounter',
    });
    finalizedEncounters.value = [];
    pagination.value.rowsNumber = 0;
  } finally {
    loading.value = false;
  }
};

const loadSpecialties = async () => {
  try {
    const res = await claimsAPI.getSpecialties(claimType.value);
    const list = res.data?.specialties || [];
    specialtyOptions.value = list.map((s) => ({ label: s, value: s }));
  } catch (e) {
    specialtyOptions.value = [];
  }
};

const clearFilters = () => {
  // Reset to today's date instead of clearing dates
  filterStartDate.value = getTodayDate();
  filterEndDate.value = getTodayDate();
  filterClaimStatus.value = null;
  filterCardNumber.value = '';
  filterClaimId.value = '';
  filterSpecialty.value = null;
  searchEncounterId.value = '';
  pagination.value.page = 1; // Reset to first page
  
  // Save cleared filters if locked
  if (filtersLocked.value) {
    saveFiltersToStorage();
  }
  
  loadFinalizedEncounters(1);
};

const toggleFiltersLock = () => {
  filtersLocked.value = !filtersLocked.value;
  
  if (filtersLocked.value) {
    // Lock: Save current filters
    saveFiltersToStorage();
    localStorage.setItem(FILTERS_LOCK_KEY, 'true');
    $q.notify({
      type: 'positive',
      message: 'Filters locked - they will persist when navigating',
      timeout: 2000,
    });
  } else {
    // Unlock: Clear saved filters
    localStorage.removeItem(FILTERS_LOCK_KEY);
    localStorage.removeItem(FILTERS_STORAGE_KEY);
    $q.notify({
      type: 'info',
      message: 'Filters unlocked',
      timeout: 2000,
    });
  }
};

const saveFiltersToStorage = () => {
  const filters = {
    claimType: claimType.value,
    filterCardNumber: filterCardNumber.value,
    filterClaimId: filterClaimId.value,
    filterClaimCheckCode: filterClaimCheckCode.value,
    filterStartDate: filterStartDate.value,
    filterEndDate: filterEndDate.value,
    filterClaimStatus: filterClaimStatus.value,
    filterSpecialty: filterSpecialty.value,
    searchEncounterId: searchEncounterId.value,
  };
  localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
};

const loadFiltersFromStorage = () => {
  const savedFilters = localStorage.getItem(FILTERS_STORAGE_KEY);
  if (savedFilters) {
    try {
      const filters = JSON.parse(savedFilters);
      claimType.value = filters.claimType ?? null;
      filterCardNumber.value = filters.filterCardNumber || '';
      filterClaimId.value = filters.filterClaimId || '';
      filterClaimCheckCode.value = filters.filterClaimCheckCode || '';
      filterSpecialty.value = filters.filterSpecialty ?? null;
      // Only load saved dates if they exist, otherwise default to today
      filterStartDate.value = filters.filterStartDate || getTodayDate();
      filterEndDate.value = filters.filterEndDate || getTodayDate();
      filterClaimStatus.value = filters.filterClaimStatus ?? null;
      searchEncounterId.value = filters.searchEncounterId || '';
    } catch (error) {
      console.error('Failed to load saved filters:', error);
      // If loading fails, ensure dates default to today
      filterStartDate.value = getTodayDate();
      filterEndDate.value = getTodayDate();
    }
  } else {
    // If no saved filters, ensure dates default to today
    filterStartDate.value = getTodayDate();
    filterEndDate.value = getTodayDate();
  }
};

const generateClaim = (encounter) => {
  // Open generate claim page in new tab
  // For IPD claims, include ward_admission_id if available
  let route;
  if (encounter.ward_admission_id) {
    route = $router.resolve({
      path: `/claims/generate/${encounter.id}`,
      query: { ward_admission_id: encounter.ward_admission_id, type: 'ipd' }
    });
  } else {
    route = $router.resolve(`/claims/generate/${encounter.id}`);
  }
  window.open(route.href, '_blank');
};

const editClaim = async (encounter) => {
  if (!encounter.claim_id) return;
  
  // Open edit page in new tab
  const route = $router.resolve(`/claims/edit/${encounter.claim_id}`);
  window.open(route.href, '_blank');
};


const finalizeClaim = async (claimId) => {
  $q.dialog({
    title: 'Finalize Claim',
    message: 'Are you sure you want to finalize this claim?',
    cancel: true,
  }).onOk(async () => {
    try {
      await claimsStore.finalizeClaim(claimId);
      loadFinalizedEncounters(pagination.value.page);
    } catch (error) {
      // Error handled in store
    }
  });
};

const reopenClaim = async (claimId) => {
  $q.dialog({
    title: 'Reopen Claim',
    message: 'Are you sure you want to reopen this claim?',
    cancel: true,
  }).onOk(async () => {
    try {
      await claimsStore.reopenClaim(claimId);
      loadFinalizedEncounters(pagination.value.page);
    } catch (error) {
      // Error handled in store
    }
  });
};

const exportSingleClaim = async (claimId) => {
  try {
    await claimsStore.exportClaim(claimId);
  } catch (error) {
    // Error handled in store
  }
};

const exportSelectedClaims = async () => {
  const exportable = selectedRows.value.filter(
    (row) => row.claim_id && row.claim_status === 'finalized'
  );
  if (exportable.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Select only finalized claims to export (rows with "Finalized" status)',
    });
    return;
  }
  const claimIds = exportable.map((row) => row.claim_id);
  exportingSelected.value = true;
  try {
    const response = await claimsAPI.exportBatch(claimIds);
    if (response.status < 200 || response.status >= 300) {
      const msg = await claimsStore._blobErrorDetail?.(response.data) ?? 'Export failed';
      $q.notify({ type: 'negative', message: msg });
      return;
    }
    const blob = new Blob([response.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_batch_${new Date().toISOString().slice(0, 10)}.xml`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    $q.notify({
      type: 'positive',
      message: `${claimIds.length} claim(s) exported successfully`,
    });
  } catch (error) {
    const msg = await claimsStore._blobErrorDetail?.(error.response?.data);
    $q.notify({
      type: 'negative',
      message: msg || error.response?.data?.detail || error.message || 'Failed to export selected claims',
    });
  } finally {
    exportingSelected.value = false;
  }
};

const regenerateClaim = (encounter) => {
  // Open generate claim page in new tab (will update existing claim)
  // For IPD claims, include ward_admission_id if available
  let route;
  if (encounter.ward_admission_id) {
    route = $router.resolve({
      path: `/claims/generate/${encounter.id}`,
      query: { 
        regenerate: 'true', 
        claimId: encounter.claim_id, 
        ward_admission_id: encounter.ward_admission_id, 
        type: 'ipd' 
      }
    });
  } else {
    route = $router.resolve({
      path: `/claims/generate/${encounter.id}`,
      query: { regenerate: 'true', claimId: encounter.claim_id }
    });
  }
  window.open(route.href, '_blank');
};

const viewClaim = (claimId) => {
  // Open edit page in new tab in view mode
  const route = $router.resolve({
    path: `/claims/edit/${claimId}`,
    query: { view: 'true' }
  });
  window.open(route.href, '_blank');
};

const loadFinalizedEncounters = async (page = 1) => {
  loading.value = true;
  try {
    const skip = (page - 1) * pagination.value.rowsPerPage;
    const response = await claimsAPI.getEligibleEncounters(
      claimType.value,
      filterStartDate.value || null,
      filterEndDate.value || null,
      filterClaimStatus.value || null,
      filterCardNumber.value || null,
      filterClaimId.value || null,
      filterClaimCheckCode.value || null,
      filterSpecialty.value || null,
      skip,
      pagination.value.rowsPerPage
    );
    
    // Handle response - check if it's the new paginated format or old format
    const responseData = response.data;
    let items = [];
    let total = 0;
    
    if (responseData && responseData.items && Array.isArray(responseData.items)) {
      // New paginated format
      items = responseData.items;
      total = responseData.total || 0;
    } else if (Array.isArray(responseData)) {
      // Old format (array directly) - fallback for compatibility
      items = responseData;
      total = responseData.length;
    } else {
      console.error('Unexpected response format:', responseData);
      throw new Error('Unexpected response format from API');
    }
    
    // Update pagination info - create new object to ensure reactivity
    pagination.value = {
      page: page,
      rowsPerPage: 50,
      rowsNumber: total
    };
    
    console.log('Pagination updated:', {
      page: pagination.value.page,
      rowsPerPage: pagination.value.rowsPerPage,
      rowsNumber: pagination.value.rowsNumber,
      totalFromAPI: total,
      itemsCount: items.length
    });
    
    finalizedEncounters.value = items.map(encounter => ({
      id: encounter.id,
      ward_admission_id: encounter.ward_admission_id || null,
      patient_name: encounter.patient_name,
      patient_card_number: encounter.patient_card_number,
      ccc_number: encounter.ccc_number,
      finalized_at: encounter.finalized_at,
      claim_id: encounter.claim_id,
      claim_status: encounter.claim_status,
      department: encounter.department,
    }));
  } catch (error) {
    console.error('Error loading encounters:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to load encounters';
    $q.notify({
      type: 'negative',
      message: errorMessage,
      timeout: 5000,
    });
    finalizedEncounters.value = [];
    pagination.value.rowsNumber = 0;
  } finally {
    loading.value = false;
  }
};

const onRequest = (props) => {
  const { page, rowsPerPage } = props.pagination;
  // Lock rowsPerPage to 50 and update pagination
  pagination.value = {
    ...pagination.value,
    page: page,
    rowsPerPage: 50
  };
  loadFinalizedEncounters(page);
};

watch(claimType, () => {
  loadSpecialties(); // Refresh specialty options (OPD = departments, IPD = wards)
});

watch([filterStartDate, filterEndDate, filterClaimStatus, filterCardNumber, filterClaimId, filterClaimCheckCode, filterSpecialty, claimType], () => {
  // Auto-reload when filters change (debounce could be added if needed)
  if (!searchEncounterId.value) {
    pagination.value.page = 1; // Reset to first page when filters change
    loadFinalizedEncounters(1);
  }
  
  // Save filters if locked
  if (filtersLocked.value) {
    saveFiltersToStorage();
  }
});

onMounted(async () => {
  // Check if filters are locked
  const isLocked = localStorage.getItem(FILTERS_LOCK_KEY) === 'true';
  filtersLocked.value = isLocked;
  
  // Load saved filters if locked, otherwise use defaults (today's date)
  if (isLocked) {
    loadFiltersFromStorage();
  } else {
    // Ensure dates are set to today if not locked
    filterStartDate.value = getTodayDate();
    filterEndDate.value = getTodayDate();
  }
  
  await loadSpecialties();
  loadFinalizedEncounters(1);
});
</script>

