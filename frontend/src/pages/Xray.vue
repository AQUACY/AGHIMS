<template>
  <q-page class="hms-page">
    <HmsPageHeader title="X-ray" subtitle="Confirm X-ray requests and enter imaging results.">
      <template #actions>
        <HmsButton
          variant="secondary"
          size="sm"
          @click="setTodayDate"
        >
          Today
        </HmsButton>
        <HmsButton
          variant="secondary"
          size="sm"
          :loading="loadingRequests"
          @click="loadRequests"
        >
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div class="diag-toolbar">
      <div class="toolbar-meta">
        <Bone :size="15" />
        <span>{{ requests.length }} request{{ requests.length === 1 ? '' : 's' }}</span>
      </div>
      <div class="toolbar-controls">
        <input
          v-model="searchTerm"
          type="search"
          class="tool-input tool-input--search"
          placeholder="Search card or name…"
          @keyup.enter="loadRequests"
        />
        <input
          v-model="filterDate"
          type="date"
          class="tool-input"
          title="Date"
          @change="loadRequests"
        />
        <select
          v-model="statusFilter"
          class="tool-input"
          @change="loadRequests"
        >
          <option value="">All statuses</option>
          <option
            v-for="opt in statusOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">X-ray Requests</div>
          <div class="panel-sub">{{ requests.length }} request{{ requests.length === 1 ? '' : 's' }}</div>
        </div>
        <div class="panel-actions">
          <HmsButton
            v-if="authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin'"
            variant="secondary"
            size="sm"
            @click="openAddServiceDialogForNew"
          >
            Add Service
          </HmsButton>
        </div>
      </div>
      <q-table
        class="diag-table"
        :rows="requests"
        :columns="requestColumns"
        row-key="id"
        flat
        dense
        :loading="loadingRequests"
        :pagination="{ rowsPerPage: 20 }"
      >
        <template v-slot:body-cell-patient_name="props">
          <q-td :props="props">
            <div class="patient-cell">
              <div class="avatar">{{ patientInitials(props.row) }}</div>
              <div>
                <div class="name">{{ props.row.patient_name || '—' }}</div>
                <div class="sub mono">{{ props.row.patient_card_number || '—' }}</div>
              </div>
            </div>
          </q-td>
        </template>
        <template v-slot:body-cell-patient_card_number="props">
          <q-td :props="props">
            <span class="mono">{{ props.value }}</span>
          </q-td>
        </template>
        <template v-slot:body-cell-status="props">
          <q-td :props="props">
            <HmsBadge :tone="statusTone(props.value)">{{ props.value }}</HmsBadge>
          </q-td>
        </template>
        <template v-slot:body-cell-encounter_date="props">
          <q-td :props="props">
            {{ formatDate(props.value || props.row.created_at) }}
          </q-td>
        </template>
        <template v-slot:body-cell-source="props">
          <q-td :props="props">
            <HmsBadge
              :tone="(props.value === 'inpatient' || props.row.prescription_type === 'inpatient') ? 'healthcare' : 'info'"
            >
              {{ (props.value === 'inpatient' || props.row.prescription_type === 'inpatient') ? 'IPD' : 'OPD' }}
            </HmsBadge>
          </q-td>
        </template>
        <template v-slot:body-cell-ward="props">
          <q-td :props="props">
            <span v-if="props.value || props.row.bed_number">
              {{ props.value || '' }}{{ props.row.bed_number ? ` / ${props.row.bed_number}` : '' }}
            </span>
            <span v-else class="text-muted">-</span>
          </q-td>
        </template>
        <template v-slot:body-cell-actions="props">
          <q-td :props="props">
            <div class="row-actions">
              <q-btn
                size="sm"
                color="info"
                icon="visibility"
                flat
                round
                dense
                @click="viewRemarks(props.row)"
              >
                <q-tooltip>View Remarks/Notes</q-tooltip>
              </q-btn>
              <q-btn
                size="sm"
                color="purple"
                icon="description"
                flat
                round
                dense
                @click="viewDoctorNotes(props.row)"
              >
                <q-tooltip>View Doctor Notes / Treatment Plan</q-tooltip>
              </q-btn>
              <HmsButton
                v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin')"
                variant="secondary"
                size="sm"
                @click="openUpdateServiceDialog(props.row)"
              >
                Update Service
              </HmsButton>
              <HmsButton
                v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Xray' || authStore.userRole === 'Xray Head' || authStore.userRole === 'Admin')"
                variant="soft"
                size="sm"
                @click="openAddServiceDialog(props.row)"
              >
                Add Service
              </HmsButton>
              <HmsButton
                v-if="props.row.status === 'requested'"
                variant="primary"
                size="sm"
                :loading="confirmingId === props.row.id"
                :disabled="confirmingId !== null"
                @click="confirmInvestigation(props.row)"
              >
                Confirm
              </HmsButton>
              <HmsButton
                v-if="props.row.status === 'confirmed'"
                variant="healthcare"
                size="sm"
                @click="navigateToResultPage(props.row)"
              >
                Add Results
              </HmsButton>
              <HmsButton
                v-if="props.row.status === 'completed'"
                variant="secondary"
                size="sm"
                @click="navigateToResultPage(props.row)"
              >
                View Results
              </HmsButton>
              <HmsButton
                v-if="props.row.status === 'confirmed' && authStore.userRole === 'Admin'"
                variant="outline"
                size="sm"
                :loading="revertingToRequestedId === props.row.id"
                @click="revertToRequested(props.row)"
              >
                Revert to Requested
              </HmsButton>
              <HmsButton
                v-if="props.row.status === 'completed' && (authStore.userRole === 'Admin' || authStore.userRole === 'Xray Head')"
                variant="outline"
                size="sm"
                :loading="revertingId === props.row.id"
                @click="revertInvestigationStatus(props.row)"
              >
                Revert to Confirmed
              </HmsButton>
            </div>
          </q-td>
        </template>
      </q-table>
      <div v-if="!loadingRequests && requests.length === 0" class="empty-hint">
        No x-ray requests found for the selected filters
      </div>
    </section>

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

    <!-- View Doctor Notes / Treatment Plan Dialog -->
    <q-dialog v-model="showDoctorNotesDialog">
      <q-card style="min-width: 500px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">{{ viewingDoctorNotes?.isInpatient ? 'Treatment Plan' : 'Doctor Notes' }}</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="viewingDoctorNotes">
            {{ viewingDoctorNotes?.procedure_name || 'Investigation' }} ({{ viewingDoctorNotes?.gdrg_code }})
          </div>
        </q-card-section>
        <q-card-section>
          <div v-if="loadingDoctorNotes" class="text-center q-pa-md">
            <q-spinner color="primary" size="3em" />
            <div class="q-mt-md">Loading...</div>
          </div>
          <div v-else-if="viewingDoctorNotes?.notes" class="text-body1 q-pa-md" style="background-color: #f5f5f5; border-radius: 4px; white-space: pre-wrap;">
            {{ viewingDoctorNotes.notes }}
          </div>
          <div v-else class="text-grey-6 text-center q-pa-md">
            {{ viewingDoctorNotes?.isInpatient ? 'No treatment plan available for this clinical review' : 'No doctor notes available for this consultation' }}
          </div>
          <div v-if="viewingDoctorNotes?.reviewed_by_name && !loadingDoctorNotes" class="text-caption text-grey-7 q-mt-md">
            Reviewed by: {{ viewingDoctorNotes.reviewed_by_name }} 
            <span v-if="viewingDoctorNotes.reviewed_at">
              on {{ new Date(viewingDoctorNotes.reviewed_at).toLocaleString() }}
            </span>
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
import { Bone } from 'lucide-vue-next';
import { consultationAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// Request list functionality
const requests = ref([]);
const loadingRequests = ref(false);
const searchTerm = ref('');
const filterDate = ref('');
const statusFilter = ref('');
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
const showDoctorNotesDialog = ref(false);
const viewingDoctorNotes = ref(null);
const loadingDoctorNotes = ref(false);
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
  { name: 'requested_by_name', label: 'Requested By', field: 'requested_by_name', align: 'left', sortable: true },
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

const statusTone = (status) => {
  const s = String(status || '').toLowerCase();
  if (s === 'requested') return 'warning';
  if (s === 'confirmed') return 'info';
  if (s === 'completed') return 'success';
  if (s === 'cancelled' || s === 'rejected') return 'critical';
  return 'muted';
};

const patientInitials = (row) => {
  const parts = String(row?.patient_name || '?').trim().split(/\s+/);
  const a = (parts[0] || '?')[0] || '?';
  const b = (parts[1] || '')[0] || '';
  return `${a}${b}`.toUpperCase();
};

const setTodayDate = () => {
  initializeDate();
  loadRequests();
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

const viewDoctorNotes = async (investigation) => {
  viewingDoctorNotes.value = {
    ...investigation,
    notes: null,
    isInpatient: investigation.source === 'inpatient' || investigation.prescription_type === 'inpatient'
  };
  showDoctorNotesDialog.value = true;
  loadingDoctorNotes.value = true;
  
  try {
    if (investigation.source === 'inpatient' || investigation.prescription_type === 'inpatient') {
      // IPD: Get treatment plan from clinical review
      if (investigation.clinical_review_id) {
        const response = await consultationAPI.getInpatientClinicalReview(investigation.clinical_review_id);
        if (response.data) {
          viewingDoctorNotes.value.notes = response.data.review_notes || null;
          viewingDoctorNotes.value.reviewed_by_name = response.data.reviewed_by_name || null;
          viewingDoctorNotes.value.reviewed_at = response.data.reviewed_at || null;
        }
      }
    } else {
      // OPD: Get doctor notes from consultation
      if (investigation.encounter_id) {
        const response = await consultationAPI.getConsultationNotes(investigation.encounter_id);
        if (response.data) {
          viewingDoctorNotes.value.notes = response.data.doctor_notes || null;
        }
      }
    }
  } catch (error) {
    console.error('Error loading doctor notes:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load notes',
    });
  } finally {
    loadingDoctorNotes.value = false;
  }
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
    
    // Use the correct endpoint based on whether it's an inpatient or OPD investigation
    const isInpatient = selectedInvestigation.value.source === 'inpatient' || 
                        selectedInvestigation.value.prescription_type === 'inpatient';
    
    if (isInpatient) {
      await consultationAPI.updateInpatientInvestigationDetails(selectedInvestigation.value.id, updateData);
    } else {
      await consultationAPI.updateInvestigationDetails(selectedInvestigation.value.id, updateData);
    }
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

<style scoped>
.diag-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.95rem;
}
.toolbar-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  font-weight: 600;
}
.toolbar-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.tool-input {
  height: 2.15rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  padding: 0 0.7rem;
}
.tool-input--search {
  min-width: 11rem;
}
.diag-panel {
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  overflow: hidden;
}
.panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}
.panel-title {
  font-size: var(--hms-text-base);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.panel-sub {
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
}
.diag-table {
  background: transparent;
}
.diag-table :deep(th) {
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 700;
}
.empty-hint {
  text-align: center;
  color: var(--hms-text-muted);
  padding: 1.25rem 1rem;
  font-size: var(--hms-text-sm);
}
.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  justify-content: center;
}
.patient-cell {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
}
.avatar {
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 9999px;
  background: linear-gradient(145deg, var(--hms-accent-muted), rgba(219, 39, 119, 0.14));
  color: var(--hms-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 750;
  flex-shrink: 0;
}
.name {
  font-weight: 700;
  color: var(--hms-text-primary);
}
.sub {
  margin-top: 0.1rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.mono {
  font-family: var(--hms-font-mono);
  font-size: 0.75rem;
}
.text-muted {
  color: var(--hms-text-muted);
}
@media (max-width: 720px) {
  .toolbar-controls {
    width: 100%;
  }
  .tool-input {
    flex: 1;
    min-width: 0;
  }
}
</style>
