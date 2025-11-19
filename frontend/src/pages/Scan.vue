<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Scan/Imaging Services</div>

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

    <!-- Scan Requests Table -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Scan Requests</div>
          <q-space />
          <q-btn
            v-if="selectedInvestigations.length > 0 && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
            color="positive"
            icon="check"
            :label="`Confirm Selected (${selectedInvestigations.length})`"
            @click="bulkConfirmInvestigations"
            :loading="bulkConfirming"
            class="q-mr-md"
          />
          <q-btn
            v-if="authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin'"
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
          v-model:selected="selectedInvestigations"
          selection="multiple"
        >
          <template v-slot:top-row>
            <q-tr>
              <q-td auto-width>
                <q-checkbox
                  :model-value="allSelected"
                  @update:model-value="selectAll"
                  indeterminate-icon="remove"
                />
              </q-td>
              <q-td colspan="100%">
                <div class="text-caption text-grey-7">
                  Select investigations to confirm multiple at once
                </div>
              </q-td>
            </q-tr>
          </template>
          <template v-slot:body-cell-selection="props">
            <q-td :props="props">
              <q-checkbox
                v-if="props.row.status === 'requested'"
                :model-value="props.selected"
                @update:model-value="props.select"
              />
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
                  v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
                  size="sm"
                  color="secondary"
                  label="Update Service"
                  @click="openUpdateServiceDialog(props.row)"
                />
                <q-btn
                  v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
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
                  v-if="props.row.status === 'completed' && (authStore.userRole === 'Admin' || authStore.userRole === 'Scan Head')"
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
          No scan requests found for the selected filters
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
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Add New Service</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation && !addServiceForm.isDirectService">
            Patient: {{ selectedInvestigation.patient_name }} ({{ selectedInvestigation.patient_card_number }})
          </div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addService" class="q-gutter-md">
            <!-- Direct Service Toggle -->
            <q-toggle
              v-model="addServiceForm.isDirectService"
              label="Direct Service (Walk-in, no consultation)"
              @update:model-value="onDirectServiceToggle"
            />
            
            <!-- Patient Selection for Direct Services -->
            <div v-if="addServiceForm.isDirectService" class="q-gutter-md">
              <q-toggle
                v-model="addServiceForm.hasCardNumber"
                label="Patient has Card Number"
                @update:model-value="onCardNumberToggle"
              />
              
              <!-- With Card Number -->
              <div v-if="addServiceForm.hasCardNumber">
                <q-input
                  v-model="addServiceForm.patientCardNumber"
                  filled
                  label="Patient Card Number"
                  @blur="loadPatientByCard"
                  :loading="loadingPatients"
                >
                  <template v-slot:append>
                    <q-icon name="search" />
                  </template>
                </q-input>
                <div v-if="availablePatients.length > 0" class="q-mt-md">
                  <div class="text-subtitle2 q-mb-sm">Select Patient:</div>
                  <q-list bordered separator>
                    <q-item
                      v-for="patient in availablePatients"
                      :key="patient.id"
                      tag="label"
                      v-ripple
                    >
                      <q-item-section avatar>
                        <q-radio
                          v-model="selectedPatients"
                          :val="patient.id"
                          @update:model-value="onPatientSelected"
                        />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label>{{ patient.name }} {{ patient.surname || '' }}<span v-if="patient.other_names"> {{ patient.other_names }}</span></q-item-label>
                        <q-item-label caption>Card: {{ patient.card_number }}</q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
              </div>
              
              <!-- Without Card Number (Name, Phone, Age) -->
              <div v-else class="q-gutter-md">
                <q-input
                  v-model="addServiceForm.patientName"
                  filled
                  label="Patient Name *"
                  :rules="[(val) => !!val || 'Name is required']"
                />
                <q-input
                  v-model="addServiceForm.patientPhone"
                  filled
                  label="Phone Number *"
                  :rules="[(val) => !!val || 'Phone number is required']"
                />
                <q-input
                  v-model="addServiceForm.patientAge"
                  filled
                  type="number"
                  label="Age *"
                  :rules="[(val) => !!val && val > 0 || 'Age is required']"
                />
                <q-select
                  v-model="addServiceForm.patientGender"
                  :options="['Male', 'Female', 'Other']"
                  filled
                  label="Gender *"
                  :rules="[(val) => !!val || 'Gender is required']"
                />
              </div>
              
              <q-toggle
                v-model="addServiceForm.isInsured"
                label="Patient is Insured"
              />
              <q-input
                v-if="addServiceForm.isInsured"
                v-model="addServiceForm.cccNumber"
                filled
                label="CCC Number (Optional)"
              />
            </div>
            
            <!-- Patient Selection for Services with Encounter -->
            <div v-else-if="requests.length > 0" class="q-mt-md">
              <div class="text-subtitle2 q-mb-sm">Select Patient(s) from existing requests:</div>
              <q-list bordered separator>
                <q-item
                  v-for="request in uniquePatients"
                  :key="request.patient_card_number"
                  tag="label"
                  v-ripple
                >
                  <q-item-section avatar>
                    <q-checkbox
                      v-model="selectedPatients"
                      :val="request.encounter_id"
                      @update:model-value="onPatientSelected"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ request.patient_name }}</q-item-label>
                    <q-item-label caption>Card: {{ request.patient_card_number }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-banner
                v-if="selectedPatients.length > 1"
                class="bg-warning text-dark q-mt-md"
                rounded
              >
                <template v-slot:avatar>
                  <q-icon name="warning" color="dark" />
                </template>
                You can only add service for one patient at a time. Please select only one patient.
              </q-banner>
            </div>
            
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
                :disable="selectedPatients.length !== 1 && !addServiceForm.isDirectService"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI, patientsAPI } from '../services/api';
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
const selectedInvestigations = ref([]);
const bulkConfirming = ref(false);
const serviceForm = ref({
  gdrg_code: '',
  procedure_name: '',
  notes: '',
});
const addServiceForm = ref({
  gdrg_code: '',
  procedure_name: '',
  notes: '',
  isDirectService: false,
  hasCardNumber: true,
  patientCardNumber: '',
  patientId: null,
  patientName: '',
  patientPhone: '',
  patientAge: null,
  patientGender: '',
  isInsured: false,
  cccNumber: '',
});
const selectedPatients = ref([]);
const availablePatients = ref([]);
const loadingPatients = ref(false);

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
      investigation_type: 'scan',
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
      consultationAPI.getInvestigationsByType('scan', filters).catch(err => {
        console.error('Failed to load OPD investigations:', err);
        return { data: [] };
      }),
      consultationAPI.getInpatientInvestigationsByType('scan', filters).catch(err => {
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
      message: error.response?.data?.detail || 'Failed to load scan requests',
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

const viewRemarks = (investigation) => {
  viewingRemarks.value = investigation;
  showRemarksDialog.value = true;
};

const navigateToResultPage = (request) => {
  router.push(`/scan/result/${request.id}`);
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
    
    // First, try to get procedures directly for "Scan" service type (most common case)
    // Try multiple variations and collect all results (don't break after first match)
    const directServiceTypes = ['Scan', 'scan', 'SCAN', 'Scanning', 'Imaging', 'Radiology', 'ECG', 'EKG'];
    
    for (const serviceType of directServiceTypes) {
      try {
        const response = await priceListAPI.getProceduresByServiceType(serviceType);
        if (response.data && Array.isArray(response.data) && response.data.length > 0) {
          services = services.concat(response.data);
          console.log(`Loaded ${response.data.length} procedures for service type: ${serviceType}`);
          // Don't break - continue to collect all matching service types
        }
      } catch (e) {
        console.warn(`Failed to load procedures for service type ${serviceType}:`, e);
        continue;
      }
    }
    
    // Remove duplicates from direct service type queries
    if (services.length > 0) {
      const seen = new Set();
      services = services.filter(service => {
        const code = service.g_drg_code;
        if (!code || seen.has(code)) return false;
        seen.add(code);
        return true;
      });
      console.log(`After direct queries: ${services.length} unique services`);
    }
    
    // Always get all available service types and match (don't skip if we already found some)
    // This ensures we get all scan-related services, not just the first match
    let allServiceTypes = [];
    try {
      const serviceTypesResponse = await priceListAPI.getServiceTypes();
      allServiceTypes = serviceTypesResponse.data || [];
      console.log('Available service types:', allServiceTypes);
    } catch (e) {
      console.warn('Failed to get service types, will try direct approach:', e);
    }
    
    // Keywords to match for Scan services
    const scanKeywords = ['scan', 'imaging', 'radiology', 'ultrasound', 'ct', 'mri', 'ecg', 'sonography', 'doppler', 'x-ray', 'xray'];
    
    // Find matching service types (case-insensitive)
    let matchingServiceTypes = [];
    if (allServiceTypes.length > 0) {
      matchingServiceTypes = allServiceTypes.filter(st => {
        if (!st) return false;
        const stLower = (st || '').toLowerCase();
        return scanKeywords.some(keyword => stLower.includes(keyword));
      });
      console.log('Matching service types:', matchingServiceTypes);
    }
    
    // If we found matching service types, load procedures for each
    // Skip service types we already tried in directServiceTypes
    const alreadyTried = new Set(directServiceTypes.map(s => s.toLowerCase()));
    for (const serviceType of matchingServiceTypes) {
      // Skip if we already tried this service type
      if (alreadyTried.has(serviceType.toLowerCase())) {
        continue;
      }
      try {
        const response = await priceListAPI.getProceduresByServiceType(serviceType);
        if (response.data && Array.isArray(response.data) && response.data.length > 0) {
          services = services.concat(response.data);
          console.log(`Loaded ${response.data.length} procedures for service type: ${serviceType}`);
        }
      } catch (e) {
        console.warn(`Failed to load procedures for service type ${serviceType}:`, e);
        continue;
      }
    }
    
    // Remove duplicates after collecting from all sources
    if (services.length > 0) {
      const seen = new Set();
      services = services.filter(service => {
        const code = service.g_drg_code;
        if (!code || seen.has(code)) return false;
        seen.add(code);
        return true;
      });
      console.log(`After collecting all service types: ${services.length} unique services`);
    }
    
    // If still no services found (or to catch any we might have missed), try getting all procedures and filter client-side
    // Always try this as a fallback to ensure we get everything
    if (services.length === 0 || services.length < 5) {  // If we have very few services, try the fallback
      try {
        console.log('Attempting to load all procedures and filter client-side...');
        const response = await priceListAPI.getProceduresByServiceType();
        // Response will be grouped object
        if (response.data && typeof response.data === 'object') {
          // Keywords to match for Scan services
          const scanKeywords = ['scan', 'imaging', 'radiology', 'ultrasound', 'ct', 'mri', 'ecg', 'sonography', 'doppler'];
          
          // Filter service types that match Scan keywords
          const scanKeys = Object.keys(response.data).filter(key => {
            if (!key) return false;
            const keyLower = key.toLowerCase();
            return scanKeywords.some(keyword => keyLower.includes(keyword));
          });
          console.log('Service type keys matching scan keywords:', scanKeys);
          
          // Also check if service names contain scan keywords (for cases where service_type might be generic)
          for (const key in response.data) {
            if (Array.isArray(response.data[key])) {
              const matchingServices = response.data[key].filter(service => {
                const serviceName = (service.service_name || '').toLowerCase();
                return scanKeywords.some(keyword => serviceName.includes(keyword));
              });
              if (matchingServices.length > 0) {
                services = services.concat(matchingServices);
                console.log(`Found ${matchingServices.length} services matching scan keywords in service type: ${key}`);
              }
            }
          }
          
          // Also add services from explicitly matching service types
          for (const key of scanKeys) {
            if (Array.isArray(response.data[key])) {
              services = services.concat(response.data[key]);
              console.log(`Added ${response.data[key].length} services from service type: ${key}`);
            }
          }
          
          // Remove duplicates based on g_drg_code
          const seen = new Set();
          services = services.filter(service => {
            const code = service.g_drg_code;
            if (!code || seen.has(code)) return false;
            seen.add(code);
            return true;
          });
          console.log(`After deduplication: ${services.length} unique services`);
        }
      } catch (e) {
        console.error('Failed to load all procedures:', e);
      }
    }
    
    availableServices.value = services;
    
    if (services.length === 0) {
      console.error('No Scan services found after all attempts');
      $q.notify({
        type: 'warning',
        message: 'No Scan services found. Please contact admin to add Scan service types.',
        timeout: 5000,
      });
    } else {
      console.log(`Successfully loaded ${services.length} Scan services`);
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
      investigation_type: 'scan',
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
    isDirectService: false,
    patientCardNumber: '',
    patientId: null,
    isInsured: false,
    cccNumber: '',
  };
  selectedPatients.value = [investigation.encounter_id];
  availablePatients.value = [];
  
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

// Computed properties
const uniquePatients = computed(() => {
  const seen = new Set();
  return requests.value.filter(request => {
    const key = request.patient_card_number;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

const allSelected = computed(() => {
  const requestedInvestigations = requests.value.filter(r => r.status === 'requested');
  return requestedInvestigations.length > 0 && 
         selectedInvestigations.value.length === requestedInvestigations.length;
});

// Selection handlers
// Note: We use v-model:selected instead of @selection to avoid conflicts
// Quasar will automatically sync selectedInvestigations with the table's selection state

const selectAll = (value) => {
  if (value) {
    // Select all requested rows only (not confirmed or completed)
    const requestedRows = requests.value.filter(r => r.status === 'requested');
    selectedInvestigations.value = [...requestedRows];
  } else {
    // Deselect all requested rows
    const requestedIds = new Set(requests.value.filter(r => r.status === 'requested').map(r => r.id));
    selectedInvestigations.value = selectedInvestigations.value.filter(r => !requestedIds.has(r.id));
  }
};

// Bulk confirm
const bulkConfirmInvestigations = async () => {
  // Filter to only requested investigations
  const requestedInvestigations = selectedInvestigations.value.filter(inv => inv.status === 'requested');
  
  if (requestedInvestigations.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please select at least one investigation with "requested" status to confirm',
    });
    return;
  }

  // Separate IPD and OPD investigations
  const ipdInvestigations = requestedInvestigations.filter(inv => inv.source === 'inpatient' || inv.prescription_type === 'inpatient');
  const opdInvestigations = requestedInvestigations.filter(inv => inv.source !== 'inpatient' && inv.prescription_type !== 'inpatient');

  bulkConfirming.value = true;
  try {
    let totalConfirmed = 0;
    let totalRequested = 0;
    const allErrors = [];

    // Confirm IPD investigations
    if (ipdInvestigations.length > 0) {
      const ipdIds = ipdInvestigations.map(inv => inv.id);
      // For IPD, show dialog to ask if they want to add to IPD bill
      const addToBill = await new Promise((resolve) => {
        $q.dialog({
          title: 'Confirm IPD Investigations',
          message: `You are about to confirm ${ipdInvestigations.length} IPD investigation(s). Add to IPD bill?`,
          cancel: true,
          persistent: true,
          options: {
            type: 'checkbox',
            model: [true],
            items: [
              { label: 'Add to IPD bill', value: true }
            ]
          }
        }).onOk((result) => {
          resolve(result && result[0] ? true : false);
        }).onCancel(() => {
          resolve(null); // User cancelled
        });
      });

      if (addToBill === null) {
        // User cancelled
        bulkConfirming.value = false;
        return;
      }

      try {
        const response = await consultationAPI.bulkConfirmInpatientInvestigations(ipdIds, addToBill);
        totalConfirmed += response.data.confirmed_count;
        totalRequested += response.data.total_requested;
        if (response.data.errors && response.data.errors.length > 0) {
          allErrors.push(...response.data.errors);
        }
      } catch (error) {
        allErrors.push(`IPD confirm error: ${error.response?.data?.detail || 'Unknown error'}`);
      }
    }

    // Confirm OPD investigations
    if (opdInvestigations.length > 0) {
      const opdIds = opdInvestigations.map(inv => inv.id);
      const response = await consultationAPI.bulkConfirmInvestigations(opdIds);
      totalConfirmed += response.data.confirmed_count;
      totalRequested += response.data.total_requested;
      if (response.data.errors && response.data.errors.length > 0) {
        allErrors.push(...response.data.errors);
      }
    }

    if (allErrors.length > 0) {
      $q.notify({
        type: 'warning',
        message: `Confirmed ${totalConfirmed} of ${totalRequested} investigations. Some errors occurred.`,
        caption: allErrors.join('; '),
        timeout: 5000,
      });
    } else {
      $q.notify({
        type: 'positive',
        message: `Successfully confirmed ${totalConfirmed} investigation(s)`,
      });
    }
    
    // Clear selection and reload
    selectedInvestigations.value = [];
    await loadRequests();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm investigations',
    });
  } finally {
    bulkConfirming.value = false;
  }
};

// Patient selection handlers
const onPatientSelected = (value) => {
  if (value.length > 1) {
    $q.notify({
      type: 'warning',
      message: 'You can only add service for one patient at a time. Please select only one patient.',
    });
    // Keep only the last selected
    selectedPatients.value = [value[value.length - 1]];
  }
};

const onDirectServiceToggle = (value) => {
  if (value) {
    selectedPatients.value = [];
    availablePatients.value = [];
  } else {
    // Reset form when toggling off
    addServiceForm.value.hasCardNumber = true;
    addServiceForm.value.patientCardNumber = '';
    addServiceForm.value.patientName = '';
    addServiceForm.value.patientPhone = '';
    addServiceForm.value.patientAge = null;
    addServiceForm.value.patientGender = '';
  }
};

const onCardNumberToggle = (value) => {
  if (value) {
    // Switching to card number mode - clear name/phone/age
    addServiceForm.value.patientName = '';
    addServiceForm.value.patientPhone = '';
    addServiceForm.value.patientAge = null;
    addServiceForm.value.patientGender = '';
    selectedPatients.value = [];
  } else {
    // Switching to name/phone/age mode - clear card number
    addServiceForm.value.patientCardNumber = '';
    availablePatients.value = [];
    selectedPatients.value = [];
  }
};

const loadPatientByCard = async () => {
  if (!addServiceForm.value.patientCardNumber || !addServiceForm.value.isDirectService) {
    return;
  }
  
  loadingPatients.value = true;
  try {
    const response = await patientsAPI.getByCard(addServiceForm.value.patientCardNumber);
    if (response.data && Array.isArray(response.data) && response.data.length > 0) {
      availablePatients.value = response.data;
      // Auto-select if only one patient found
      if (response.data.length === 1) {
        selectedPatients.value = [response.data[0].id];
        addServiceForm.value.isInsured = response.data[0].insured || false;
        addServiceForm.value.cccNumber = response.data[0].ccc_number || '';
      }
    } else {
      availablePatients.value = [];
      $q.notify({
        type: 'warning',
        message: 'No patient found with this card number',
      });
    }
  } catch (error) {
    console.error('Failed to load patient:', error);
    availablePatients.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load patient',
    });
  } finally {
    loadingPatients.value = false;
  }
};

// Update addService function
const addService = async () => {
  // Validate patient selection
  if (!addServiceForm.value.isDirectService && selectedPatients.value.length !== 1) {
    $q.notify({
      type: 'warning',
      message: 'Please select exactly one patient',
    });
    return;
  }
  
  if (addServiceForm.value.isDirectService) {
    // Validate direct service patient info
    if (addServiceForm.value.hasCardNumber) {
      // Must have selected a patient from card number search
      if (selectedPatients.value.length !== 1) {
        $q.notify({
          type: 'warning',
          message: 'Please select a patient from the search results',
        });
        return;
      }
    } else {
      // Must have name, phone, and age
      if (!addServiceForm.value.patientName || !addServiceForm.value.patientPhone || !addServiceForm.value.patientAge || !addServiceForm.value.patientGender) {
        $q.notify({
          type: 'warning',
          message: 'Please provide patient name, phone number, age, and gender',
        });
        return;
      }
    }
  }
  
  addingService.value = true;
  try {
    const newServiceData = {
      gdrg_code: typeof addServiceForm.value.gdrg_code === 'object' 
        ? addServiceForm.value.gdrg_code.g_drg_code 
        : addServiceForm.value.gdrg_code,
      procedure_name: addServiceForm.value.procedure_name,
      investigation_type: 'scan',
      notes: addServiceForm.value.notes || null,
    };
    
    if (addServiceForm.value.isDirectService) {
      // Direct service without encounter
      if (addServiceForm.value.hasCardNumber) {
        // Patient with card number
        const selectedPatient = availablePatients.value.find(p => p.id === selectedPatients.value[0]);
        if (!selectedPatient) {
          throw new Error('Selected patient not found');
        }
        newServiceData.patient_id = selectedPatient.id;
        newServiceData.patient_card_number = selectedPatient.card_number;
      } else {
        // Patient without card number - use name, phone, age
        newServiceData.patient_name = addServiceForm.value.patientName;
        newServiceData.patient_phone = addServiceForm.value.patientPhone;
        newServiceData.patient_age = addServiceForm.value.patientAge;
        newServiceData.patient_gender = addServiceForm.value.patientGender;
      }
      newServiceData.is_insured = addServiceForm.value.isInsured;
      newServiceData.ccc_number = addServiceForm.value.cccNumber || null;
    } else {
      // Service with encounter
      const selectedRequest = requests.value.find(r => r.encounter_id === selectedPatients.value[0]);
      if (!selectedRequest) {
        throw new Error('Selected request not found');
      }
      newServiceData.encounter_id = selectedRequest.encounter_id;
    }
    
    await consultationAPI.createInvestigation(newServiceData);
    $q.notify({
      type: 'positive',
      message: 'Service added successfully',
    });
    showAddServiceDialog.value = false;
    // Reset form
    addServiceForm.value = {
      gdrg_code: '',
      procedure_name: '',
      notes: '',
      isDirectService: false,
      hasCardNumber: true,
      patientCardNumber: '',
      patientId: null,
      patientName: '',
      patientPhone: '',
      patientAge: null,
      patientGender: '',
      isInsured: false,
      cccNumber: '',
    };
    selectedPatients.value = [];
    availablePatients.value = [];
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

// Update openAddServiceDialogForNew
const openAddServiceDialogForNew = async () => {
  selectedInvestigation.value = null;
  addServiceForm.value = {
    gdrg_code: '',
    procedure_name: '',
    notes: '',
    isDirectService: false,
    hasCardNumber: true,
    patientCardNumber: '',
    patientId: null,
    patientName: '',
    patientPhone: '',
    patientAge: null,
    patientGender: '',
    isInsured: false,
    cccNumber: '',
  };
  selectedPatients.value = [];
  availablePatients.value = [];
  
  // Load available services if not already loaded
  if (availableServices.value.length === 0) {
    await loadAvailableServices();
  }
  
  // Initialize filtered options
  filteredServiceOptions.value = availableServices.value;
  
  showAddServiceDialog.value = true;
};

onMounted(() => {
  initializeDate();
  loadRequests();
});
</script>
