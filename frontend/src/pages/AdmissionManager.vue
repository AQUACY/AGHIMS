<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Ward"
        @click="$router.push('/ipd/doctor-nursing-station')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Admission Manager
      </div>
    </div>

    <!-- Patient Info Card -->
    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center">
          <q-avatar size="64px" color="primary" text-color="white" class="q-mr-md">
            <q-icon name="person" size="40px" />
          </q-avatar>
          <div class="col">
            <div class="text-h5 text-weight-bold glass-text q-mb-xs">
              {{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}
              <span v-if="patientInfo.patient_other_names">
                {{ patientInfo.patient_other_names }}
              </span>
            </div>
            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-6">
                <div class="text-body2 text-secondary">
                  <q-icon name="credit_card" size="16px" class="q-mr-xs" />
                  Card: {{ patientInfo.patient_card_number }}
                </div>
                <div class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="person" size="16px" class="q-mr-xs" />
                  {{ patientInfo.patient_gender }}
                  <span v-if="patientInfo.patient_date_of_birth" class="q-ml-sm">
                    | DOB: {{ formatDate(patientInfo.patient_date_of_birth) }}
                  </span>
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="text-body2 text-secondary">
                  <q-icon name="local_hospital" size="16px" class="q-mr-xs" />
                  Ward: <strong>{{ patientInfo.ward }}</strong>
                </div>
                <div class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="schedule" size="16px" class="q-mr-xs" />
                  Admitted: {{ formatDateTime(patientInfo.admitted_at) }}
                </div>
                <div v-if="patientInfo.admitted_by_name" class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="person" size="16px" class="q-mr-xs" />
                  Admitted by: <strong>{{ patientInfo.admitted_by_name }}</strong>
                  <span v-if="patientInfo.admitted_by_role"> ({{ patientInfo.admitted_by_role }})</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading patient information...</div>
      </q-card-section>
    </q-card>

    <!-- Main Content Layout -->
    <div v-else class="row q-col-gutter-md">
      <!-- Main Body - Middle Section -->
      <div class="col-12 col-md-8 col-lg-9">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-h6 glass-text q-mb-md">
              Inpatient Activities
            </div>
            <div class="text-body2 text-secondary text-center q-pa-xl">
              <!-- Blank card - will be populated later -->
              <q-icon name="inbox" size="64px" color="grey-6" class="q-mb-md" />
              <div class="text-subtitle1 glass-text">
                Content will be added here
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Right Sidebar - Quick Actions -->
      <div class="col-12 col-md-4 col-lg-3">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-h6 glass-text q-mb-md">
              <q-icon name="flash_on" color="primary" class="q-mr-sm" />
              Quick Actions
            </div>
            <div class="column q-gutter-sm">
              <q-btn
                flat
                icon="visibility"
                label="View Patient Profile"
                color="primary"
                @click="viewPatient"
                class="full-width"
              />
              <q-btn
                flat
                icon="medical_services"
                label="View Encounter"
                color="secondary"
                @click="viewEncounter"
                class="full-width"
              />
              <q-btn
                flat
                icon="monitor_heart"
                label="Vitals"
                color="info"
                @click="viewVitals"
                class="full-width"
              />
              <q-btn
                flat
                icon="medication"
                label="Prescriptions"
                color="accent"
                @click="viewPrescriptions"
                class="full-width"
              />
              <q-btn
                flat
                icon="science"
                label="Investigations"
                color="purple"
                @click="viewInvestigations"
                class="full-width"
              />
              <q-separator class="q-my-sm" />
              <q-btn
                flat
                icon="note_add"
                label="Add Note"
                color="orange"
                @click="addNote"
                class="full-width"
              />
              <q-btn
                flat
                icon="assignment"
                label="Daily Notes"
                color="teal"
                @click="viewDailyNotes"
                class="full-width"
              />
              <q-btn
                flat
                icon="receipt"
                label="Billing"
                color="amber"
                @click="viewBilling"
                class="full-width"
              />
              <q-separator class="q-my-sm" />
              <q-btn
                flat
                icon="exit_to_app"
                label="Discharge Patient"
                color="negative"
                @click="dischargePatient"
                :loading="discharging"
                class="full-width"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Additional sections can be added here for inpatient activities -->
    <!-- Examples: Daily notes, medication schedule, test results, etc. -->
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();

const loading = ref(false);
const patientInfo = ref(null);
const discharging = ref(false);

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);
const cardNumber = computed(() => route.query.card_number || null);

const loadPatientInfo = async () => {
  if (!wardAdmissionId.value) return;
  
  loading.value = true;
  try {
    // Load all ward admissions to find this patient
    const response = await consultationAPI.getWardAdmissions();
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    // Find the specific patient
    const patient = data.find(p => p.id === wardAdmissionId.value);
    if (patient) {
      patientInfo.value = patient;
    } else {
      $q.notify({
        type: 'negative',
        message: 'Patient not found in ward admissions',
      });
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load patient information',
    });
  } finally {
    loading.value = false;
  }
};

const viewPatient = () => {
  if (cardNumber.value) {
    router.push(`/patients/${cardNumber.value}`);
  } else if (patientInfo.value?.patient_card_number) {
    router.push(`/patients/${patientInfo.value.patient_card_number}`);
  }
};

const viewEncounter = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}`);
  }
};

const viewVitals = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#vitals`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#vitals`);
  }
};

const viewPrescriptions = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#prescriptions`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#prescriptions`);
  }
};

const viewInvestigations = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#investigations`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#investigations`);
  }
};

const addNote = () => {
  // TODO: Implement add note functionality
  $q.notify({
    type: 'info',
    message: 'Add note functionality will be implemented soon',
  });
};

const viewDailyNotes = () => {
  // TODO: Implement daily notes view
  $q.notify({
    type: 'info',
    message: 'Daily notes functionality will be implemented soon',
  });
};

const viewBilling = () => {
  if (encounterId.value) {
    router.push(`/billing/${encounterId.value}`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/billing/${patientInfo.value.encounter_id}`);
  }
};

const dischargePatient = async () => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Discharge Patient',
    message: `Are you sure you want to discharge ${patientInfo.value?.patient_name} ${patientInfo.value?.patient_surname} from ${patientInfo.value?.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    discharging.value = true;
    try {
      await consultationAPI.dischargePatient(wardAdmissionId.value);
      $q.notify({
        type: 'positive',
        message: 'Patient discharged successfully',
      });
      // Redirect back to ward page
      router.push('/ipd/doctor-nursing-station');
    } catch (error) {
      console.error('Error discharging patient:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to discharge patient',
      });
    } finally {
      discharging.value = false;
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

onMounted(() => {
  loadPatientInfo();
});
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

