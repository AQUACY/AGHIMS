<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to IPD"
        @click="$router.push('/ipd')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Doctor/Nursing Station
      </div>
    </div>

    <!-- Ward Filter - Must select ward first -->
    <q-card v-if="!selectedWard" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">Select Ward</div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
              dense
              label="Select Ward"
              emit-value
              map-options
              @update:model-value="onWardSelected"
            >
              <template v-slot:prepend>
                <q-icon name="local_hospital" />
              </template>
            </q-select>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Loading State -->
    <q-card v-if="loading && selectedWard" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading ward patients...</div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="!loading && selectedWard && wardPatients.length === 0" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="local_hospital" size="64px" color="grey-6" />
        <div class="text-subtitle1 q-mt-md glass-text">No patients currently admitted to {{ selectedWard }}</div>
      </q-card-section>
    </q-card>

    <!-- Ward Patients Cards -->
    <div v-else-if="selectedWard && wardPatients.length > 0">
      <div class="row items-center q-mb-md">
        <div class="text-h6 glass-text">
          {{ selectedWard }} - Active Patients ({{ filteredPatients.length }})
        </div>
        <q-space />
        <q-input
          v-model="filter"
          filled
          dense
          placeholder="Search by card number..."
          class="q-mr-md"
          style="max-width: 300px;"
        >
          <template v-slot:append>
            <q-icon name="search" />
          </template>
        </q-input>
        <q-btn
          flat
          icon="refresh"
          label="Refresh"
          @click="loadWardPatients"
          class="glass-button"
        />
      </div>

      <div class="row q-col-gutter-md">
        <div
          v-for="patient in filteredPatients"
          :key="patient.id"
          class="col-12 col-md-6 col-lg-4"
        >
          <q-card class="patient-card glass-card" flat bordered>
            <q-card-section>
              <div class="row items-start q-mb-md">
                <q-avatar size="56px" color="primary" text-color="white" class="q-mr-md">
                  <q-icon name="person" size="32px" />
                </q-avatar>
                <div class="col">
                  <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                    {{ patient.patient_name }} {{ patient.patient_surname }}
                    <span v-if="patient.patient_other_names">
                      {{ patient.patient_other_names }}
                    </span>
                  </div>
                  <div class="text-caption text-secondary q-mb-xs">
                    <q-icon name="credit_card" size="14px" class="q-mr-xs" />
                    Card: {{ patient.patient_card_number }}
                  </div>
                  <div class="text-caption text-secondary">
                    <q-icon name="person" size="14px" class="q-mr-xs" />
                    {{ patient.patient_gender }}
                    <span v-if="patient.patient_date_of_birth" class="q-ml-sm">
                      | DOB: {{ formatDate(patient.patient_date_of_birth) }}
                    </span>
                  </div>
                </div>
              </div>

              <q-separator class="q-mb-md" />

              <div class="row q-col-gutter-xs q-mb-md">
                <div class="col-12">
                  <q-badge color="primary" :label="patient.ward" class="q-mr-sm" />
                  <q-badge color="info" :label="patient.encounter_service_type" />
                </div>
              </div>

              <div class="text-caption text-secondary q-mb-md">
                <div>
                  <q-icon name="schedule" size="14px" class="q-mr-xs" />
                  Admitted: {{ formatDateTime(patient.admitted_at) }}
                </div>
                <div v-if="patient.admitted_by_name" class="q-mt-xs">
                  By: <strong>{{ patient.admitted_by_name }}</strong>
                  <span v-if="patient.admitted_by_role"> ({{ patient.admitted_by_role }})</span>
                </div>
              </div>

              <q-separator class="q-mb-md" />

              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="visibility"
                  label="View Patient"
                  color="primary"
                  size="sm"
                  @click="viewPatient(patient.patient_card_number)"
                  class="col"
                />
                <q-btn
                  flat
                  dense
                  icon="medical_services"
                  label="View Encounter"
                  color="secondary"
                  size="sm"
                  @click="viewEncounter(patient.encounter_id)"
                  class="col"
                />
              </div>
              <div class="row q-gutter-xs q-mt-xs">
                <q-btn
                  flat
                  dense
                  icon="manage_accounts"
                  label="AM"
                  color="accent"
                  size="sm"
                  @click="openAdmissionManager(patient)"
                  class="col"
                />
                <q-btn
                  flat
                  dense
                  icon="exit_to_app"
                  label="Discharge"
                  color="negative"
                  size="sm"
                  @click="dischargePatient(patient)"
                  :loading="dischargingId === patient.id"
                  class="col"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();

const loading = ref(false);
const wardPatients = ref([]);
const allWardPatients = ref([]); // Store all for getting unique wards
const filter = ref('');
const selectedWard = ref(null);
const dischargingId = ref(null);


// Get unique wards from all ward patients
const wardOptions = computed(() => {
  const wards = new Set();
  allWardPatients.value.forEach(patient => {
    if (patient.ward) {
      wards.add(patient.ward);
    }
  });
  return Array.from(wards).sort().map(ward => ({
    label: ward,
    value: ward
  }));
});

// Filter patients by search
const filteredPatients = computed(() => {
  if (!filter.value) {
    return wardPatients.value;
  }
  const searchTerm = filter.value.toLowerCase();
  return wardPatients.value.filter(patient => {
    const cardNumber = patient.patient_card_number?.toLowerCase() || '';
    const name = `${patient.patient_name} ${patient.patient_surname}`.toLowerCase();
    return cardNumber.includes(searchTerm) || name.includes(searchTerm);
  });
});

const loadWardPatients = async () => {
  if (!selectedWard.value) return;
  
  loading.value = true;
  try {
    // First load all to get ward options
    const allResponse = await consultationAPI.getWardAdmissions();
    let allData = [];
    if (Array.isArray(allResponse.data)) {
      allData = allResponse.data;
    } else if (allResponse.data && Array.isArray(allResponse.data.data)) {
      allData = allResponse.data.data;
    }
    allWardPatients.value = allData;
    
    // Then load filtered by ward
    const response = await consultationAPI.getWardAdmissions(selectedWard.value);
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    wardPatients.value = data;
  } catch (error) {
    console.error('Error loading ward patients:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load ward patients',
    });
    wardPatients.value = [];
  } finally {
    loading.value = false;
  }
};

const onWardSelected = () => {
  if (selectedWard.value) {
    loadWardPatients();
  } else {
    wardPatients.value = [];
  }
};

const dischargePatient = async (patient) => {
  $q.dialog({
    title: 'Discharge Patient',
    message: `Are you sure you want to discharge ${patient.patient_name} ${patient.patient_surname} from ${patient.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    dischargingId.value = patient.id;
    try {
      await consultationAPI.dischargePatient(patient.id);
      $q.notify({
        type: 'positive',
        message: 'Patient discharged successfully',
      });
      // Reload ward patients
      await loadWardPatients();
    } catch (error) {
      console.error('Error discharging patient:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to discharge patient',
      });
    } finally {
      dischargingId.value = null;
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

const viewPatient = (cardNumber) => {
  router.push(`/patients/${cardNumber}`);
};

const viewEncounter = (encounterId) => {
  router.push(`/consultation/${encounterId}`);
};

const openAdmissionManager = (patient) => {
  router.push(`/ipd/admission-manager/${patient.id}?encounter_id=${patient.encounter_id}&card_number=${patient.patient_card_number}`);
};

onMounted(async () => {
  // Load all ward patients to get ward options
  try {
    const response = await consultationAPI.getWardAdmissions();
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    allWardPatients.value = data;
  } catch (error) {
    console.error('Error loading ward options:', error);
  }
});
</script>

<style scoped>
/* Patient card styling */
.patient-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}

.patient-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.body--dark .patient-card:hover {
  box-shadow: 0 8px 16px rgba(255, 255, 255, 0.15);
}

/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.glass-button {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Light mode button adjustments */
.body--light .glass-button {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: rgba(0, 0, 0, 0.87);
}

.body--light .glass-button:hover {
  background: rgba(255, 255, 255, 0.9);
}
</style>

