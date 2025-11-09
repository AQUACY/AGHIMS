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
        Admission Recommendations
      </div>
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
            Admission Recommendations 
            <span v-if="selectedWard">({{ filteredAdmissions.length }} in {{ selectedWard }})</span>
            <span v-else>({{ allAdmissions.length }} total)</span>
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
          :rows="filteredAdmissions"
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
            <div class="row q-col-gutter-md q-mb-md" style="width: 100%;">
              <div class="col-12 col-md-4">
                <q-select
                  v-model="selectedWard"
                  :options="wardOptions"
                  filled
                  dense
                  label="Filter by Ward"
                  clearable
                  emit-value
                  map-options
                  @update:model-value="onWardFilterChange"
                >
                  <template v-slot:prepend>
                    <q-icon name="local_hospital" />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="filter"
                  filled
                  dense
                  placeholder="Search by card number..."
                  @update:model-value="onSearchChange"
                >
                  <template v-slot:append>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-badge v-if="selectedWard" color="primary" :label="`Ward: ${selectedWard}`" class="q-mr-sm" />
                <q-badge color="info" :label="`Showing: ${filteredAdmissions.length} of ${allAdmissions.length}`" />
              </div>
            </div>
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
              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="visibility"
                  label="View Patient"
                  color="primary"
                  size="sm"
                  @click="viewPatient(props.row.patient_card_number)"
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
                <template v-if="props.row.cancelled === 1">
                  <q-chip
                    color="negative"
                    text-color="white"
                    icon="cancel"
                    size="sm"
                  >
                    Cancelled
                  </q-chip>
                  <q-btn
                    flat
                    dense
                    icon="info"
                    label="View Reason"
                    color="info"
                    size="sm"
                    @click="showCancellationReason(props.row)"
                  />
                </template>
                <template v-else-if="!props.row.confirmed_by">
                  <q-btn
                    flat
                    dense
                    icon="check_circle"
                    label="Confirm Admission"
                    color="positive"
                    size="sm"
                    @click="confirmAdmission(props.row)"
                    :loading="confirmingId === props.row.id"
                  />
                  <q-btn
                    flat
                    dense
                    icon="cancel"
                    label="Cancel"
                    color="negative"
                    size="sm"
                    @click="cancelAdmission(props.row)"
                    :loading="cancellingId === props.row.id"
                  />
                </template>
                <template v-else>
                  <q-chip
                    color="positive"
                    text-color="white"
                    icon="check_circle"
                    size="sm"
                  >
                    Confirmed
                  </q-chip>
                  <q-btn
                    flat
                    dense
                    icon="undo"
                    label="Revert"
                    color="warning"
                    size="sm"
                    @click="revertConfirmation(props.row)"
                    :loading="revertingId === props.row.id"
                  />
                  <q-btn
                    flat
                    dense
                    icon="cancel"
                    label="Cancel"
                    color="negative"
                    size="sm"
                    @click="cancelAdmission(props.row)"
                    :loading="cancellingId === props.row.id"
                  />
                </template>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Cancel Admission Dialog -->
    <q-dialog v-model="showCancelDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Cancel Admission</div>
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <div class="text-body2 glass-text q-mb-sm">
              <strong>Patient:</strong> {{ selectedAdmissionForCancel?.patient_name }} {{ selectedAdmissionForCancel?.patient_surname }}
            </div>
            <div class="text-body2 glass-text">
              <strong>Ward:</strong> {{ selectedAdmissionForCancel?.ward }}
            </div>
          </div>
          <q-input
            v-model="cancelReason"
            filled
            type="textarea"
            label="Cancellation Reason *"
            hint="Please provide a reason for cancelling this admission"
            :rules="[val => !!val || 'Cancellation reason is required']"
            rows="4"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showCancelDialog = false" />
          <q-btn 
            flat 
            label="Confirm Cancel" 
            color="negative" 
            @click="submitCancelAdmission"
            :loading="cancellingId !== null"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
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
const admissions = ref([]);
const allAdmissions = ref([]); // Store all admissions before filtering
const filter = ref('');
const selectedWard = ref(null);
const confirmingId = ref(null);
const revertingId = ref(null);
const cancellingId = ref(null);
const cancelReason = ref('');
const showCancelDialog = ref(false);
const selectedAdmissionForCancel = ref(null);

const pagination = ref({
  sortBy: 'created_at',
  descending: true,
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0,
});

// Get unique wards from admissions
const wardOptions = computed(() => {
  const wards = new Set();
  allAdmissions.value.forEach(admission => {
    if (admission.ward) {
      wards.add(admission.ward);
    }
  });
  return Array.from(wards).sort().map(ward => ({
    label: ward,
    value: ward
  }));
});

// Filter admissions based on ward and search (exclude cancelled)
const filteredAdmissions = computed(() => {
  let filtered = [...allAdmissions.value];
  
  // Exclude cancelled admissions
  filtered = filtered.filter(admission => admission.cancelled !== 1);
  
  // Filter by ward
  if (selectedWard.value) {
    filtered = filtered.filter(admission => admission.ward === selectedWard.value);
  }
  
  // Filter by search (card number)
  if (filter.value) {
    const searchTerm = filter.value.toLowerCase();
    filtered = filtered.filter(admission => {
      const cardNumber = admission.patient_card_number?.toLowerCase() || '';
      return cardNumber.includes(searchTerm);
    });
  }
  
  return filtered;
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
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    allAdmissions.value = data;
    admissions.value = data;
    
    pagination.value.rowsNumber = filteredAdmissions.value.length;
    console.log('Loaded admissions:', allAdmissions.value.length);
  } catch (error) {
    console.error('Error loading admissions:', error);
    console.error('Error response:', error.response);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load admission recommendations',
    });
    allAdmissions.value = [];
    admissions.value = [];
  } finally {
    loading.value = false;
  }
};

const onWardFilterChange = () => {
  pagination.value.rowsNumber = filteredAdmissions.value.length;
  pagination.value.page = 1;
};

const onSearchChange = () => {
  pagination.value.rowsNumber = filteredAdmissions.value.length;
  pagination.value.page = 1;
};

const confirmAdmission = async (admission) => {
  $q.dialog({
    title: 'Confirm Admission',
    message: `Are you sure you want to confirm admission for ${admission.patient_name} ${admission.patient_surname} to ${admission.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    confirmingId.value = admission.id;
    try {
      await consultationAPI.confirmAdmission(admission.id);
      $q.notify({
        type: 'positive',
        message: 'Admission confirmed successfully',
      });
      // Reload admissions to get updated status
      await loadAdmissions();
    } catch (error) {
      console.error('Error confirming admission:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to confirm admission',
      });
    } finally {
      confirmingId.value = null;
    }
  });
};

const revertConfirmation = async (admission) => {
  $q.dialog({
    title: 'Revert Confirmation',
    message: `Are you sure you want to revert the confirmation for ${admission.patient_name} ${admission.patient_surname}? This will remove them from the ward and return to recommendation status.`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    revertingId.value = admission.id;
    try {
      await consultationAPI.revertAdmissionConfirmation(admission.id);
      $q.notify({
        type: 'positive',
        message: 'Admission confirmation reverted successfully',
      });
      // Reload admissions to get updated status
      await loadAdmissions();
    } catch (error) {
      console.error('Error reverting confirmation:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to revert confirmation',
      });
    } finally {
      revertingId.value = null;
    }
  });
};

const cancelAdmission = (admission) => {
  selectedAdmissionForCancel.value = admission;
  cancelReason.value = '';
  showCancelDialog.value = true;
};

const submitCancelAdmission = async () => {
  if (!cancelReason.value.trim()) {
    $q.notify({
      type: 'negative',
      message: 'Please provide a cancellation reason',
    });
    return;
  }

  const admission = selectedAdmissionForCancel.value;
  if (!admission) return;

  cancellingId.value = admission.id;
  try {
    await consultationAPI.cancelAdmission(admission.id, cancelReason.value);
    $q.notify({
      type: 'positive',
      message: 'Admission cancelled successfully',
    });
    showCancelDialog.value = false;
    selectedAdmissionForCancel.value = null;
    cancelReason.value = '';
    // Reload admissions to get updated status
    await loadAdmissions();
  } catch (error) {
    console.error('Error cancelling admission:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to cancel admission',
    });
  } finally {
    cancellingId.value = null;
  }
};

const showCancellationReason = (admission) => {
  $q.dialog({
    title: 'Cancellation Reason',
    message: `<strong>Patient:</strong> ${admission.patient_name} ${admission.patient_surname}<br/><strong>Ward:</strong> ${admission.ward}<br/><strong>Reason:</strong> ${admission.cancellation_reason || 'No reason provided'}`,
    html: true,
    persistent: true
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

