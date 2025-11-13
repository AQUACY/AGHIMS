<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">X-ray Services</div>

    <!-- Filters and Search -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row q-gutter-md q-mb-md">
          <!-- Search by Card Number or Name -->
          <q-input
            v-model="searchTerm"
            filled
            label="Search by Card Number or Patient Name"
            class="col-12 col-md-4"
            @keyup.enter="loadRequests"
            clearable
            @clear="loadRequests"
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>

          <!-- Date Filter -->
          <q-input
            v-model="filterDate"
            filled
            label="Date (optional)"
            type="date"
            class="col-12 col-md-3"
            @update:model-value="loadRequests"
            clearable
            hint="Leave empty to show all dates"
          >
            <template v-slot:prepend>
              <q-icon name="event" />
            </template>
          </q-input>

          <!-- Status Filter -->
          <q-select
            v-model="statusFilter"
            filled
            :options="statusOptions"
            label="Status"
            class="col-12 col-md-3"
            @update:model-value="loadRequests"
            clearable
          >
            <template v-slot:prepend>
              <q-icon name="filter_list" />
            </template>
          </q-select>

          <!-- Refresh Button -->
          <q-btn
            color="primary"
            icon="refresh"
            label="Refresh"
            @click="loadRequests"
            :loading="loadingRequests"
            class="col-12 col-md-2"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- X-ray Requests Table -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">X-ray Requests</div>
          <q-space />
          <q-btn
            v-if="authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin'"
            color="primary"
            icon="add"
            label="Add Service"
            @click="openAddServiceDialogForNew"
            class="q-mr-md"
          />
          <q-badge color="primary" :label="`${requests.length} request(s)`" />
        </div>
        <q-table
          :rows="requests"
          :columns="requestColumns"
          row-key="id"
          flat
          :loading="loadingRequests"
          :pagination="{ rowsPerPage: 20 }"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-encounter_date="props">
            <q-td :props="props">
              {{ formatDate(props.value || props.row.created_at) }}
            </q-td>
          </template>
          <template v-slot:body-cell-source="props">
            <q-td :props="props">
              <q-badge
                v-if="props.value === 'inpatient' || props.row.prescription_type === 'inpatient'"
                color="purple"
                label="IPD"
              />
              <q-badge
                v-else
                color="blue"
                label="OPD"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <span v-if="props.value || props.row.bed_number">
                {{ props.value || '' }}{{ props.row.bed_number ? ` / ${props.row.bed_number}` : '' }}
              </span>
              <span v-else class="text-grey">-</span>
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  size="sm"
                  color="info"
                  icon="visibility"
                  flat
                  round
                  @click="viewRemarks(props.row)"
                >
                  <q-tooltip>View Remarks/Notes</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin')"
                  size="sm"
                  color="secondary"
                  label="Update Service"
                  @click="openUpdateServiceDialog(props.row)"
                />
                <q-btn
                  v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin')"
                  size="sm"
                  color="accent"
                  label="Add Service"
                  @click="openAddServiceDialog(props.row)"
                />
                <q-btn
                  v-if="props.row.status === 'requested'"
                  size="sm"
                  color="primary"
                  label="Confirm"
                  @click="confirmInvestigation(props.row)"
                  :loading="confirmingId === props.row.id"
                  :disable="confirmingId !== null"
                />
                <q-btn
                  v-if="props.row.status === 'confirmed'"
                  size="sm"
                  color="positive"
                  label="Add Results"
                  @click="navigateToResultPage(props.row)"
                />
              <q-btn
                  v-if="props.row.status === 'completed'"
                size="sm"
                  color="info"
                  label="View Results"
                  @click="navigateToResultPage(props.row)"
                />
              <q-btn
                  v-if="props.row.status === 'confirmed' && authStore.userRole === 'Admin'"
                size="sm"
                  color="orange"
                  label="Revert to Requested"
                  @click="revertToRequested(props.row)"
                  :loading="revertingToRequestedId === props.row.id"
                />
                <q-btn
                  v-if="props.row.status === 'completed' && (authStore.userRole === 'Admin' || authStore.userRole === 'Xray Head')"
                  size="sm"
                  color="warning"
                  label="Revert to Confirmed"
                  @click="revertInvestigationStatus(props.row)"
                  :loading="revertingId === props.row.id"
                />
              </div>
            </q-td>
          </template>
        </q-table>
        <div v-if="!loadingRequests && requests.length === 0" class="text-center text-grey-7 q-pa-md">
          No x-ray requests found for the selected filters
        </div>
      </q-card-section>
    </q-card>

    <!-- View Remarks Dialog -->
    <q-dialog v-model="showRemarksDialog">
      <q-card style="min-width: 400px; max-width: 600px">
        <q-card-section>
          <div class="text-h6">Remarks / Notes</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="viewingRemarks">
            {{ viewingRemarks?.procedure_name || 'Investigation' }} ({{ viewingRemarks?.gdrg_code }})
          </div>
        </q-card-section>
        <q-card-section>
          <div v-if="viewingRemarks?.notes" class="text-body1 q-pa-md" style="background-color: #f5f5f5; border-radius: 4px; white-space: pre-wrap;">
            {{ viewingRemarks.notes }}
          </div>
          <div v-else class="text-grey-6 text-center q-pa-md">
            No remarks/notes provided for this investigation
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" flat v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- IPD Confirmation Dialog -->
    <q-dialog v-model="showConfirmInpatientDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Confirm IPD Investigation</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ confirmInpatientForm.procedure_name }}
          </div>
        </q-card-section>
        <q-card-section>
          <q-checkbox
            v-model="confirmInpatientForm.add_to_ipd_bill"
            label="Add to IPD bill"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showConfirmInpatientDialog = false" />
          <q-btn
            label="Confirm"
            color="primary"
            @click="confirmInpatientInvestigation"
            :loading="confirmingId === confirmInpatientForm.id"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Update Service Dialog -->
    <q-dialog v-model="showUpdateServiceDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">Update Service</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            Patient: {{ selectedInvestigation.patient_name }} ({{ selectedInvestigation.patient_card_number }})
          </div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="updateService" class="q-gutter-md">
            <q-select
              v-model="serviceForm.gdrg_code"
              filled
              :options="filteredServiceOptions"
              option-label="service_name"
              option-value="g_drg_code"
              label="Search Service (start typing)"
              :loading="loadingServices"
              @update:model-value="onServiceSelected"
              :rules="[(val) => !!val || 'Service is required']"
              use-input
              input-debounce="300"
              @filter="filterServices"
              clearable
              hint="Start typing to search for services"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                    <q-item-label caption>G-DRG: {{ scope.opt.g_drg_code }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="serviceForm.procedure_name"
              filled
              label="Procedure Name"
              :rules="[(val) => !!val || 'Procedure name is required']"
            />
            <q-input
              v-model="serviceForm.notes"
              filled
              type="textarea"
              rows="3"
              label="Notes (Optional)"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Update Service"
                type="submit"
                color="primary"
                class="col"
                :loading="updatingService"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add Service Dialog -->
    <q-dialog v-model="showAddServiceDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">Add New Service</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            Patient: {{ selectedInvestigation.patient_name }} ({{ selectedInvestigation.patient_card_number }})
          </div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addService" class="q-gutter-md">
            <q-select
              v-model="addServiceForm.gdrg_code"
              filled
              :options="filteredServiceOptions"
              option-label="service_name"
              option-value="g_drg_code"
              label="Search Service (start typing)"
              :loading="loadingServices"
              @update:model-value="onAddServiceSelected"
              :rules="[(val) => !!val || 'Service is required']"
              use-input
              input-debounce="300"
              @filter="filterServices"
              clearable
              hint="Start typing to search for services"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                    <q-item-label caption>G-DRG: {{ scope.opt.g_drg_code }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No services found
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="addServiceForm.procedure_name"
              filled
              label="Procedure Name"
              :rules="[(val) => !!val || 'Procedure name is required']"
            />
            <q-input
              v-model="addServiceForm.notes"
              filled
              type="textarea"
              rows="3"
              label="Notes (Optional)"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Add Service"
                type="submit"
                color="primary"
                class="col"
                :loading="addingService"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// Request list functionality
const requests = ref([]);
const loadingRequests = ref(false);
const searchTerm = ref('');
const filterDate = ref('');
const statusFilter = ref(null);
const statusOptions = [
  { label: 'Requested', value: 'requested' },
  { label: 'Confirmed', value: 'confirmed' },
  { label: 'Completed', value: 'completed' },
  { label: 'Cancelled', value: 'cancelled' }
];

const confirmingId = ref(null);
const revertingId = ref(null);
const revertingToRequestedId = ref(null);
const showRemarksDialog = ref(false);
const showConfirmInpatientDialog = ref(false);
const confirmInpatientForm = ref({
  id: null,
  procedure_name: '',
  add_to_ipd_bill: true
});
const viewingRemarks = ref(null);
const showUpdateServiceDialog = ref(false);
const showAddServiceDialog = ref(false);
const selectedInvestigation = ref(null);
const availableServices = ref([]);
const loadingServices = ref(false);
const updatingService = ref(false);
const addingService = ref(false);
const serviceForm = ref({
  gdrg_code: '',
  procedure_name: '',
  notes: '',
});
const addServiceForm = ref({
  gdrg_code: '',
  procedure_name: '',
  notes: '',
});

const requestColumns = [
  { name: 'patient_name', label: 'Patient Name', field: 'patient_name', align: 'left', sortable: true },
  { name: 'patient_card_number', label: 'Card Number', field: 'patient_card_number', align: 'left', sortable: true },
  { name: 'source', label: 'Source', field: 'source', align: 'center', sortable: true },
  { name: 'ward', label: 'Ward/Bed', field: 'ward', align: 'left', sortable: true },
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left', sortable: true },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left', sortable: true },
  { name: 'encounter_date', label: 'Request Date', field: 'encounter_date', align: 'left', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true },
  { name: 'confirmed_by_name', label: 'Confirmed By', field: 'confirmed_by_name', align: 'left', sortable: true },
  { name: 'completed_by_name', label: 'Completed By', field: 'completed_by_name', align: 'left', sortable: true },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const getStatusColor = (status) => {
  const colors = {
    requested: 'orange',
    confirmed: 'blue',
    completed: 'green',
  };
  return colors[status] || 'grey';
};

// Load requests with filters
const loadRequests = async () => {
  loadingRequests.value = true;
  try {
    const filters = {
      investigation_type: 'xray',
    };
    
    if (statusFilter.value) {
      filters.status = statusFilter.value.value || statusFilter.value;
    }
    
    if (searchTerm.value && searchTerm.value.trim()) {
      filters.search = searchTerm.value.trim();
    }
    
    if (filterDate.value) {
      filters.date = filterDate.value;
    }
    
    // Load both OPD and IPD investigations
    const [opdResponse, ipdResponse] = await Promise.all([
      consultationAPI.getInvestigationsByType('xray', filters).catch(err => {
        console.error('Failed to load OPD investigations:', err);
        return { data: [] };
      }),
      consultationAPI.getInpatientInvestigationsByType('xray', filters).catch(err => {
        console.error('Failed to load IPD investigations:', err);
        console.error('Error details:', err.response?.data || err.message);
        return { data: [] };
      })
    ]);
    
    const opdRequests = opdResponse.data || [];
    const ipdRequests = ipdResponse.data || [];
    
    // Mark source and merge
    const opdMarked = opdRequests.map(req => ({ ...req, source: 'opd' }));
    const ipdMarked = ipdRequests.map(req => ({ ...req, source: 'inpatient' }));
    
    // Merge both lists
    requests.value = [...opdMarked, ...ipdMarked];
  } catch (error) {
    console.error('Failed to load requests:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load x-ray requests',
    });
    requests.value = [];
  } finally {
    loadingRequests.value = false;
  }
};

// Initialize date to today (optional - user can clear to see all dates)
const initializeDate = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  filterDate.value = `${year}-${month}-${day}`;
};

const confirmInvestigation = async (investigation) => {
  // Check if IPD investigation
  if (investigation.source === 'inpatient' || investigation.prescription_type === 'inpatient') {
    // Show IPD confirmation dialog
    showConfirmInpatientDialog.value = true;
    confirmInpatientForm.value = {
      id: investigation.id,
      procedure_name: investigation.procedure_name || investigation.gdrg_code,
      add_to_ipd_bill: true
    };
  } else {
    // Standard OPD confirmation
    $q.dialog({
      title: 'Confirm Investigation',
      message: `Confirm ${investigation.procedure_name || investigation.gdrg_code}?`,
      cancel: true,
      persistent: true,
    }).onOk(async () => {
      confirmingId.value = investigation.id;
      try {
        await consultationAPI.confirmInvestigation(investigation.id);
        $q.notify({
          type: 'positive',
          message: 'Investigation confirmed',
        });
        await loadRequests();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to confirm investigation',
        });
      } finally {
        confirmingId.value = null;
      }
    });
  }
};

const confirmInpatientInvestigation = async () => {
  if (!confirmInpatientForm.value.id) return;
  
  confirmingId.value = confirmInpatientForm.value.id;
  try {
    await consultationAPI.confirmInpatientInvestigation(confirmInpatientForm.value.id, {
      add_to_ipd_bill: confirmInpatientForm.value.add_to_ipd_bill
    });
    $q.notify({
      type: 'positive',
      message: 'IPD investigation confirmed',
    });
    showConfirmInpatientDialog.value = false;
    await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm investigation',
    });
  } finally {
    confirmingId.value = null;
  }
};

const viewRemarks = (investigation) => {
  viewingRemarks.value = investigation;
  showRemarksDialog.value = true;
};

const navigateToResultPage = (request) => {
  router.push(`/xray/result/${request.id}`);
};

const revertToRequested = async (investigation) => {
  $q.dialog({
    title: 'Revert to Requested',
    message: 'Please provide a reason for reverting this investigation from "confirmed" to "requested":',
    prompt: {
      model: '',
      type: 'text',
      placeholder: 'Enter reason for revert...',
      isValid: (val) => val && val.trim().length > 0,
      attrs: {
        maxlength: 500,
      },
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    revertingToRequestedId.value = investigation.id;
    try {
      // Check if IPD investigation
      if (investigation.source === 'inpatient' || investigation.prescription_type === 'inpatient') {
        await consultationAPI.revertInpatientInvestigationToRequested(investigation.id, reason);
      } else {
        await consultationAPI.revertInvestigationToRequested(investigation.id, reason);
      }
    $q.notify({
      type: 'positive',
        message: 'Status reverted to requested successfully',
    });
      await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
        message: error.response?.data?.detail || 'Failed to revert status',
    });
  } finally {
      revertingToRequestedId.value = null;
    }
  });
};

const revertInvestigationStatus = async (investigation) => {
  $q.dialog({
    title: 'Revert Status',
    message: `Are you sure you want to revert this investigation from "completed" to "confirmed"? This will allow editing the results.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    revertingId.value = investigation.id;
    try {
      // Check if IPD investigation
      if (investigation.source === 'inpatient' || investigation.prescription_type === 'inpatient') {
        await consultationAPI.revertInpatientInvestigationStatus(investigation.id);
      } else {
        await consultationAPI.revertInvestigationStatus(investigation.id);
      }
    $q.notify({
      type: 'positive',
        message: 'Status reverted to confirmed successfully',
    });
      await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
        message: error.response?.data?.detail || 'Failed to revert status',
      });
    } finally {
      revertingId.value = null;
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const loadAvailableServices = async () => {
  loadingServices.value = true;
  try {
    const userRole = authStore.userRole;
    let services = [];
    
    // First, get all available service types
    let allServiceTypes = [];
    try {
      const serviceTypesResponse = await priceListAPI.getServiceTypes();
      allServiceTypes = serviceTypesResponse.data || [];
    } catch (e) {
      console.warn('Failed to get service types, will try direct approach:', e);
    }
    
    // Keywords to match for Xray services
    const xrayKeywords = ['xray', 'x-ray', 'radiology', 'chest x-ray', 'bone x-ray'];
    
    // Find matching service types (case-insensitive)
    let matchingServiceTypes = [];
    if (allServiceTypes.length > 0) {
      matchingServiceTypes = allServiceTypes.filter(st => {
        const stLower = (st || '').toLowerCase();
        return xrayKeywords.some(keyword => stLower.includes(keyword));
      });
    }
    
    // If we found matching service types, load procedures for each
    if (matchingServiceTypes.length > 0) {
      for (const serviceType of matchingServiceTypes) {
        try {
          const response = await priceListAPI.getProceduresByServiceType(serviceType);
          if (response.data && Array.isArray(response.data) && response.data.length > 0) {
            services = services.concat(response.data);
          }
        } catch (e) {
          console.warn(`Failed to load procedures for service type ${serviceType}:`, e);
          continue;
        }
      }
    }
    
    // If still no services found, try getting all procedures and filter client-side
    if (services.length === 0) {
      try {
        const response = await priceListAPI.getProceduresByServiceType();
        // Response will be grouped object
        if (response.data && typeof response.data === 'object') {
          // Filter service types that match Xray keywords
          const xrayKeys = Object.keys(response.data).filter(key => {
            if (!key) return false;
            const keyLower = key.toLowerCase();
            return xrayKeywords.some(keyword => keyLower.includes(keyword));
          });
          
          // Also check if service names contain xray keywords (for cases where service_type might be generic)
          for (const key in response.data) {
            if (Array.isArray(response.data[key])) {
              const matchingServices = response.data[key].filter(service => {
                const serviceName = (service.service_name || '').toLowerCase();
                return xrayKeywords.some(keyword => serviceName.includes(keyword));
              });
              if (matchingServices.length > 0) {
                services = services.concat(matchingServices);
              }
            }
          }
          
          // Also add services from explicitly matching service types
          for (const key of xrayKeys) {
            if (Array.isArray(response.data[key])) {
              services = services.concat(response.data[key]);
            }
          }
          
          // Remove duplicates based on g_drg_code
          const seen = new Set();
          services = services.filter(service => {
            const code = service.g_drg_code;
            if (seen.has(code)) return false;
            seen.add(code);
            return true;
          });
        }
      } catch (e) {
        console.error('Failed to load all procedures:', e);
      }
    }
    
    availableServices.value = services;
    
    if (services.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No Xray services found. Please contact admin to add Xray service types.',
        timeout: 5000,
      });
    } else {
      console.log(`Loaded ${services.length} Xray services`);
    }
  } catch (error) {
    console.error('Failed to load services:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load available services',
    });
    availableServices.value = [];
  } finally {
    loadingServices.value = false;
  }
};

const openUpdateServiceDialog = async (investigation) => {
  selectedInvestigation.value = investigation;
  serviceForm.value = {
    gdrg_code: investigation.gdrg_code || '',
    procedure_name: investigation.procedure_name || '',
    notes: investigation.notes || '',
  };
  
  // Load available services if not already loaded
  if (availableServices.value.length === 0) {
    await loadAvailableServices();
  }
  
  // Initialize filtered options
  filteredServiceOptions.value = availableServices.value;
  
  // Find and set the selected service
  const selectedService = availableServices.value.find(
    s => s.g_drg_code === investigation.gdrg_code
  );
  if (selectedService) {
    serviceForm.value.gdrg_code = selectedService;
  }
  
  showUpdateServiceDialog.value = true;
};

const onServiceSelected = (service) => {
  if (service && typeof service === 'object') {
    serviceForm.value.procedure_name = service.service_name || '';
    serviceForm.value.gdrg_code = service.g_drg_code || '';
  }
};

const updateService = async () => {
  if (!selectedInvestigation.value) return;
  
  updatingService.value = true;
  try {
    const updateData = {
      gdrg_code: typeof serviceForm.value.gdrg_code === 'object' 
        ? serviceForm.value.gdrg_code.g_drg_code 
        : serviceForm.value.gdrg_code,
      procedure_name: serviceForm.value.procedure_name,
      investigation_type: 'xray',
      notes: serviceForm.value.notes || null,
    };
    
    await consultationAPI.updateInvestigationDetails(selectedInvestigation.value.id, updateData);
    $q.notify({
      type: 'positive',
      message: 'Service updated successfully',
    });
    showUpdateServiceDialog.value = false;
    await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update service',
    });
  } finally {
    updatingService.value = false;
  }
};

const openAddServiceDialog = async (investigation) => {
  selectedInvestigation.value = investigation;
  addServiceForm.value = {
    gdrg_code: '',
    procedure_name: '',
    notes: '',
  };
  
  // Load available services if not already loaded
  if (availableServices.value.length === 0) {
    await loadAvailableServices();
  }
  
  // Initialize filtered options
  filteredServiceOptions.value = availableServices.value;
  
  showAddServiceDialog.value = true;
};

const openAddServiceDialogForNew = async () => {
  // For adding a new service, we need to select from existing requests to get encounter_id
  if (requests.value.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please filter to find a patient request first, then use "Add Service" from the actions column',
    });
    return;
  }
  
  // Use the first request as reference (user can change if needed)
  const firstRequest = requests.value[0];
  selectedInvestigation.value = {
    encounter_id: firstRequest.encounter_id,
    patient_name: firstRequest.patient_name,
    patient_card_number: firstRequest.patient_card_number,
  };
  
  addServiceForm.value = {
    gdrg_code: '',
    procedure_name: '',
    notes: '',
  };
  
  // Load available services if not already loaded
  if (availableServices.value.length === 0) {
    await loadAvailableServices();
  }
  
  // Initialize filtered options
  filteredServiceOptions.value = availableServices.value;
  
  showAddServiceDialog.value = true;
};

const onAddServiceSelected = (service) => {
  if (service && typeof service === 'object') {
    addServiceForm.value.procedure_name = service.service_name || '';
    addServiceForm.value.gdrg_code = service.g_drg_code || '';
  }
};

const filteredServiceOptions = ref([]);

const filterServices = (val, update) => {
  if (val === '') {
    update(() => {
      filteredServiceOptions.value = availableServices.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    filteredServiceOptions.value = availableServices.value.filter(
      (service) =>
        (service.service_name && service.service_name.toLowerCase().includes(needle)) ||
        (service.g_drg_code && service.g_drg_code.toLowerCase().includes(needle))
    );
  });
};

const addService = async () => {
  if (!selectedInvestigation.value) return;
  
  addingService.value = true;
  try {
    const newServiceData = {
      encounter_id: selectedInvestigation.value.encounter_id,
      gdrg_code: typeof addServiceForm.value.gdrg_code === 'object' 
        ? addServiceForm.value.gdrg_code.g_drg_code 
        : addServiceForm.value.gdrg_code,
      procedure_name: addServiceForm.value.procedure_name,
      investigation_type: 'xray',
      notes: addServiceForm.value.notes || null,
    };
    
    await consultationAPI.createInvestigation(newServiceData);
    $q.notify({
      type: 'positive',
      message: 'Service added successfully',
    });
    showAddServiceDialog.value = false;
    await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add service',
    });
  } finally {
    addingService.value = false;
  }
};

onMounted(() => {
  initializeDate();
  loadRequests();
});
</script>
