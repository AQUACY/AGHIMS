<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Inpatient Department (IPD)
    </div>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading admission recommendations...</div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="!loading && admissions.length === 0" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="local_hospital" size="64px" color="grey-6" />
        <div class="text-subtitle1 q-mt-md glass-text">No patients recommended for admission</div>
      </q-card-section>
    </q-card>

    <!-- Admissions Table -->
    <q-card v-else class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            Admission Recommendations ({{ admissions.length }})
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Refresh"
            @click="loadAdmissions"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="admissions"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :filter="filter"
          @request="onRequest"
          :pagination="pagination"
          class="glass-table"
        >
          <template v-slot:top>
            <q-input
              v-model="filter"
              filled
              dense
              placeholder="Search by name, card number, or ward..."
              class="col-12 col-md-4"
            >
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>
          </template>

          <template v-slot:body-cell-patient="props">
            <q-td :props="props">
              <div>
                <div class="text-weight-medium glass-text">
                  {{ props.row.patient_name }} {{ props.row.patient_surname }}
                  <span v-if="props.row.patient_other_names">
                    {{ props.row.patient_other_names }}
                  </span>
                </div>
                <div class="text-caption text-secondary">
                  Card: {{ props.row.patient_card_number }}
                </div>
                <div class="text-caption text-secondary">
                  {{ props.row.patient_gender }} | 
                  <span v-if="props.row.patient_date_of_birth">
                    DOB: {{ formatDate(props.row.patient_date_of_birth) }}
                  </span>
                </div>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <q-badge color="primary" :label="props.value" />
            </q-td>
          </template>

          <template v-slot:body-cell-date="props">
            <q-td :props="props">
              <div class="glass-text">{{ formatDateTime(props.value) }}</div>
              <div v-if="props.row.finalized_by_name" class="text-caption text-secondary q-mt-xs">
                Finalized by: <strong>{{ props.row.finalized_by_name }}</strong>
                <span v-if="props.row.finalized_by_role"> ({{ props.row.finalized_by_role }})</span>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                icon="visibility"
                label="View Patient"
                color="primary"
                size="sm"
                @click="viewPatient(props.row.patient_card_number)"
                class="q-mr-xs"
              />
              <q-btn
                flat
                dense
                icon="medical_services"
                label="View Encounter"
                color="secondary"
                size="sm"
                @click="viewEncounter(props.row.encounter_id)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();

const loading = ref(false);
const admissions = ref([]);
const filter = ref('');

const pagination = ref({
  sortBy: 'created_at',
  descending: true,
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0,
});

const columns = [
  {
    name: 'patient',
    required: true,
    label: 'Patient',
    align: 'left',
    field: (row) => `${row.patient_name} ${row.patient_surname}`,
    sortable: true,
  },
  {
    name: 'ward',
    required: true,
    label: 'Ward',
    align: 'center',
    field: 'ward',
    sortable: true,
  },
  {
    name: 'encounter_type',
    label: 'Service Type',
    align: 'center',
    field: 'encounter_service_type',
    sortable: true,
  },
  {
    name: 'date',
    label: 'Recommended Date',
    align: 'center',
    field: 'created_at',
    sortable: true,
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center',
    field: 'actions',
    sortable: false,
  },
];

const loadAdmissions = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getAdmissionRecommendations();
    console.log('Admissions API response:', response);
    console.log('Response data:', response.data);
    
    // Handle both array and object responses
    if (Array.isArray(response.data)) {
      admissions.value = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      admissions.value = response.data.data;
    } else {
      admissions.value = [];
    }
    
    pagination.value.rowsNumber = admissions.value.length;
    console.log('Loaded admissions:', admissions.value.length);
  } catch (error) {
    console.error('Error loading admissions:', error);
    console.error('Error response:', error.response);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load admission recommendations',
    });
    admissions.value = [];
  } finally {
    loading.value = false;
  }
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

const onRequest = (props) => {
  const { page, rowsPerPage, sortBy, descending } = props.pagination;
  pagination.value.page = page;
  pagination.value.rowsPerPage = rowsPerPage;
  pagination.value.sortBy = sortBy;
  pagination.value.descending = descending;
};

onMounted(() => {
  loadAdmissions();
});
</script>

<style scoped>
/* Table cell text styling for better visibility */
.glass-table :deep(.q-table__top),
.glass-table :deep(.q-table__bottom),
.glass-table :deep(.q-table tbody td),
.glass-table :deep(.q-table thead th) {
  color: inherit;
}

/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--light .glass-table :deep(.q-table thead th) {
  color: rgba(0, 0, 0, 0.87);
  font-weight: 500;
}

.body--light .glass-table :deep(.q-table tbody td) {
  color: rgba(0, 0, 0, 0.87);
}

.body--light .glass-table :deep(.q-table tbody td .text-secondary) {
  color: rgba(0, 0, 0, 0.6) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.body--dark .glass-table :deep(.q-table thead th) {
  color: rgba(255, 255, 255, 0.9);
}

.body--dark .glass-table :deep(.q-table tbody td) {
  color: rgba(255, 255, 255, 0.9);
}

.body--dark .glass-table :deep(.q-table tbody td .text-secondary) {
  color: rgba(255, 255, 255, 0.6) !important;
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

