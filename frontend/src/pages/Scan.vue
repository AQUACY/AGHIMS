<template>
  <q-page class="hms-page">
    <HmsPageHeader title="Scan / Imaging" subtitle="Confirm imaging requests and enter scan results.">
      <template #actions>
        <HmsButton
          variant="secondary"
          size="sm"
          :disabled="filtersLocked"
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
        <ScanIcon :size="15" />
        <span>{{ requests.length }} request{{ requests.length === 1 ? '' : 's' }}</span>
        <HmsBadge v-if="filtersLocked" tone="success">Locked</HmsBadge>
      </div>
      <div class="toolbar-controls">
        <input
          v-model="searchTerm"
          type="search"
          class="tool-input tool-input--search"
          placeholder="Search card or name…"
          :disabled="filtersLocked"
          @keyup.enter="loadRequests"
        />
        <input
          v-model="filterDate"
          type="date"
          class="tool-input"
          title="Date"
          :disabled="filtersLocked"
          @change="loadRequests"
        />
        <select
          v-model="statusFilter"
          class="tool-input"
          :disabled="filtersLocked"
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
        <q-select
          v-model="procedureFilter"
          dense
          outlined
          :options="procedureOptions"
          label="Procedure"
          class="tool-select"
          @update:model-value="loadRequests"
          :clearable="!filtersLocked"
          :disable="filtersLocked"
          use-input
          input-debounce="0"
          @filter="filterProcedures"
        >
          <template v-slot:no-option>
            <q-item>
              <q-item-section class="text-grey">
                No procedures found
              </q-item-section>
            </q-item>
          </template>
        </q-select>
        <HmsButton
          :variant="filtersLocked ? 'healthcare' : 'secondary'"
          size="sm"
          @click="toggleFilterLock"
        >
          {{ filtersLocked ? 'Unlock' : 'Lock' }}
        </HmsButton>
      </div>
    </div>

    <div v-if="filtersLocked" class="diag-lock-banner">
      <div>
        <div class="lock-title">Filters locked</div>
        <div class="lock-sub">
          <span v-if="lockedSearchTerm">Search: {{ lockedSearchTerm }}</span>
          <span v-if="lockedSearchTerm && lockedFilterDate"> · </span>
          <span v-if="lockedFilterDate">Date: {{ formatLockedDate(lockedFilterDate) }}</span>
          <span v-if="(lockedSearchTerm || lockedFilterDate) && lockedStatusFilter"> · </span>
          <span v-if="lockedStatusFilter">Status: {{ lockedStatusLabel }}</span>
          <span v-if="(lockedSearchTerm || lockedFilterDate || lockedStatusFilter) && lockedProcedureFilter"> · </span>
          <span v-if="lockedProcedureFilter">Procedure: {{ lockedProcedureLabel }}</span>
        </div>
      </div>
      <HmsButton variant="ghost" size="sm" @click="unlockFilters">Unlock</HmsButton>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Scan Requests</div>
          <div class="panel-sub">{{ requests.length }} request{{ requests.length === 1 ? '' : 's' }}</div>
        </div>
        <div class="panel-actions">
          <HmsButton
            v-if="selectedInvestigations.length > 0 && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
            variant="primary"
            size="sm"
            :loading="bulkConfirming"
            @click="bulkConfirmInvestigations"
          >
            Confirm selected ({{ selectedInvestigations.length }})
          </HmsButton>
          <HmsButton
            v-if="authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin'"
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
              <div class="select-hint">
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
                v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
                variant="secondary"
                size="sm"
                @click="openUpdateServiceDialog(props.row)"
              >
                Update Service
              </HmsButton>
              <HmsButton
                v-if="(props.row.status === 'requested' || props.row.status === 'confirmed') && (authStore.userRole === 'Scan' || authStore.userRole === 'Scan Head' || authStore.userRole === 'Admin')"
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
                v-if="props.row.status === 'completed' && (authStore.userRole === 'Admin' || authStore.userRole === 'Scan Head')"
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
        No scan requests found for the selected filters
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
              :option-value="(item) => item"
              label="Search Service (start typing)"
              :loading="loadingServices"
              @update:model-value="onServiceSelected"
              :rules="[(val) => !!val || 'Service is required']"
              use-input
              input-debounce="300"
              @filter="filterServices"
              clearable
              hint="Start typing to search for services"
              emit-value
              map-options
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
              :option-value="(item) => item"
              label="Search Service (start typing)"
              :loading="loadingServices"
              @update:model-value="onAddServiceSelected"
              :rules="[(val) => !!val || 'Service is required']"
              use-input
              input-debounce="300"
              @filter="filterServices"
              clearable
              hint="Start typing to search for services"
              emit-value
              map-options
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
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { Scan as ScanIcon } from 'lucide-vue-next';
import { consultationAPI, priceListAPI, patientsAPI } from '../services/api';
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
const procedureFilter = ref(null);
const statusOptions = [
  { label: 'Requested', value: 'requested' },
  { label: 'Confirmed', value: 'confirmed' },
  { label: 'Completed', value: 'completed' },
  { label: 'Cancelled', value: 'cancelled' }
];
const procedureOptions = ref([]);
const allProcedureOptions = ref([]);

// Filter lock functionality
const filtersLocked = ref(false);
const lockedSearchTerm = ref('');
const lockedFilterDate = ref('');
const lockedStatusFilter = ref(null);
const lockedProcedureFilter = ref(null);
const FILTER_LOCK_KEY = 'scan_page_locked_filters';

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

const lockedStatusLabel = computed(() => {
  const s = lockedStatusFilter.value;
  if (!s) return '';
  if (typeof s === 'object') return s.label || s.value || '';
  return String(s);
});

const lockedProcedureLabel = computed(() => {
  const p = lockedProcedureFilter.value;
  if (!p) return '';
  if (typeof p === 'object') return p.label || p.value || '';
  return String(p);
});

const setTodayDate = () => {
  if (filtersLocked.value) return;
  initializeDate();
  loadRequests();
};

// Load requests with filters
const loadRequests = async () => {
  // If filters are locked, restore them before loading
  if (filtersLocked.value) {
    if (lockedSearchTerm.value && searchTerm.value !== lockedSearchTerm.value) {
      searchTerm.value = lockedSearchTerm.value;
    }
    if (lockedFilterDate.value && filterDate.value !== lockedFilterDate.value) {
      filterDate.value = lockedFilterDate.value;
    }
    if (lockedStatusFilter.value !== null && statusFilter.value !== lockedStatusFilter.value) {
      statusFilter.value = lockedStatusFilter.value;
    }
    if (lockedProcedureFilter.value !== null && procedureFilter.value !== lockedProcedureFilter.value) {
      procedureFilter.value = lockedProcedureFilter.value;
    }
  }
  
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
    
    if (procedureFilter.value) {
      filters.procedure = typeof procedureFilter.value === 'object' 
        ? procedureFilter.value.value || procedureFilter.value.label
        : procedureFilter.value;
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
    
    // Update procedure options from loaded requests
    updateProcedureOptions();
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
        // Only auto-refresh if filters are not locked
        if (!filtersLocked.value) {
          await loadRequests();
        }
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
        // Get clinical review - we need ward_admission_id first
        // Since we have clinical_review_id, we can get the review directly
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
    // Only auto-refresh if filters are not locked
    if (!filtersLocked.value) {
      await loadRequests();
    }
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
      // Only auto-refresh if filters are not locked
      if (!filtersLocked.value) {
        await loadRequests();
      }
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
      // Only auto-refresh if filters are not locked
      if (!filtersLocked.value) {
        await loadRequests();
      }
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
    // Use id as unique identifier, or combination of g_drg_code + service_name if id is not available
    if (services.length > 0) {
      const seen = new Set();
      services = services.filter(service => {
        // Use id if available, otherwise use combination of code + name
        const uniqueKey = service.id 
          ? `id_${service.id}` 
          : `${service.g_drg_code || 'no_code'}_${service.service_name || 'no_name'}`;
        if (seen.has(uniqueKey)) return false;
        seen.add(uniqueKey);
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
    // Use id as unique identifier, or combination of g_drg_code + service_name if id is not available
    if (services.length > 0) {
      const seen = new Set();
      services = services.filter(service => {
        // Use id if available, otherwise use combination of code + name
        const uniqueKey = service.id 
          ? `id_${service.id}` 
          : `${service.g_drg_code || 'no_code'}_${service.service_name || 'no_name'}`;
        if (seen.has(uniqueKey)) return false;
        seen.add(uniqueKey);
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
          
          // Remove duplicates based on id (or combination of g_drg_code + service_name)
          // This ensures all services are kept even if they share the same g_drg_code
          const seen = new Set();
          services = services.filter(service => {
            // Use id if available, otherwise use combination of code + name
            const uniqueKey = service.id 
              ? `id_${service.id}` 
              : `${service.g_drg_code || 'no_code'}_${service.service_name || 'no_name'}`;
            if (seen.has(uniqueKey)) return false;
            seen.add(uniqueKey);
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
  // Since multiple services can have the same g_drg_code, try to match by both code and name
  const selectedService = availableServices.value.find(
    s => s.g_drg_code === investigation.gdrg_code && 
         s.service_name === investigation.procedure_name
  ) || availableServices.value.find(
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
    // Only auto-refresh if filters are not locked
    if (!filtersLocked.value) {
      await loadRequests();
    }
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

// Update procedure options from requests
const updateProcedureOptions = () => {
  const procedures = new Set();
  requests.value.forEach(request => {
    if (request.procedure_name && request.procedure_name.trim()) {
      procedures.add(request.procedure_name.trim());
    }
  });
  allProcedureOptions.value = Array.from(procedures).sort().map(p => ({ label: p, value: p }));
  procedureOptions.value = allProcedureOptions.value;
};

// Filter procedures for the dropdown
const filterProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      procedureOptions.value = allProcedureOptions.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    procedureOptions.value = allProcedureOptions.value.filter(
      (proc) => proc.label.toLowerCase().includes(needle)
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
    // Only auto-refresh if filters are not locked
    if (!filtersLocked.value) {
      await loadRequests();
    }
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
    // Only auto-refresh if filters are not locked
    if (!filtersLocked.value) {
      await loadRequests();
    }
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

// Filter lock functions
const loadLockedFilters = () => {
  try {
    const locked = localStorage.getItem(FILTER_LOCK_KEY);
    if (locked) {
      const filterData = JSON.parse(locked);
      filtersLocked.value = true;
      lockedSearchTerm.value = filterData.searchTerm || '';
      lockedFilterDate.value = filterData.filterDate || '';
      lockedStatusFilter.value = filterData.statusFilter || null;
      lockedProcedureFilter.value = filterData.procedureFilter || null;
      
      // Apply locked filters
      if (lockedSearchTerm.value) {
        searchTerm.value = lockedSearchTerm.value;
      }
      if (lockedFilterDate.value) {
        filterDate.value = lockedFilterDate.value;
      }
      if (lockedStatusFilter.value !== null) {
        const s = lockedStatusFilter.value;
        statusFilter.value = typeof s === 'object' ? (s.value || '') : (s || '');
        lockedStatusFilter.value = statusFilter.value || null;
      }
      if (lockedProcedureFilter.value !== null) {
        procedureFilter.value = lockedProcedureFilter.value;
      }
      
      return true;
    }
    return false;
  } catch (error) {
    console.error('Failed to load locked filters:', error);
    return false;
  }
};

const saveLockedFilters = () => {
  try {
    const filterData = {
      searchTerm: searchTerm.value || '',
      filterDate: filterDate.value || '',
      statusFilter: statusFilter.value || null,
      procedureFilter: procedureFilter.value || null,
      lockedAt: Date.now(),
    };
    localStorage.setItem(FILTER_LOCK_KEY, JSON.stringify(filterData));
    lockedSearchTerm.value = filterData.searchTerm;
    lockedFilterDate.value = filterData.filterDate;
    lockedStatusFilter.value = filterData.statusFilter;
    lockedProcedureFilter.value = filterData.procedureFilter;
    filtersLocked.value = true;
  } catch (error) {
    console.error('Failed to save locked filters:', error);
  }
};

const clearLockedFilters = () => {
  try {
    localStorage.removeItem(FILTER_LOCK_KEY);
    filtersLocked.value = false;
    lockedSearchTerm.value = '';
    lockedFilterDate.value = '';
    lockedStatusFilter.value = null;
    lockedProcedureFilter.value = null;
  } catch (error) {
    console.error('Failed to clear locked filters:', error);
  }
};

const toggleFilterLock = () => {
  if (filtersLocked.value) {
    unlockFilters();
  } else {
    lockFilters();
  }
};

const lockFilters = () => {
  // Check if at least one filter is set
  if (!searchTerm.value && !filterDate.value && !statusFilter.value && !procedureFilter.value) {
    $q.notify({
      type: 'warning',
      message: 'Please set at least one filter before locking',
      timeout: 3000,
    });
    return;
  }
  
  saveLockedFilters();
  
  $q.notify({
    type: 'positive',
    message: 'Filters locked. Auto-refresh disabled when completing services.',
    timeout: 3000,
  });
};

const unlockFilters = () => {
  $q.dialog({
    title: 'Unlock Filters',
    message: 'Are you sure you want to unlock filters? Auto-refresh will be enabled again.',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    clearLockedFilters();
    $q.notify({
      type: 'info',
      message: 'Filters unlocked',
      timeout: 2000,
    });
  });
};

// Helper to format date for locked filter display
const formatLockedDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

// Watch for filter changes and prevent clearing if locked
watch([searchTerm, filterDate, statusFilter, procedureFilter], ([newSearch, newDate, newStatus, newProcedure], [oldSearch, oldDate, oldStatus, oldProcedure]) => {
  if (filtersLocked.value) {
    // If filters are locked and user tries to clear them, restore locked values
    if (lockedSearchTerm.value && !newSearch && oldSearch) {
      nextTick(() => {
        searchTerm.value = lockedSearchTerm.value;
      });
    }
    if (lockedFilterDate.value && !newDate && oldDate) {
      nextTick(() => {
        filterDate.value = lockedFilterDate.value;
      });
    }
    if (lockedStatusFilter.value !== null && !newStatus && oldStatus) {
      nextTick(() => {
        statusFilter.value = lockedStatusFilter.value;
      });
    }
    if (lockedProcedureFilter.value !== null && !newProcedure && oldProcedure) {
      nextTick(() => {
        procedureFilter.value = lockedProcedureFilter.value;
      });
    }
  }
});

onMounted(() => {
  // Load locked filters first (before initializing date)
  const hadLockedFilters = loadLockedFilters();
  
  // Only initialize date if no locked filters were loaded
  if (!hadLockedFilters) {
    initializeDate();
  }
  
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
.tool-input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.tool-input--search {
  min-width: 11rem;
}
.tool-select {
  min-width: 10rem;
  max-width: 14rem;
}
.tool-select :deep(.q-field__control) {
  height: 2.15rem;
  min-height: 2.15rem !important;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-panel-bg);
}
.diag-lock-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.95rem;
  padding: 0.75rem 1rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid rgba(34, 197, 94, 0.28);
  background: var(--hms-success-muted);
}
.lock-title {
  font-weight: 700;
  color: var(--hms-success);
  font-size: var(--hms-text-sm);
}
.lock-sub {
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-secondary);
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
.select-hint {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
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
  .tool-input,
  .tool-select {
    flex: 1;
    min-width: 0;
  }
}
</style>
