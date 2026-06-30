<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Generate Claim</div>

    <!-- Back Button -->
    <q-btn
      flat
      icon="arrow_back"
      label="Back to Claims"
      @click="$router.push('/claims')"
      class="q-mb-md"
    />

    <!-- Loading State -->
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner color="primary" size="3em" />
      <div class="q-mt-md">Loading encounter data...</div>
    </div>

    <!-- Error State -->
    <q-banner
      v-if="error"
      class="bg-negative text-white q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="error" />
      </template>
      {{ error }}
    </q-banner>

    <!-- Encounter Details -->
    <q-card v-if="encounter && !loading" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Encounter Details</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Encounter ID</div>
            <div class="text-body1">{{ encounter.id }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1">{{ encounter.patient_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Card Number</div>
            <div class="text-body1">{{ encounter.patient_card_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Member Number</div>
            <div class="text-body1">
              <span v-if="encounter.patient_insurance_id">{{ encounter.patient_insurance_id }}</span>
              <span v-else class="text-negative">Not Set</span>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">CCC Number</div>
            <div class="text-body1">{{ encounter.ccc_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Department</div>
            <div class="text-body1">{{ encounter.department || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Finalized At</div>
            <div class="text-body1">{{ formatDate(encounter.finalized_at) }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Physician Code (Finalized By)</div>
            <div class="text-body1">{{ encounter.finalized_by_username || 'N/A' }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Incomplete Investigations Alert -->
    <q-banner
      v-if="incompleteInvestigations.length > 0"
      class="bg-warning text-dark q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="warning" color="dark" />
      </template>
      <strong>Some Services Have Not Been Finalized</strong>
      <div class="text-caption q-mt-xs">
        The following investigations are not yet completed. They will be included in the claim, but you may want to finalize them first:
      </div>
      <q-list dense class="q-mt-sm">
        <q-item
          v-for="inv in incompleteInvestigations"
          :key="inv.id"
          dense
        >
          <q-item-section>
            <q-item-label>{{ inv.procedure_name || inv.gdrg_code }}</q-item-label>
            <q-item-label caption>Status: {{ inv.status }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-banner>

    <!-- Undispensed Medicines Alert -->
    <q-banner
      v-if="undispensedMedicines.length > 0"
      class="bg-warning text-dark q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="medication" color="dark" />
      </template>
      <strong>Some Medicines Have Not Been Dispensed</strong>
      <div class="text-caption q-mt-xs">
        The following medicines are not yet dispensed. Dispensed medicines are always included in the claim.
        When you generate, you can choose to include undispensed medicines as well.
      </div>
      <q-list dense class="q-mt-sm">
        <q-item
          v-for="med in undispensedMedicines"
          :key="med.prescriptionKey"
          dense
        >
          <q-item-section>
            <q-item-label>{{ med.medicine_name || med.medicine_code }}</q-item-label>
            <q-item-label caption>Status: {{ med.displayStatus }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-banner>

    <!-- Medicines Section -->
    <q-card v-if="encounter && !loading" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Medicines (Prescriptions)</div>
        <q-table
          v-if="medicinesDisplay.length > 0"
          :rows="medicinesDisplay"
          :columns="medicineColumns"
          row-key="prescriptionKey"
          flat
          :loading="loadingMedicines"
        >
          <template v-slot:body-cell-displayStatus="props">
            <q-td :props="props">
              <q-badge
                :color="getMedicineStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-7 q-pa-md">
          No medicines prescribed for this encounter
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigations Section -->
    <q-card v-if="encounter && !loading" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Investigations</div>
        <q-table
          v-if="investigations.length > 0"
          :rows="investigations"
          :columns="investigationColumns"
          row-key="id"
          flat
          :loading="loadingInvestigations"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getInvestigationStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="canFinalizeInvestigation(props.row)"
                size="sm"
                color="primary"
                label="Finalize"
                @click="openResultEntry(props.row)"
                class="q-mr-xs"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-7 q-pa-md">
          No investigations for this encounter
        </div>
      </q-card-section>
    </q-card>

    <!-- Diagnoses Section -->
    <q-card v-if="encounter && !loading && diagnoses.length > 0" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          Diagnoses 
          <span v-if="isIPD" class="text-caption text-grey-7">
            (OPD + IPD Clinical Reviews)
          </span>
        </div>
        <q-table
          :rows="diagnoses"
          :columns="diagnosisColumns"
          row-key="id"
          flat
        >
          <template v-slot:body-cell-is_chief="props">
            <q-td :props="props">
              <q-badge v-if="props.value" color="primary" label="Chief" />
            </q-td>
          </template>
          <template v-slot:body-cell-source="props">
            <q-td :props="props">
              <q-badge 
                v-if="props.value"
                :color="props.value === 'opd' ? 'blue' : 'green'" 
                :label="props.value === 'opd' ? 'OPD' : 'IPD'"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Surgeries Section - Show for both IPD and OPD (OPD will always show "No surgeries") -->
    <q-card v-if="encounter && !loading" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          Surgeries
          <q-badge v-if="surgeries.length > 0" color="primary" :label="surgeries.length" class="q-ml-sm" />
        </div>
        <q-table
          v-if="surgeries.length > 0"
          :rows="surgeries"
          :columns="surgeryColumns"
          row-key="id"
          flat
        >
          <template v-slot:body-cell-is_completed="props">
            <q-td :props="props">
              <q-badge
                :color="props.value ? 'green' : 'orange'"
                :label="props.value ? 'Completed' : 'Pending'"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-7 q-pa-md">
          <q-icon name="info" size="md" class="q-mb-sm" />
          <div v-if="isIPD">No surgeries recorded for this admission</div>
          <div v-else>
            <strong>OPD Claims:</strong> No surgeries/procedures recorded.
            <br />If this OPD encounter has surgeries (e.g., catheter changing), they will appear here and in the claim edit form.
            <br />Otherwise, only diagnoses, investigations, and medications will appear in the claim edit form.
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Claim Form -->
    <q-card v-if="encounter && !loading" class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          {{ isRegenerating ? 'Regenerate Claim' : 'Claim Information' }}
        </div>
        <q-banner
          v-if="isRegenerating"
          class="bg-info text-white q-mb-md"
          rounded
        >
          <template v-slot:avatar>
            <q-icon name="info" />
          </template>
          Regenerating claim will update the claim with the latest investigations and medicines from this encounter.
        </q-banner>
        <q-form @submit="generateClaim" class="q-gutter-md">
          <q-input
            v-model="claimForm.physician_id"
            filled
            label="Physician ID (SNO Code) *"
            hint="Enter physician SNO code (e.g., SNO-001)"
            lazy-rules
            :rules="[(val) => !!val || 'Required']"
          >
            <template v-if="isIPD && wardAdmission?.doctor_name" v-slot:append>
              <q-tooltip>
                Doctor under care: {{ wardAdmission.doctor_name }}
              </q-tooltip>
              <q-icon name="info" color="primary" />
            </template>
          </q-input>
          <q-input
            v-model="claimForm.physician_name"
            filled
            label="Physician Name"
            hint="Enter physician full name"
          />
          <q-select
            v-model="claimForm.type_of_service"
            :options="['OPD', 'Inpatient']"
            filled
            label="Type of Service"
          />
          <q-select
            v-model="claimForm.type_of_attendance"
            :options="['EAE', 'Referral', 'Antenatal', 'Postnatal']"
            filled
            label="Type of Attendance"
          />
          <q-input
            v-model="claimForm.specialty_attended"
            filled
            label="Specialty Attended"
          />
          <div class="row q-gutter-md">
            <q-btn
              type="submit"
              color="primary"
              :label="isRegenerating ? 'Regenerate Claim' : 'Generate Claim'"
              :loading="generating"
              class="col-12 col-md-4"
            />
            <q-btn
              flat
              label="Cancel"
              @click="$router.push('/claims')"
              class="col-12 col-md-4"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Undispensed medicine selection dialog -->
    <q-dialog v-model="medicineSelectDialogOpen" persistent>
      <q-card style="min-width: 420px; max-width: 640px">
        <q-card-section>
          <div class="text-h6">Select Medicines to Include</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Choose which undispensed medicines to add to the claim. Dispensed medicines are already included.
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-item dense class="q-px-none">
            <q-item-section side>
              <q-checkbox v-model="selectAllUndispensed" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">Select all</q-item-label>
            </q-item-section>
          </q-item>
          <q-separator class="q-mb-sm" />
          <q-list dense>
            <q-item
              v-for="med in undispensedMedicines"
              :key="med.prescriptionKey"
              tag="label"
              dense
              class="q-px-none"
            >
              <q-item-section side>
                <q-checkbox
                  :model-value="selectedUndispensedKeys.includes(med.prescriptionKey)"
                  @update:model-value="(val) => toggleUndispensedKey(med.prescriptionKey, val)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ med.medicine_name || med.medicine_code }}</q-item-label>
                <q-item-label caption>
                  {{ med.medicine_code }} · Qty {{ med.quantity }} · {{ med.displayStatus }}
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="cancelMedicineSelection" />
          <q-btn
            color="primary"
            :label="selectedUndispensedKeys.length > 0 ? 'Include selected' : 'Continue without undispensed'"
            @click="confirmMedicineSelection"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { encountersAPI, consultationAPI, claimsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();

const loading = ref(false);
const loadingMedicines = ref(false);
const loadingInvestigations = ref(false);
const generating = ref(false);
const error = ref(null);
const isRegenerating = ref(false);
const existingClaimId = ref(null);
const wardAdmissionId = ref(null);
const isIPD = ref(false);

const encounter = ref(null);
const wardAdmission = ref(null);
const medicines = ref([]);
const investigations = ref([]);
const diagnoses = ref([]);
const surgeries = ref([]);
const medicineSelectDialogOpen = ref(false);
const selectedUndispensedKeys = ref([]);
let medicineSelectDeferred = null;

const getMedicineStatus = (med) => {
  if (med.is_dispensed) return 'Dispensed';
  if (med.is_confirmed) return 'Confirmed';
  return 'Pending';
};

const medicinesDisplay = computed(() =>
  medicines.value.map((med) => ({
    ...med,
    displayStatus: getMedicineStatus(med),
    prescriptionKey: med.source === 'ipd' ? `ipd-${med.id}` : `opd-${med.id}`,
  }))
);

const undispensedMedicines = computed(() =>
  medicinesDisplay.value.filter((med) => !med.is_dispensed && med.medicine_code)
);

const selectAllUndispensed = computed({
  get() {
    const undispensed = undispensedMedicines.value;
    return (
      undispensed.length > 0 &&
      undispensed.every((med) => selectedUndispensedKeys.value.includes(med.prescriptionKey))
    );
  },
  set(val) {
    selectedUndispensedKeys.value = val
      ? undispensedMedicines.value.map((med) => med.prescriptionKey)
      : [];
  },
});

// Check if this is an IPD claim from route query
if (route.query.ward_admission_id) {
  wardAdmissionId.value = parseInt(route.query.ward_admission_id);
  isIPD.value = route.query.type === 'ipd' || !!wardAdmissionId.value; // If ward_admission_id exists, it's IPD
}

const claimForm = reactive({
  physician_id: '',
  physician_name: '',
  type_of_service: isIPD.value ? 'IPD' : 'OPD',
  type_of_attendance: 'EAE',
  specialty_attended: 'OPDC',
});

const incompleteInvestigations = computed(() => {
  return investigations.value.filter(
    inv => inv.status !== 'completed' && inv.status !== 'cancelled'
  );
});

const medicineColumns = [
  { name: 'medicine_code', label: 'Code', field: 'medicine_code', align: 'left' },
  { name: 'medicine_name', label: 'Medicine Name', field: 'medicine_name', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'unit', label: 'Unit', field: 'unit', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'left' },
  { name: 'displayStatus', label: 'Status', field: 'displayStatus', align: 'center' },
];

const investigationColumns = [
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'procedure_name', label: 'Procedure Name', field: 'procedure_name', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'service_date', label: 'Service Date', field: 'service_date', align: 'left', format: (val) => val ? new Date(val).toLocaleString() : '-' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const diagnosisColumns = [
  { name: 'diagnosis', label: 'Diagnosis', field: 'diagnosis', align: 'left' },
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'is_chief', label: 'Chief', field: 'is_chief', align: 'center' },
  { name: 'source', label: 'Source', field: 'source', align: 'center' },
  { name: 'created_at', label: 'Date', field: 'created_at', align: 'left', format: (val) => val ? new Date(val).toLocaleDateString() : '-' },
];

const surgeryColumns = [
  { name: 'surgery_name', label: 'Surgery Name', field: 'surgery_name', align: 'left' },
  { name: 'g_drg_code', label: 'G-DRG Code', field: 'g_drg_code', align: 'left' },
  { name: 'surgery_type', label: 'Type', field: 'surgery_type', align: 'left' },
  { name: 'surgeon_name', label: 'Surgeon', field: 'surgeon_name', align: 'left' },
  { name: 'surgery_date', label: 'Date', field: 'surgery_date', align: 'left', format: (val) => val ? new Date(val).toLocaleDateString() : '-' },
  { name: 'is_completed', label: 'Status', field: 'is_completed', align: 'center' },
];

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
};

const getMedicineStatusColor = (status) => {
  const colors = {
    Pending: 'orange',
    Confirmed: 'blue',
    Dispensed: 'green',
  };
  return colors[status] || 'grey';
};

const getInvestigationStatusColor = (status) => {
  const colors = {
    'requested': 'orange',
    'confirmed': 'blue',
    'completed': 'green',
    'cancelled': 'red',
  };
  return colors[status] || 'grey';
};

const canFinalizeInvestigation = (investigation) => {
  // Only show button for investigations that are not completed or cancelled
  if (investigation.status === 'completed' || investigation.status === 'cancelled') {
    return false;
  }
  
  // Check if user has permission based on investigation type
  const userRoles = authStore.allUserRoles || [];
  const investigationType = investigation.investigation_type?.toLowerCase();
  
  // Admin can finalize all investigations
  if (userRoles.includes('Admin')) {
    return true;
  }
  
  // Check role-specific permissions
  if (investigationType === 'lab') {
    return userRoles.includes('Lab Head');
  } else if (investigationType === 'scan') {
    return userRoles.includes('Scan Head');
  } else if (investigationType === 'xray') {
    return userRoles.includes('Xray Head');
  }
  
  return false;
};

const openResultEntry = (investigation) => {
  const investigationType = investigation.investigation_type?.toLowerCase();
  const investigationId = investigation.id;
  
  if (!investigationId) {
    $q.notify({
      type: 'negative',
      message: 'Invalid investigation ID',
    });
    return;
  }
  
  // Determine the route based on investigation type
  let routePath = '';
  if (investigationType === 'lab') {
    routePath = `/lab/result/${investigationId}`;
  } else if (investigationType === 'scan') {
    routePath = `/scan/result/${investigationId}`;
  } else if (investigationType === 'xray') {
    routePath = `/xray/result/${investigationId}`;
  } else {
    $q.notify({
      type: 'negative',
      message: 'Unknown investigation type',
    });
    return;
  }
  
  // Open in new tab
  const route = router.resolve(routePath);
  window.open(route.href, '_blank');
};

const loadEncounter = async () => {
  const encounterId = route.params.encounterId;
  if (!encounterId) {
    error.value = 'No encounter ID provided';
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const response = await encountersAPI.get(encounterId);
    encounter.value = response.data;
    
    // For IPD claims, load ward admission data
    if (isIPD.value && wardAdmissionId.value) {
      await loadWardAdmission(wardAdmissionId.value);
    } else {
      // Auto-fill physician_id with finalized_by username if available (for OPD)
      if (response.data.finalized_by_username) {
        claimForm.physician_id = response.data.finalized_by_username;
      }
      // Auto-fill physician_name with finalized_by name if available (for OPD)
      if (response.data.finalized_by_name) {
        claimForm.physician_name = response.data.finalized_by_name;
      }
    }
    
    // Load medicines and investigations in parallel
    await Promise.all([
      loadMedicines(encounterId),
      loadInvestigations(encounterId),
    ]);
    
    // For IPD, load diagnoses and surgeries from ward admission
    if (isIPD.value && wardAdmissionId.value) {
      console.log('Loading IPD data - diagnoses and surgeries for ward admission:', wardAdmissionId.value);
      await Promise.all([
        loadDiagnoses(wardAdmissionId.value),
        loadSurgeries(wardAdmissionId.value),
      ]);
      console.log('IPD data loaded - isIPD:', isIPD.value, 'surgeries count:', surgeries.value.length);
    } else {
      // For OPD, load diagnoses from encounter and check for surgeries
      await loadOPDDiagnoses(encounterId);
      await loadSurgeriesForEncounter(encounterId);
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load encounter';
    $q.notify({
      type: 'negative',
      message: error.value,
    });
  } finally {
    loading.value = false;
  }
};

const loadWardAdmission = async (wardAdmissionId) => {
  try {
    const response = await consultationAPI.getWardAdmission(wardAdmissionId);
    wardAdmission.value = response.data;
    
    // Pre-fill physician_id with doctor's username (user can change to SNO code)
    if (wardAdmission.value?.doctor_username) {
      claimForm.physician_id = wardAdmission.value.doctor_username;
    }
    // Pre-fill physician_name with doctor's name if available
    if (wardAdmission.value?.doctor_name) {
      claimForm.physician_name = wardAdmission.value.doctor_name;
    }
  } catch (err) {
    console.error('Failed to load ward admission:', err);
    $q.notify({
      type: 'warning',
      message: 'Failed to load ward admission details',
    });
  }
};

const loadDiagnoses = async (wardAdmissionId) => {
  try {
    const response = await consultationAPI.getAllInpatientDiagnoses(wardAdmissionId);
    diagnoses.value = response.data || [];
  } catch (err) {
    console.error('Failed to load diagnoses:', err);
    diagnoses.value = [];
  }
};

const loadOPDDiagnoses = async (encounterId) => {
  try {
    const response = await consultationAPI.getDiagnoses(encounterId);
    diagnoses.value = response.data || [];
  } catch (err) {
    console.error('Failed to load OPD diagnoses:', err);
    diagnoses.value = [];
  }
};

const loadSurgeries = async (wardAdmissionId) => {
  try {
    const response = await consultationAPI.getInpatientSurgeries(wardAdmissionId);
    surgeries.value = response.data || [];
    console.log('Loaded surgeries for IPD ward admission:', wardAdmissionId, 'count:', surgeries.value.length);
  } catch (err) {
    console.error('Failed to load surgeries:', err);
    surgeries.value = [];
  }
};

const loadSurgeriesForEncounter = async (encounterId) => {
  try {
    // For OPD, try to find surgeries linked to this encounter
    // First check if there's a ward admission for this encounter
    const encounterResponse = await encountersAPI.get(encounterId);
    const encounterData = encounterResponse.data;
    
    // Check if encounter has surgeries via ward admission
    // If it's OPD but has surgeries, they might be linked through a ward admission
    if (encounterData) {
      // Try to find ward admission for this encounter
      try {
        const wardAdmissionsResponse = await consultationAPI.getWardAdmissionsByPatientCard(
          encounterData.patient_card_number || '', 
          true // Include discharged
        );
        const wardAdmissions = wardAdmissionsResponse.data || [];
        const matchingAdmission = wardAdmissions.find(wa => wa.encounter_id === encounterId);
        
        if (matchingAdmission) {
          // Load surgeries from ward admission
          const response = await consultationAPI.getInpatientSurgeries(matchingAdmission.id);
          surgeries.value = response.data || [];
          console.log('Loaded surgeries for OPD encounter via ward admission:', surgeries.value.length);
        } else {
          // No ward admission, so no surgeries for OPD
          surgeries.value = [];
          console.log('No ward admission found for OPD encounter, no surgeries');
        }
      } catch (err) {
        console.warn('Could not check for ward admission:', err);
        surgeries.value = [];
      }
    }
  } catch (err) {
    console.error('Failed to load surgeries for encounter:', err);
    surgeries.value = [];
  }
};

const loadMedicines = async (encounterId) => {
  loadingMedicines.value = true;
  try {
    const response = await consultationAPI.getPrescriptions(encounterId);
    const opdMeds = (response.data || []).map((med) => ({ ...med, source: 'opd' }));

    if (isIPD.value && wardAdmissionId.value) {
      try {
        const ipdResponse = await consultationAPI.getInpatientPrescriptionsByWardAdmission(
          wardAdmissionId.value
        );
        const ipdMeds = (ipdResponse.data || []).map((med) => ({ ...med, source: 'ipd' }));
        medicines.value = [...opdMeds, ...ipdMeds];
      } catch (ipdErr) {
        console.error('Failed to load IPD medicines:', ipdErr);
        medicines.value = opdMeds;
      }
    } else {
      medicines.value = opdMeds;
    }
  } catch (err) {
    console.error('Failed to load medicines:', err);
    medicines.value = [];
  } finally {
    loadingMedicines.value = false;
  }
};

const loadInvestigations = async (encounterId) => {
  loadingInvestigations.value = true;
  try {
    // Load OPD investigations
    const response = await consultationAPI.getInvestigations(encounterId);
    const opdInvestigations = response.data || [];
    
    // For IPD claims, also load IPD investigations
    if (isIPD.value && wardAdmissionId.value) {
      try {
        const ipdResponse = await consultationAPI.getAllInpatientInvestigations(wardAdmissionId.value);
        const ipdInvestigations = ipdResponse.data || [];
        // Merge OPD and IPD investigations
        investigations.value = [...opdInvestigations, ...ipdInvestigations];
      } catch (ipdErr) {
        console.error('Failed to load IPD investigations:', ipdErr);
        // If IPD investigations fail to load, just use OPD investigations
        investigations.value = opdInvestigations;
      }
    } else {
      // For OPD claims, just use OPD investigations
      investigations.value = opdInvestigations;
    }
  } catch (err) {
    console.error('Failed to load investigations:', err);
    investigations.value = [];
  } finally {
    loadingInvestigations.value = false;
  }
};

const showMedicineSelectDialog = () => {
  selectedUndispensedKeys.value = undispensedMedicines.value.map((med) => med.prescriptionKey);
  medicineSelectDialogOpen.value = true;
  return new Promise((resolve) => {
    medicineSelectDeferred = resolve;
  });
};

const toggleUndispensedKey = (key, checked) => {
  if (checked) {
    if (!selectedUndispensedKeys.value.includes(key)) {
      selectedUndispensedKeys.value.push(key);
    }
  } else {
    selectedUndispensedKeys.value = selectedUndispensedKeys.value.filter((k) => k !== key);
  }
};

const cancelMedicineSelection = () => {
  medicineSelectDialogOpen.value = false;
  medicineSelectDeferred?.({ cancelled: true, opd: [], ipd: [] });
  medicineSelectDeferred = null;
};

const confirmMedicineSelection = () => {
  const opd = [];
  const ipd = [];
  for (const key of selectedUndispensedKeys.value) {
    if (key.startsWith('ipd-')) {
      ipd.push(parseInt(key.slice(4), 10));
    } else {
      opd.push(parseInt(key.slice(4), 10));
    }
  }
  medicineSelectDialogOpen.value = false;
  medicineSelectDeferred?.({ cancelled: false, opd, ipd });
  medicineSelectDeferred = null;
};

const submitClaim = async (includePrescriptionIds = { opd: [], ipd: [] }) => {
  generating.value = true;
  try {
    const claimData = {
      ...claimForm,
    };

    if (includePrescriptionIds.opd.length > 0) {
      claimData.include_prescription_ids = includePrescriptionIds.opd;
    }
    if (includePrescriptionIds.ipd.length > 0) {
      claimData.include_inpatient_prescription_ids = includePrescriptionIds.ipd;
    }

    // For IPD claims, include ward_admission_id; for OPD, include encounter_id
    if (isIPD.value && wardAdmissionId.value) {
      claimData.ward_admission_id = wardAdmissionId.value;
      claimData.type_of_service = 'IPD';
    } else {
      claimData.encounter_id = encounter.value.id;
    }

    let claimId;

    if (isRegenerating.value && existingClaimId.value) {
      const response = await claimsAPI.regenerate(existingClaimId.value, claimData);
      claimId = response.data.id;

      $q.notify({
        type: 'positive',
        message: 'Claim regenerated successfully',
      });
    } else {
      const response = await claimsAPI.create(claimData);
      claimId = response.data.id;

      $q.notify({
        type: 'positive',
        message: 'Claim generated successfully',
      });
    }

    router.push(`/claims/edit/${claimId}`);
  } catch (err) {
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Failed to generate claim',
      timeout: 5000,
    });
  } finally {
    generating.value = false;
  }
};

const generateClaim = async () => {
  // If there are incomplete investigations, show a confirmation dialog
  if (incompleteInvestigations.value.length > 0) {
    const incompleteList = incompleteInvestigations.value
      .slice(0, 5)
      .map(inv => inv.procedure_name || inv.gdrg_code)
      .join(', ');
    const moreCount = incompleteInvestigations.value.length > 5 
      ? ` and ${incompleteInvestigations.value.length - 5} more` 
      : '';
    
    const confirmed = await new Promise((resolve) => {
      $q.dialog({
        title: 'Unfinalized Services Detected',
        message: `Some investigations (${incompleteInvestigations.value.length}) have not been finalized yet: ${incompleteList}${moreCount}.\n\nThese services will be included in the claim. Do you want to proceed with ${isRegenerating.value ? 'regenerating' : 'generating'} the claim?`,
        cancel: true,
        persistent: true,
      }).onOk(() => resolve(true)).onCancel(() => resolve(false));
    });
    
    if (!confirmed) {
      return;
    }
  }

  let includePrescriptionIds = { opd: [], ipd: [] };
  if (undispensedMedicines.value.length > 0) {
    const wantsInclude = await new Promise((resolve) => {
      $q.dialog({
        title: 'Undispensed Medicines',
        message: `${undispensedMedicines.value.length} medicine(s) have not been dispensed yet. Do you want to include any of them in the claim?`,
        cancel: { label: 'No, skip undispensed', flat: true },
        ok: { label: 'Yes, choose medicines', color: 'primary' },
        persistent: true,
      })
        .onOk(() => resolve(true))
        .onCancel(() => resolve(false));
    });

    if (wantsInclude) {
      const selection = await showMedicineSelectDialog();
      if (selection.cancelled) {
        return;
      }
      includePrescriptionIds = { opd: selection.opd, ipd: selection.ipd };
    }
  }

  await submitClaim(includePrescriptionIds);
};

const loadExistingClaim = async (claimId) => {
  try {
    const response = await claimsAPI.get(claimId);
    const claim = response.data;
    
    if (claim) {
      claimForm.physician_id = claim.physician_id || '';
      claimForm.type_of_service = claim.type_of_service || 'OPD';
      claimForm.type_of_attendance = claim.type_of_attendance || 'EAE';
      claimForm.specialty_attended = claim.specialty_attended || 'OPDC';
    }
  } catch (err) {
    console.error('Failed to load existing claim:', err);
  }
};

onMounted(async () => {
  // Check if this is a regeneration
  const regenerate = route.query.regenerate === 'true';
  const claimId = route.query.claimId;
  
  if (regenerate && claimId) {
    isRegenerating.value = true;
    existingClaimId.value = parseInt(claimId);
    // Load existing claim data to pre-fill form
    await loadExistingClaim(existingClaimId.value);
  }
  
  loadEncounter();
});
</script>

