<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Claims Management</div>

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
        
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="searchEncounterId"
            filled
            type="number"
            label="Search Encounter ID"
            class="col-12 col-md-4"
            @keyup.enter="searchEncounter"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchEncounter"
            class="col-12 col-md-2 glass-button"
          />
        </div>

        <q-table
          :rows="finalizedEncounters"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
        >
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
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Generate Claim Dialog -->
    <q-dialog v-model="showClaimDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ editing ? 'Edit Claim' : 'Generate Claim' }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="createClaim" class="q-gutter-md">
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
              :options="['EAE', 'Referral']"
              filled
              label="Type of Attendance"
            />
            <q-input
              v-model="claimForm.specialty_attended"
              filled
              label="Specialty Attended"
            />
            <div>
              <q-btn :label="editing ? 'Update' : 'Generate'" type="submit" color="primary" :loading="generating" />
              <q-btn label="Cancel" flat v-close-popup @click="() => { editing = false; currentClaimId = null; }" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue';
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

const searchEncounterId = ref('');
const finalizedEncounters = ref([]);
const claimType = ref(null); // 'opd' | 'ipd' | null
const loading = ref(false);

const showClaimDialog = ref(false);
const generating = ref(false);
const editing = ref(false);
const currentEncounterId = ref(null);
const currentClaimId = ref(null);

const claimForm = reactive({
  physician_id: '',
  type_of_service: 'OPD',
  type_of_attendance: 'EAE',
  specialty_attended: 'OPDC',
});

const columns = [
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
    loadFinalizedEncounters();
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
  } finally {
    loading.value = false;
  }
};

const generateClaim = (encounter) => {
  currentEncounterId.value = encounter.id;
  currentClaimId.value = null;
  editing.value = false;
  // Reset form
  Object.assign(claimForm, {
    physician_id: '',
    type_of_service: 'OPD',
    type_of_attendance: 'EAE',
    specialty_attended: 'OPDC',
  });
  showClaimDialog.value = true;
};

const editClaim = async (encounter) => {
  if (!encounter.claim_id) return;
  
  // Navigate to edit page
  $router.push(`/claims/edit/${encounter.claim_id}`);
};

const createClaim = async () => {
  if (editing.value && currentClaimId.value) {
    // Update existing claim
    generating.value = true;
    try {
      const claimData = {
        encounter_id: currentEncounterId.value,
        ...claimForm,
      };
      
      await claimsAPI.update(currentClaimId.value, claimData);
      
      $q.notify({
        type: 'positive',
        message: 'Claim updated successfully',
      });
      
      showClaimDialog.value = false;
      Object.assign(claimForm, {
        physician_id: '',
        type_of_service: 'OPD',
        type_of_attendance: 'EAE',
        specialty_attended: 'OPDC',
      });
      currentClaimId.value = null;
      editing.value = false;
      
      loadFinalizedEncounters();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to update claim',
      });
    } finally {
      generating.value = false;
    }
  } else {
    // Create new claim
    generating.value = true;
    try {
      const claimData = {
        encounter_id: currentEncounterId.value,
        ...claimForm,
      };
      
      await claimsStore.createClaim(claimData);
      showClaimDialog.value = false;
      Object.assign(claimForm, {
        physician_id: '',
        type_of_service: 'OPD',
        type_of_attendance: 'EAE',
        specialty_attended: 'OPDC',
      });
      
      loadFinalizedEncounters();
    } catch (error) {
      // Error handled in store
    } finally {
      generating.value = false;
    }
  }
};

const finalizeClaim = async (claimId) => {
  $q.dialog({
    title: 'Finalize Claim',
    message: 'Are you sure you want to finalize this claim?',
    cancel: true,
  }).onOk(async () => {
    try {
      await claimsStore.finalizeClaim(claimId);
      loadFinalizedEncounters();
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
      loadFinalizedEncounters();
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

const loadFinalizedEncounters = async () => {
  loading.value = true;
  try {
    const response = await claimsAPI.getEligibleEncounters(claimType.value);
    finalizedEncounters.value = response.data.map(encounter => ({
      id: encounter.id,
      patient_name: encounter.patient_name,
      patient_card_number: encounter.patient_card_number,
      ccc_number: encounter.ccc_number,
      finalized_at: encounter.finalized_at,
      claim_id: encounter.claim_id,
      claim_status: encounter.claim_status,
      department: encounter.department,
    }));
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    finalizedEncounters.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadFinalizedEncounters();
});

watch(claimType, () => {
  loadFinalizedEncounters();
});
</script>

