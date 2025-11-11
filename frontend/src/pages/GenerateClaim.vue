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
      <strong>Incomplete Investigations Detected</strong>
      <div class="text-caption q-mt-xs">
        The following investigations are not completed. Claims cannot be generated until all investigations are completed:
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

    <!-- Medicines Section -->
    <q-card v-if="encounter && !loading" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Medicines (Prescriptions)</div>
        <q-table
          v-if="medicines.length > 0"
          :rows="medicines"
          :columns="medicineColumns"
          row-key="id"
          flat
          :loading="loadingMedicines"
        >
          <template v-slot:body-cell-status="props">
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
        </q-table>
        <div v-else class="text-center text-grey-7 q-pa-md">
          No investigations for this encounter
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
            label="Physician ID *"
            lazy-rules
            :rules="[(val) => !!val || 'Required']"
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
              :disable="incompleteInvestigations.length > 0"
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
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { encountersAPI, consultationAPI, claimsAPI } from '../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const loading = ref(false);
const loadingMedicines = ref(false);
const loadingInvestigations = ref(false);
const generating = ref(false);
const error = ref(null);
const isRegenerating = ref(false);
const existingClaimId = ref(null);

const encounter = ref(null);
const medicines = ref([]);
const investigations = ref([]);

const claimForm = reactive({
  physician_id: '',
  type_of_service: 'OPD',
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
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
];

const investigationColumns = [
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'procedure_name', label: 'Procedure Name', field: 'procedure_name', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'service_date', label: 'Service Date', field: 'service_date', align: 'left', format: (val) => val ? new Date(val).toLocaleString() : '-' },
];

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
};

const getMedicineStatusColor = (status) => {
  const colors = {
    'pending': 'orange',
    'dispensed': 'green',
    'returned': 'red',
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
    
    // Auto-fill physician_id with finalized_by username if available (for both new and regeneration)
    if (response.data.finalized_by_username) {
      claimForm.physician_id = response.data.finalized_by_username;
    }
    
    // Load medicines and investigations in parallel
    await Promise.all([
      loadMedicines(encounterId),
      loadInvestigations(encounterId),
    ]);
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

const loadMedicines = async (encounterId) => {
  loadingMedicines.value = true;
  try {
    const response = await consultationAPI.getPrescriptions(encounterId);
    medicines.value = response.data || [];
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
    const response = await consultationAPI.getInvestigations(encounterId);
    investigations.value = response.data || [];
  } catch (err) {
    console.error('Failed to load investigations:', err);
    investigations.value = [];
  } finally {
    loadingInvestigations.value = false;
  }
};

const generateClaim = async () => {
  if (incompleteInvestigations.value.length > 0) {
    $q.notify({
      type: 'negative',
      message: 'Cannot generate claim. Please complete all investigations first.',
      timeout: 5000,
    });
    return;
  }

  generating.value = true;
  try {
    const claimData = {
      encounter_id: encounter.value.id,
      ...claimForm,
    };

    if (isRegenerating.value && existingClaimId.value) {
      // Regenerate existing claim
      await claimsAPI.regenerate(existingClaimId.value, claimData);
      
      $q.notify({
        type: 'positive',
        message: 'Claim regenerated successfully',
      });
    } else {
      // Create new claim
      await claimsAPI.create(claimData);
      
      $q.notify({
        type: 'positive',
        message: 'Claim generated successfully',
      });
    }

    router.push('/claims');
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

