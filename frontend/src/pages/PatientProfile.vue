<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Patient Profile</div>

    <q-card v-if="loading && !patient">
      <q-card-section class="text-center q-pa-lg">
        <q-spinner color="primary" size="3em" />
        <div class="q-mt-md">Loading patient information...</div>
      </q-card-section>
    </q-card>

    <div v-if="patient">
      <!-- Patient Basic Information -->
      <q-card class="q-mb-md">
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h5">{{ patient.name }} {{ patient.surname || '' }}</div>
            <q-space />
            <q-btn
              color="primary"
              icon="description"
              label="Print Records"
              @click="printPatientRecords"
              class="glass-button q-mr-sm"
            />
            <q-btn
              v-if="canAccess(['Admin', 'Records'])"
              color="secondary"
              icon="edit"
              label="Edit"
              @click="editPatient"
              class="glass-button"
            />
          </div>
          <div class="row q-gutter-md">
            <div class="col-12 col-md-3">
              <div class="text-grey-7 text-caption">Card Number</div>
              <div class="text-h6 text-primary">{{ patient.card_number }}</div>
            </div>
            <div class="col-12 col-md-3">
              <div class="text-grey-7 text-caption">Gender</div>
              <div class="text-body1">{{ patient.gender }}</div>
            </div>
            <div class="col-12 col-md-3">
              <div class="text-grey-7 text-caption">Age</div>
              <div class="text-body1">{{ patient.age || 'N/A' }}</div>
            </div>
            <div class="col-12 col-md-3">
              <div class="text-grey-7 text-caption">Date of Birth</div>
              <div class="text-body1">{{ formatDate(patient.date_of_birth) }}</div>
            </div>
          </div>

          <q-separator class="q-mt-md q-mb-md" />

          <div class="row q-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-grey-7 text-caption">Insurance Status</div>
              <q-badge
                :color="patient.insured ? 'green' : 'orange'"
                :label="patient.insured ? 'Insured' : 'Cash Patient'"
                class="q-mt-xs"
              />
              <div v-if="patient.insured" class="q-mt-sm">
                <div class="text-body2">
                  <strong>Insurance ID:</strong> {{ patient.insurance_id || 'N/A' }}
                </div>
                <div class="text-body2">
                  <strong>Valid From:</strong> {{ formatDate(patient.insurance_start_date) }}
                </div>
                <div class="text-body2">
                  <strong>Valid To:</strong> {{ formatDate(patient.insurance_end_date) }}
                </div>
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-grey-7 text-caption">Contact Information</div>
              <div class="text-body2">
                <strong>Phone:</strong> {{ patient.contact || 'N/A' }}
              </div>
              <div class="text-body2 q-mt-xs">
                <strong>Address:</strong> {{ patient.address || 'N/A' }}
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Bill Summary -->
      <q-card class="q-mb-md glass-card" v-if="patient" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Bill Summary</div>
            <q-space />
            <div class="text-h5" :class="totalRemainingBalance > 0 ? 'text-negative' : 'text-positive'">
              <span v-if="totalRemainingBalance > 0" class="text-weight-bold cursor-pointer" @click="goToBilling" style="text-decoration: underline;">
                Total Balance: ₵{{ totalRemainingBalance.toFixed(2) }} (Click to Pay)
              </span>
              <span v-else-if="totalBillAmount > 0" class="text-positive text-weight-bold">
                Total Balance: ₵0.00
              </span>
              <span v-else class="text-grey-7">
                Total Balance: ₵0.00
              </span>
            </div>
          </div>
          
          <div v-if="unpaidEncounters.length > 0" class="q-mt-md">
            <div class="text-subtitle2 q-mb-sm glass-text">Unpaid Services:</div>
            <q-list class="glass-card">
              <q-item 
                v-for="encounter in unpaidEncounters" 
                :key="encounter.id"
                clickable
                @click="viewEncounterBilling(encounter.id)"
                class="q-mb-xs"
              >
                <q-item-section avatar>
                  <q-icon name="receipt" :color="encounter.remaining_balance > 0 ? 'negative' : 'positive'" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium glass-text">
                    Encounter #{{ encounter.id }} - {{ encounter.department }}
                  </q-item-label>
                  <q-item-label caption>
                    Date: {{ formatDateTime(encounter.created_at) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-h6" :class="encounter.remaining_balance > 0 ? 'text-negative' : 'text-positive'">
                    <span class="text-weight-bold">₵{{ encounter.remaining_balance.toFixed(2) }}</span>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
          <div v-else-if="loadingBills" class="text-center q-pa-md">
            <q-spinner color="primary" size="2em" />
            <div class="q-mt-sm text-grey-7">Loading bill information...</div>
          </div>
          <div v-else class="text-center q-pa-md text-grey-7">
            No unpaid services found
          </div>
        </q-card-section>
      </q-card>

      <!-- Patient Encounters -->
      <q-card>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Encounters History</div>
            <q-space />
            <q-btn
              color="primary"
              icon="add"
              label="New Encounter"
              @click="createNewEncounter"
            />
          </div>

          <q-table
            :rows="patientEncounters"
            :columns="encounterColumns"
            row-key="id"
            flat
            :loading="loadingEncounters"
            class="glass-table"
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge
                  :color="getStatusColor(props.value)"
                  :label="props.value"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-created_at="props">
              <q-td :props="props">
                {{ formatDateTime(props.value) }}
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <div class="row q-gutter-xs">
                  <!-- Doctor: Go to Consultation -->
                  <q-btn
                    v-if="canAccess(['Doctor', 'Admin'])"
                    size="sm"
                    color="primary"
                    icon="medical_services"
                    label="Consult"
                    @click="goToConsultation(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Nurse: Go to Vitals -->
                  <q-btn
                    v-if="canAccess(['Nurse', 'Admin'])"
                    size="sm"
                    color="pink"
                    icon="favorite"
                    label="Vitals"
                    @click="goToVitals(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Pharmacy: Go to Pharmacy -->
                  <q-btn
                    v-if="canAccess(['Pharmacy', 'Admin'])"
                    size="sm"
                    color="purple"
                    icon="medication"
                    label="Prescriptions"
                    @click="goToPharmacy(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Lab: Go to Lab -->
                  <q-btn
                    v-if="canAccess(['Lab', 'Admin'])"
                    size="sm"
                    color="blue"
                    icon="science"
                    label="Lab"
                    @click="goToLab(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Scan: Go to Scan -->
                  <q-btn
                    v-if="canAccess(['Scan', 'Admin'])"
                    size="sm"
                    color="teal"
                    icon="biotech"
                    label="Scan"
                    @click="goToScan(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Xray: Go to Xray -->
                  <q-btn
                    v-if="canAccess(['Xray', 'Admin'])"
                    size="sm"
                    color="cyan"
                    icon="radio_button_checked"
                    label="X-ray"
                    @click="goToXray(props.row.id)"
                    class="glass-button"
                  />
                  <!-- Billing: Go to Billing -->
                  <q-btn
                    v-if="canAccess(['Billing', 'Admin'])"
                    size="sm"
                    color="green"
                    icon="receipt"
                    label="Bill"
                    @click="viewEncounterBilling(props.row.id)"
                    class="glass-button"
                  />
                  <!-- View/Edit (Admin/Records) -->
                  <q-btn
                    v-if="canAccess(['Admin', 'Records'])"
                    size="sm"
                    color="info"
                    icon="visibility"
                    flat
                    @click="viewEncounter(props.row.id)"
                  />
                  <q-btn
                    v-if="canAccess(['Admin', 'Records'])"
                    size="sm"
                    color="secondary"
                    icon="edit"
                    flat
                    @click="editEncounter(props.row)"
                  />
                  <q-btn
                    v-if="isAdmin"
                    size="sm"
                    color="negative"
                    icon="delete"
                    flat
                    @click="deleteEncounterConfirm(props.row)"
                  />
                </div>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>

    <q-card v-if="!loading && !patient">
      <q-card-section class="text-center q-pa-lg">
        <q-icon name="person_off" size="64px" color="grey" />
        <div class="text-h6 q-mt-md">Patient not found</div>
      </q-card-section>
    </q-card>

    <!-- Edit Patient Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Patient Information</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="savePatientEdit" class="q-gutter-md">
            <div class="row q-gutter-md">
              <q-input
                v-model="editForm.name"
                filled
                label="First Name *"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Required']"
              />
              <q-input
                v-model="editForm.surname"
                filled
                label="Surname"
                class="col-12 col-md-6"
              />
            </div>

            <q-input
              v-model="editForm.other_names"
              filled
              label="Other Names"
            />

            <div class="row q-gutter-md">
              <q-select
                v-model="editForm.gender"
                filled
                :options="genderOptions"
                label="Gender *"
                class="col-12 col-md-4"
                lazy-rules
                :rules="[(val) => !!val || 'Required']"
              />
              <q-input
                v-model.number="editForm.age"
                filled
                type="number"
                label="Age"
                class="col-12 col-md-4"
              />
              <q-input
                v-model="editForm.date_of_birth"
                filled
                type="date"
                label="Date of Birth"
                class="col-12 col-md-4"
              />
            </div>

            <q-toggle
              v-model="editForm.insured"
              label="Insured (NHIS)"
            />

            <div v-if="editForm.insured" class="row q-gutter-md">
              <q-input
                v-model="editForm.insurance_id"
                filled
                label="Insurance ID / Member Number"
                class="col-12 col-md-6"
              />
              <q-input
                v-model="editForm.insurance_start_date"
                filled
                type="date"
                label="Insurance Start Date"
                class="col-12 col-md-3"
              />
              <q-input
                v-model="editForm.insurance_end_date"
                filled
                type="date"
                label="Insurance End Date"
                class="col-12 col-md-3"
              />
            </div>

            <q-input
              v-model="editForm.contact"
              filled
              label="Contact Number"
            />

            <q-input
              v-model="editForm.address"
              filled
              label="Address"
              type="textarea"
              rows="2"
            />

            <div>
              <q-btn
                label="Save Changes"
                type="submit"
                color="primary"
                :loading="saving"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEditDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Encounter Dialog -->
    <q-dialog v-model="showEditEncounterDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Encounter #{{ currentEncounter?.id }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveEncounterEdit" class="q-gutter-md">
            <q-select
              v-model="encounterEditForm.department"
              filled
              :options="departmentOptions"
              option-label="service_type"
              option-value="service_type"
              emit-value
              map-options
              label="Department/Clinic *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-select
              v-model="encounterEditForm.procedure_g_drg_code"
              filled
              :options="procedureOptions"
              option-label="service_name"
              option-value="g_drg_code"
              emit-value
              map-options
              label="Procedure (optional)"
              @update:model-value="val => { const sel = (procedureOptions||[]).find(p=>p.g_drg_code===val); encounterEditForm.procedure_name = sel?.service_name || '' }"
              :disable="!encounterEditForm.department"
            />
            <q-input
              v-model="encounterEditForm.ccc_number"
              filled
              label="CCC Number"
            />
            <q-select
              v-model="encounterEditForm.status"
              filled
              :options="statusOptions"
              label="Status"
            />
            <div>
              <q-btn
                label="Save Changes"
                type="submit"
                color="primary"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEditEncounterDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { patientsAPI, encountersAPI, billingAPI, consultationAPI, vitalsAPI } from '../services/api';
import { usePatientsStore } from '../stores/patients';
import { useEncountersStore } from '../stores/encounters';
import { useAuthStore } from '../stores/auth';
import { useQuasar } from 'quasar';
import { priceListAPI } from '../services/api';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const patientsStore = usePatientsStore();
const encountersStore = useEncountersStore();
const authStore = useAuthStore();

const patient = ref(null);
const patientEncounters = ref([]);
const loading = ref(false);
const loadingEncounters = ref(false);
const loadingBills = ref(false);
const totalBillAmount = ref(0);
const totalPaidAmount = ref(0);
const totalRemainingBalance = computed(() => Math.max(0, totalBillAmount.value - totalPaidAmount.value));
const unpaidEncounters = ref([]);
const saving = ref(false);
const showEditDialog = ref(false);
const showEditEncounterDialog = ref(false);
const currentEncounter = ref(null);
const isAdmin = computed(() => authStore.userRole === 'Admin');

const encounterEditForm = reactive({
  department: '',
  ccc_number: '',
  status: '',
  procedure_g_drg_code: '',
  procedure_name: ''
});

const genderOptions = ['M', 'F'];

const editForm = reactive({
  name: '',
  surname: '',
  other_names: '',
  gender: '',
  age: null,
  date_of_birth: '',
  insured: false,
  insurance_id: '',
  insurance_start_date: '',
  insurance_end_date: '',
  contact: '',
  address: '',
});

const encounterColumns = [
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'created_at', label: 'Date & Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'ccc_number', label: 'CCC Number', field: 'ccc_number', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const departmentOptions = ref([]);
const procedureOptions = ref([]);
const statusOptions = ['draft', 'in_consultation', 'awaiting_services', 'finalized'];

const loadServiceTypes = async () => {
  try {
    const resp = await priceListAPI.getServiceTypes();
    departmentOptions.value = resp.data || [];
  } catch (e) {
    departmentOptions.value = [];
  }
};

watch(() => encounterEditForm.department, async (newVal) => {
  if (!newVal) { procedureOptions.value = []; return; }
  try {
    const resp = await priceListAPI.getProceduresByServiceType(newVal);
    procedureOptions.value = resp.data || [];
  } catch (e) {
    procedureOptions.value = [];
  }
});

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    in_consultation: 'blue',
    awaiting_services: 'purple',
    finalized: 'green',
  };
  return colors[status] || 'grey';
};

const loadPatient = async () => {
  const cardNumber = route.params.cardNumber;
  if (!cardNumber) {
    $q.notify({
      type: 'warning',
      message: 'Card number not provided',
    });
    return;
  }

  loading.value = true;
  try {
    const response = await patientsAPI.getByCard(cardNumber);
    console.log('Profile card search response:', response);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'negative',
        message: 'Patient not found',
      });
      patient.value = null;
      return;
    }
    
    // If multiple matches, use the exact match if available, otherwise use first one
    // Try to find exact match first (case-insensitive)
    const normalizedCard = cardNumber.trim().toUpperCase();
    const exactMatch = patients.find(p => 
      p.card_number && p.card_number.toUpperCase() === normalizedCard
    );
    
    patient.value = exactMatch || patients[0];
    await loadEncounters(patient.value.id);
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Patient not found',
    });
    patient.value = null;
  } finally {
    loading.value = false;
  }
};

const loadEncounters = async (patientId) => {
  loadingEncounters.value = true;
  try {
    const response = await encountersAPI.getPatientEncounters(patientId);
    patientEncounters.value = response.data;
    
    // Load bill information for all encounters
    await loadBillSummary(patientId);
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    patientEncounters.value = [];
  } finally {
    loadingEncounters.value = false;
  }
};

const loadBillSummary = async (patientId) => {
  if (!patientId) return;
  
  loadingBills.value = true;
  try {
    // Get all encounters for this patient
    const encounters = patientEncounters.value.filter(e => !e.archived);
    
    // Load bills for each encounter
    const encounterBills = await Promise.all(
      encounters.map(async (encounter) => {
        try {
          const billsResponse = await billingAPI.getEncounterBills(encounter.id);
          const bills = billsResponse.data || [];
          
          const encounterTotal = bills.reduce((sum, bill) => sum + (bill.total_amount || 0), 0);
          const encounterPaid = bills.reduce((sum, bill) => sum + (bill.paid_amount || 0), 0);
          const encounterBalance = encounterTotal - encounterPaid;
          
          return {
            ...encounter,
            total_amount: encounterTotal,
            paid_amount: encounterPaid,
            remaining_balance: encounterBalance,
            has_bills: bills.length > 0,
          };
        } catch (error) {
          console.error(`Failed to load bills for encounter ${encounter.id}:`, error);
          return {
            ...encounter,
            total_amount: 0,
            paid_amount: 0,
            remaining_balance: 0,
            has_bills: false,
          };
        }
      })
    );
    
    // Calculate totals
    totalBillAmount.value = encounterBills.reduce((sum, e) => sum + e.total_amount, 0);
    totalPaidAmount.value = encounterBills.reduce((sum, e) => sum + e.paid_amount, 0);
    
    // Filter unpaid encounters (those with remaining balance > 0)
    unpaidEncounters.value = encounterBills.filter(e => e.remaining_balance > 0);
  } catch (error) {
    console.error('Failed to load bill summary:', error);
    totalBillAmount.value = 0;
    totalPaidAmount.value = 0;
    unpaidEncounters.value = [];
  } finally {
    loadingBills.value = false;
  }
};

const goToBilling = () => {
  if (unpaidEncounters.value.length > 0) {
    // Go to billing page with the first unpaid encounter
    router.push({
      name: 'Billing',
      params: { encounterId: unpaidEncounters.value[0].id }
    });
  }
};

const viewEncounterBilling = (encounterId) => {
  router.push({
    name: 'Billing',
    params: { encounterId: encounterId }
  });
};

// Navigation functions for different roles
const goToConsultation = (encounterId) => {
  router.push({
    name: 'Consultation',
    params: { encounterId: encounterId }
  });
};

const goToVitals = (encounterId) => {
  router.push({
    name: 'Vitals',
    query: { encounterId: encounterId }
  });
};

const goToPharmacy = (encounterId) => {
  router.push({
    name: 'Pharmacy',
    query: { encounterId: encounterId }
  });
};

const goToLab = (encounterId) => {
  router.push({
    name: 'Lab',
    query: { encounterId: encounterId }
  });
};

const goToScan = (encounterId) => {
  router.push({
    name: 'Scan',
    query: { encounterId: encounterId }
  });
};

const goToXray = (encounterId) => {
  router.push({
    name: 'Xray',
    query: { encounterId: encounterId }
  });
};

const canAccess = (roles) => authStore.canAccess(roles);

const editPatient = () => {
  if (!patient.value) return;
  
  Object.assign(editForm, {
    name: patient.value.name || '',
    surname: patient.value.surname || '',
    other_names: patient.value.other_names || '',
    gender: patient.value.gender || '',
    age: patient.value.age || null,
    date_of_birth: patient.value.date_of_birth ? patient.value.date_of_birth.split('T')[0] : '',
    insured: patient.value.insured || false,
    insurance_id: patient.value.insurance_id || '',
    insurance_start_date: patient.value.insurance_start_date 
      ? patient.value.insurance_start_date.split('T')[0] : '',
    insurance_end_date: patient.value.insurance_end_date 
      ? patient.value.insurance_end_date.split('T')[0] : '',
    contact: patient.value.contact || '',
    address: patient.value.address || '',
  });
  
  showEditDialog.value = true;
};

const savePatientEdit = async () => {
  saving.value = true;
  try {
    const patientData = { ...editForm };
    
    // Clean up empty fields
    const fieldsToClean = [
      'date_of_birth', 'insurance_start_date', 'insurance_end_date',
      'insurance_id', 'surname', 'other_names', 'contact', 'address'
    ];
    
    fieldsToClean.forEach(field => {
      if (patientData[field] === '') {
        patientData[field] = null;
      }
    });
    
    await patientsStore.updatePatient(patient.value.id, patientData);
    await loadPatient(); // Reload patient data
    showEditDialog.value = false;
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false;
  }
};

const viewEncounter = (encounterId) => {
  router.push(`/consultation/${encounterId}`);
};

const editEncounter = (encounter) => {
  showEditEncounterDialog.value = true;
  currentEncounter.value = encounter;
  encounterEditForm.department = encounter.department;
  encounterEditForm.ccc_number = encounter.ccc_number || '';
  encounterEditForm.status = encounter.status;
};

const saveEncounterEdit = async () => {
  if (!currentEncounter.value) return;
  
  const updateData = {};
  if (encounterEditForm.department !== currentEncounter.value.department) {
    updateData.department = encounterEditForm.department;
  }
  if (encounterEditForm.ccc_number !== currentEncounter.value.ccc_number) {
    updateData.ccc_number = encounterEditForm.ccc_number || null;
  }
  if (encounterEditForm.status !== currentEncounter.value.status) {
    updateData.status = encounterEditForm.status;
  }
  if (encounterEditForm.procedure_g_drg_code) {
    updateData.procedure_g_drg_code = encounterEditForm.procedure_g_drg_code;
    updateData.procedure_name = encounterEditForm.procedure_name || null;
  }
  
  if (Object.keys(updateData).length === 0) {
    $q.notify({
      type: 'info',
      message: 'No changes detected',
    });
    showEditEncounterDialog.value = false;
    return;
  }
  
  try {
    await encountersStore.updateEncounter(currentEncounter.value.id, updateData);
    showEditEncounterDialog.value = false;
    await loadEncounters(patient.value.id); // Reload encounters
  } catch (error) {
    // Error handled in store
  }
};

const deleteEncounterConfirm = (encounter) => {
  $q.dialog({
    title: 'Archive Encounter',
    message: `Are you sure you want to archive Encounter #${encounter.id}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Archive',
      color: 'negative'
    }
  }).onOk(async () => {
    try {
      await encountersStore.deleteEncounter(encounter.id);
      await loadEncounters(patient.value.id); // Reload encounters
    } catch (error) {
      // Error handled in store
    }
  });
};

const createNewEncounter = () => {
  if (patient.value) {
    patientsStore.currentPatient = patient.value;
    router.push('/patients/register');
  }
};

const printPatientRecords = async () => {
  if (!patient.value) {
    $q.notify({
      type: 'warning',
      message: 'Patient information not loaded',
    });
    return;
  }

  try {
    $q.loading.show({
      message: 'Generating patient records...',
    });

    // Collect all encounter data - only finalized encounters
    const encounterData = [];
    
    for (const encounter of patientEncounters.value.filter(e => !e.archived && e.status === 'finalized')) {
      const encounterInfo = {
        ...encounter,
        vitals: null,
        consultationNotes: null,
        diagnoses: [],
        prescriptions: [],
        investigations: [],
        labResults: [],
        scanResults: [],
        xrayResults: [],
        bills: []
      };

      // Load vitals
      try {
        const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
        encounterInfo.vitals = vitalsResponse.data || null;
      } catch (error) {
        console.error(`Failed to load vitals for encounter ${encounter.id}:`, error);
      }

      // Load consultation notes
      try {
        const notesResponse = await consultationAPI.getConsultationNotes(encounter.id);
        encounterInfo.consultationNotes = notesResponse.data || null;
      } catch (error) {
        console.error(`Failed to load consultation notes for encounter ${encounter.id}:`, error);
      }

      // Load diagnoses
      try {
        const diagnosesResponse = await consultationAPI.getDiagnoses(encounter.id);
        encounterInfo.diagnoses = diagnosesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load diagnoses for encounter ${encounter.id}:`, error);
      }

      // Load prescriptions
      try {
        const prescriptionsResponse = await consultationAPI.getPrescriptions(encounter.id);
        encounterInfo.prescriptions = prescriptionsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load prescriptions for encounter ${encounter.id}:`, error);
      }

      // Load investigations
      try {
        const investigationsResponse = await consultationAPI.getInvestigations(encounter.id);
        encounterInfo.investigations = investigationsResponse.data || [];
        
        // Load results for each investigation
        for (const investigation of encounterInfo.investigations) {
          if (investigation.investigation_type === 'Lab') {
            try {
              const labResultResponse = await consultationAPI.getLabResult(investigation.id);
              encounterInfo.labResults.push({
                investigation_id: investigation.id,
                result: labResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load lab result for investigation ${investigation.id}:`, error);
            }
          } else if (investigation.investigation_type === 'Scan') {
            try {
              const scanResultResponse = await consultationAPI.getScanResult(investigation.id);
              encounterInfo.scanResults.push({
                investigation_id: investigation.id,
                result: scanResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load scan result for investigation ${investigation.id}:`, error);
            }
          } else if (investigation.investigation_type === 'Xray') {
            try {
              const xrayResultResponse = await consultationAPI.getXrayResult(investigation.id);
              encounterInfo.xrayResults.push({
                investigation_id: investigation.id,
                result: xrayResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load xray result for investigation ${investigation.id}:`, error);
            }
          }
        }
      } catch (error) {
        console.error(`Failed to load investigations for encounter ${encounter.id}:`, error);
      }

      // Load bills
      try {
        const billsResponse = await billingAPI.getEncounterBills(encounter.id);
        encounterInfo.bills = billsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load bills for encounter ${encounter.id}:`, error);
      }

      encounterData.push(encounterInfo);
    }

    // Sort encounters by date (newest first)
    encounterData.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    // Generate HTML
    const html = buildPatientRecordsHtml(patient.value, encounterData);
    
    // Open in new window and print
    const w = window.open('', '_blank', 'width=1200,height=800');
    if (!w) {
      $q.loading.hide();
      $q.notify({
        type: 'negative',
        message: 'Please allow popups to print records',
      });
      return;
    }
    
    w.document.open();
    w.document.write(html);
    w.document.close();
    
    $q.loading.hide();
    
    setTimeout(() => {
      try {
        w.focus();
        w.print();
      } catch (e) {
        console.error('Print error:', e);
      }
    }, 500);
  } catch (error) {
    $q.loading.hide();
    console.error('Failed to generate patient records:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to generate patient records',
    });
  }
};

const buildPatientRecordsHtml = (patient, encounterData) => {
  const now = new Date();

  // Build patient biostats section
  const biostatsHtml = `
    <div class="section">
      <h3 class="section-title">PATIENT BIOSTATISTICS</h3>
      <div class="two-column">
        <div><strong>Card Number:</strong> ${patient.card_number || 'N/A'}</div>
        <div><strong>Name:</strong> ${patient.name || ''} ${patient.surname || ''} ${patient.other_names || ''}</div>
        <div><strong>Gender:</strong> ${patient.gender || 'N/A'}</div>
        <div><strong>Age:</strong> ${patient.age || 'N/A'}</div>
        <div><strong>Date of Birth:</strong> ${formatDate(patient.date_of_birth)}</div>
        <div><strong>Contact:</strong> ${patient.contact || 'N/A'}</div>
        <div><strong>Address:</strong> ${patient.address || 'N/A'}</div>
        <div><strong>Insurance Status:</strong> ${patient.insured ? 'Insured' : 'Cash Patient'}</div>
        ${patient.insured ? `
          <div><strong>Insurance ID:</strong> ${patient.insurance_id || 'N/A'}</div>
          <div><strong>Insurance Start:</strong> ${formatDate(patient.insurance_start_date)}</div>
          <div><strong>Insurance End:</strong> ${formatDate(patient.insurance_end_date)}</div>
        ` : ''}
      </div>
    </div>
  `;

  // Build encounters HTML
  let encountersHtml = '';
  
  if (encounterData.length === 0) {
    encountersHtml = '<div class="section"><p class="no-data">No encounters found</p></div>';
  } else {
    encounterData.forEach((encounter, idx) => {
      // Build vitals HTML
      let vitalsHtml = '<p class="no-data">No vitals recorded</p>';
      if (encounter.vitals) {
        const v = encounter.vitals;
        vitalsHtml = `
          <div class="two-column">
            ${v.weight ? `<div><strong>Weight:</strong> ${v.weight} kg</div>` : ''}
            ${v.height ? `<div><strong>Height:</strong> ${v.height} cm</div>` : ''}
            ${v.bp_systolic || v.bp_diastolic ? `<div><strong>Blood Pressure:</strong> ${v.bp_systolic || ''}/${v.bp_diastolic || ''} mmHg</div>` : ''}
            ${v.temperature ? `<div><strong>Temperature:</strong> ${v.temperature} °C</div>` : ''}
            ${v.pulse ? `<div><strong>Pulse:</strong> ${v.pulse} bpm</div>` : ''}
            ${v.respiratory_rate ? `<div><strong>Respiratory Rate:</strong> ${v.respiratory_rate} /min</div>` : ''}
            ${v.spo2 ? `<div><strong>SpO2:</strong> ${v.spo2}%</div>` : ''}
            ${v.bmi ? `<div><strong>BMI:</strong> ${v.bmi}</div>` : ''}
          </div>
        `;
      }

      // Build presenting complaints HTML
      let presentingComplaintsHtml = '<p class="no-data">No presenting complaints recorded</p>';
      if (encounter.consultationNotes?.presenting_complaints) {
        presentingComplaintsHtml = `<div style="white-space: pre-wrap;">${encounter.consultationNotes.presenting_complaints}</div>`;
      }
      
      // Build doctor notes HTML
      let doctorNotesHtml = '<p class="no-data">No doctor notes recorded</p>';
      if (encounter.consultationNotes?.doctor_notes) {
        doctorNotesHtml = `<div style="white-space: pre-wrap;">${encounter.consultationNotes.doctor_notes}</div>`;
      }
      
      // Build follow up date HTML
      let followUpDateHtml = '<p class="no-data">No follow-up date set</p>';
      if (encounter.consultationNotes?.follow_up_date) {
        followUpDateHtml = `<div><strong>Follow Up Date:</strong> ${formatDate(encounter.consultationNotes.follow_up_date)}</div>`;
      }
      
      // Build consultation outcome HTML
      let consultationOutcomeHtml = '<p class="no-data">No consultation outcome recorded</p>';
      if (encounter.consultationNotes?.outcome) {
        const outcomeLabels = {
          'discharged': 'Discharged',
          'referred': 'Referred',
          'recommended_for_admission': 'Recommended for Admission'
        };
        const outcomeLabel = outcomeLabels[encounter.consultationNotes.outcome] || encounter.consultationNotes.outcome;
        consultationOutcomeHtml = `<div><strong>Consultation Outcome:</strong> ${outcomeLabel}</div>`;
      }

      // Build diagnoses HTML
      let diagnosesHtml = '<p class="no-data">No diagnoses recorded</p>';
      if (encounter.diagnoses.length > 0) {
        diagnosesHtml = '<ul>';
        encounter.diagnoses.forEach(diag => {
          diagnosesHtml += `<li><strong>${diag.diagnosis || 'N/A'}</strong>${diag.icd10_code ? ` (ICD-10: ${diag.icd10_code})` : ''}</li>`;
        });
        diagnosesHtml += '</ul>';
      }

      // Build prescriptions HTML
      let prescriptionsHtml = '<p class="no-data">No prescriptions</p>';
      if (encounter.prescriptions.length > 0) {
        prescriptionsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Medication</th><th>Dose</th><th>Frequency</th><th>Duration</th><th>Quantity</th><th>Status</th></tr></thead><tbody>';
        encounter.prescriptions.forEach((pres, pidx) => {
          prescriptionsHtml += `
            <tr>
              <td>${pidx + 1}</td>
              <td>${pres.medicine_name || 'N/A'}</td>
              <td>${pres.dose || 'N/A'}</td>
              <td>${pres.frequency || 'N/A'}</td>
              <td>${pres.duration || 'N/A'}</td>
              <td>${pres.quantity || 0}</td>
              <td>${pres.is_dispensed ? 'Dispensed' : pres.is_confirmed ? 'Confirmed' : 'Pending'}</td>
            </tr>
          `;
        });
        prescriptionsHtml += '</tbody></table>';
      }

      // Build investigations HTML
      let investigationsHtml = '<p class="no-data">No investigations</p>';
      if (encounter.investigations.length > 0) {
        investigationsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Type</th><th>Investigation</th><th>Status</th></tr></thead><tbody>';
        encounter.investigations.forEach((inv, invidx) => {
          investigationsHtml += `
            <tr>
              <td>${invidx + 1}</td>
              <td>${inv.investigation_type || 'N/A'}</td>
              <td>${inv.procedure_name || inv.investigation_name || 'N/A'}</td>
              <td>${inv.is_confirmed ? 'Confirmed' : 'Pending'}</td>
            </tr>
          `;
        });
        investigationsHtml += '</tbody></table>';

        // Add results if available
        if (encounter.labResults.length > 0 || encounter.scanResults.length > 0 || encounter.xrayResults.length > 0) {
          investigationsHtml += '<h4 class="subsection-title">Investigation Results</h4>';
          
          encounter.labResults.forEach(lab => {
            investigationsHtml += `<div class="result-section"><strong>Lab Result:</strong><pre>${lab.result?.result || 'N/A'}</pre></div>`;
          });
          
          encounter.scanResults.forEach(scan => {
            investigationsHtml += `<div class="result-section"><strong>Scan Result:</strong><pre>${scan.result?.result || 'N/A'}</pre></div>`;
          });
          
          encounter.xrayResults.forEach(xray => {
            investigationsHtml += `<div class="result-section"><strong>X-ray Result:</strong><pre>${xray.result?.result || 'N/A'}</pre></div>`;
          });
        }
      }

      // Build bills HTML
      let billsHtml = '<p class="no-data">No bills</p>';
      if (encounter.bills.length > 0) {
        const encounterTotal = encounter.bills.reduce((sum, b) => sum + (b.total_amount || 0), 0);
        const encounterPaid = encounter.bills.reduce((sum, b) => sum + (b.paid_amount || 0), 0);
        const encounterBalance = encounterTotal - encounterPaid;
        
        billsHtml = `
          <table class="data-table"><thead><tr><th>Bill ID</th><th>Total Amount</th><th>Paid Amount</th><th>Balance</th></tr></thead><tbody>
          ${encounter.bills.map(bill => `
            <tr>
              <td>${bill.id}</td>
              <td>₵${(bill.total_amount || 0).toFixed(2)}</td>
              <td>₵${(bill.paid_amount || 0).toFixed(2)}</td>
              <td>₵${((bill.total_amount || 0) - (bill.paid_amount || 0)).toFixed(2)}</td>
            </tr>
          `).join('')}
          </tbody></table>
          <div class="bill-summary">
            <strong>Encounter Total:</strong> ₵${encounterTotal.toFixed(2)} | 
            <strong>Paid:</strong> ₵${encounterPaid.toFixed(2)} | 
            <strong>Balance:</strong> ₵${encounterBalance.toFixed(2)}
          </div>
        `;
      }

      encountersHtml += `
        <div class="encounter-section">
          <h3 class="encounter-title">ENCOUNTER #${encounter.id} - ${encounter.department || 'N/A'}</h3>
          <div class="encounter-meta">
            <strong>Date:</strong> ${formatDateTime(encounter.created_at)} | 
            <strong>Status:</strong> ${encounter.status || 'N/A'} | 
            ${encounter.ccc_number ? `<strong>CCC Number:</strong> ${encounter.ccc_number}` : ''}
          </div>
          
          <h4 class="subsection-title">Vitals</h4>
          ${vitalsHtml}
          
          <h4 class="subsection-title">Presenting Complaints</h4>
          ${presentingComplaintsHtml}
          
          <h4 class="subsection-title">Diagnoses</h4>
          ${diagnosesHtml}
          
          <h4 class="subsection-title">Prescriptions</h4>
          ${prescriptionsHtml}
          
          <h4 class="subsection-title">Investigations</h4>
          ${investigationsHtml}
          
          <h4 class="subsection-title">Doctor Note</h4>
          ${doctorNotesHtml}
          
          <h4 class="subsection-title">Follow Up Date</h4>
          ${followUpDateHtml}
          
          <h4 class="subsection-title">Consultation Outcome</h4>
          ${consultationOutcomeHtml}
          
          <h4 class="subsection-title">Billing</h4>
          ${billsHtml}
        </div>
      `;
    });
  }

  return `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Patient Electronic Records - ${patient.card_number || patient.name}</title>
    <style>
      @page { size: A4; margin: 20mm; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Arial', sans-serif; font-size: 11px; line-height: 1.6; color: #333; }
      
      .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
      .logo-container { display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 10px; }
      .logo { max-width: 80px; max-height: 80px; object-fit: contain; }
      .hospital-name { font-size: 18px; font-weight: bold; margin: 10px 0; }
      .document-title { font-size: 16px; font-weight: bold; text-transform: uppercase; }
      
      .section { margin-bottom: 25px; page-break-inside: avoid; }
      .section-title { font-size: 14px; font-weight: bold; text-transform: uppercase; border-bottom: 2px solid #333; padding-bottom: 5px; margin-bottom: 10px; }
      .subsection-title { font-size: 12px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; color: #555; }
      
      .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      
      .encounter-section { margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; page-break-inside: avoid; }
      .encounter-title { font-size: 14px; font-weight: bold; color: #000; margin-bottom: 8px; }
      .encounter-meta { font-size: 10px; color: #666; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px dashed #ccc; }
      
      table.data-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10px; }
      table.data-table th, table.data-table td { border: 1px solid #ddd; padding: 6px; text-align: left; }
      table.data-table th { background-color: #f5f5f5; font-weight: bold; }
      
      ul { margin-left: 20px; }
      li { margin-bottom: 5px; }
      
      .no-data { color: #999; font-style: italic; }
      
      .result-section { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #333; }
      .result-section pre { white-space: pre-wrap; margin-top: 5px; }
      
      .bill-summary { margin-top: 10px; padding: 10px; background-color: #f0f0f0; font-weight: bold; }
      
      @media print {
        .encounter-section { page-break-inside: avoid; }
        .section { page-break-inside: avoid; }
      }
    </style>
  </head>
  <body>
    <div class="header">
      <div class="logo-container">
        <img src="/logos/ministry-of-health-logo.png" alt="Ministry of Health" class="logo" onerror="this.style.display='none'">
        <img src="/logos/ghana-health-service-logo.png" alt="Ghana Health Service" class="logo" onerror="this.style.display='none'">
      </div>
      <div class="hospital-name">GHANA HEALTH SERVICE</div>
      <div class="hospital-name">ASESEWA GOVERNMENT HOSPITAL</div>
      <div class="document-title">PATIENT ELECTRONIC RECORDS</div>
      <div style="margin-top: 10px; font-size: 10px;">Generated: ${now.toLocaleString('en-GB')}</div>
    </div>

    ${biostatsHtml}
    
    <div class="section">
      <h3 class="section-title">PATIENT ENCOUNTERS</h3>
      ${encountersHtml}
    </div>
    
    <div style="margin-top: 40px; text-align: center; font-size: 10px; color: #666; border-top: 1px solid #ddd; padding-top: 15px;">
      <p>This document contains the complete electronic health records for the patient.</p>
      <p>Generated on ${now.toLocaleString('en-GB')}</p>
      <p>Generated by ${authStore.user?.name || 'System'}</p>
      <p>Made with ❤️ by IT Unit @ ASESEWA GOVERNMENT HOSPITAL</p>
    </div>

   
  </body>
  </html>`;
};

onMounted(() => {
  loadPatient();
  loadServiceTypes();
});
</script>

