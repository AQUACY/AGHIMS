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
        Daily Ward State
      </div>
    </div>

    <!-- Ward and Date Selection -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
              label="Select Ward *"
              emit-value
              map-options
              @update:model-value="loadWardState"
            >
              <template v-slot:prepend>
                <q-icon name="local_hospital" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model="selectedDate"
              filled
              type="date"
              label="Date"
              @update:model-value="loadWardState"
            >
              <template v-slot:prepend>
                <q-icon name="calendar_today" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-4 flex items-end">
            <q-btn
              flat
              icon="refresh"
              label="Refresh"
              color="primary"
              @click="loadWardState"
              :loading="loading"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Daily Ward State Form -->
    <q-card v-if="wardState" class="glass-card" flat bordered>
      <q-card-section>
        <!-- Header -->
        <div class="row items-center q-mb-md">
          <div class="col">
            <div class="text-h5 text-weight-bold glass-text text-center">
              DAILY WARD STATE
            </div>
            <div class="text-subtitle1 text-secondary text-center q-mt-sm">
              WARD: <strong>{{ selectedWard }}</strong> | DATE: {{ formatDate(selectedDate) }}
            </div>
          </div>
        </div>

        <q-separator class="q-mb-md" />

        <!-- Three Column Grid Layout -->
        <div class="row q-col-gutter-md">
          <!-- Column 1: Admissions -->
          <div class="col-12 col-md-4">
            <q-card flat bordered class="q-pa-md">
              <div class="text-h6 glass-text q-mb-md text-center">
                ADMISSIONS
              </div>
              <q-table
                :rows="admissionRows"
                :columns="admissionColumns"
                row-key="id"
                flat
                hide-pagination
                dense
                class="glass-table"
              >
                <template v-slot:body-cell-name="props">
                  <q-td :props="props" class="text-caption">
                    {{ props.value }}
                  </q-td>
                </template>
              </q-table>
            </q-card>
          </div>

          <!-- Column 2: Discharges -->
          <div class="col-12 col-md-4">
            <q-card flat bordered class="q-pa-md">
              <div class="text-h6 glass-text q-mb-md text-center">
                DISCHARGES
              </div>
              <q-table
                :rows="dischargeRows"
                :columns="dischargeColumns"
                row-key="id"
                flat
                hide-pagination
                dense
                class="glass-table"
              >
                <template v-slot:body-cell-name="props">
                  <q-td :props="props" class="text-caption">
                    {{ props.value }}
                  </q-td>
                </template>
              </q-table>
            </q-card>
          </div>

          <!-- Column 3: Deaths -->
          <div class="col-12 col-md-4">
            <q-card flat bordered class="q-pa-md">
              <div class="text-h6 glass-text q-mb-md text-center">
                DEATH
              </div>
              <q-table
                :rows="deathRows"
                :columns="deathColumns"
                row-key="id"
                flat
                hide-pagination
                dense
                class="glass-table"
              >
                <template v-slot:body-cell-name="props">
                  <q-td :props="props" class="text-caption">
                    {{ props.value }}
                  </q-td>
                </template>
              </q-table>
            </q-card>
          </div>
        </div>

        <q-separator class="q-my-md" />

        <!-- Summary Statistics -->
        <q-card flat bordered class="q-pa-md">
          <div class="text-h6 glass-text q-mb-md text-center">
            SUMMARY STATISTICS
          </div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Remained Previous Day</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.remained_previous_day }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Total Admissions</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.total_admissions }}</strong>
                <span class="text-caption text-secondary q-ml-sm">
                  ({{ wardState.statistics.new_admissions }} new + {{ wardState.statistics.transfers_in }} transfers)
                </span>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Total Discharges</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.total_discharges }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Total Deaths</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.total_deaths }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Transfers Out</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.transfers_out }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Remained at Midnight</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.remained_at_midnight }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6 col-lg-3">
              <div class="text-body2 text-secondary">Empty Beds</div>
              <div class="text-h6 glass-text q-mt-xs">
                <strong>{{ wardState.statistics.empty_beds }}</strong>
                <span class="text-caption text-secondary q-ml-sm">
                  ({{ wardState.statistics.occupied_beds }}/{{ wardState.statistics.total_beds }} occupied)
                </span>
              </div>
            </div>
          </div>
        </q-card>
      </q-card-section>
    </q-card>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading ward state...</div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-if="!loading && !wardState && selectedWard" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="info" size="48px" color="grey-6" class="q-mb-sm" />
        <div class="text-subtitle1 glass-text">No data available for selected ward and date</div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { useRoute } from 'vue-router';
import { consultationAPI } from '../services/api';

const $q = useQuasar();
const route = useRoute();

const loading = ref(false);
const selectedWard = ref(null);
const selectedDate = ref(new Date().toISOString().split('T')[0]);
const wardState = ref(null);

const wardOptions = [
  { label: 'Accident & Emergency Ward', value: 'Accident & Emergency Ward' },
  { label: 'Maternity Ward', value: 'Maternity Ward' },
  { label: 'Female Ward', value: 'Female Ward' },
  { label: 'Male Ward', value: 'Male Ward' },
  { label: 'Kids Ward', value: 'Kids Ward' },
  { label: 'Nicu', value: 'Nicu' },
  { label: 'Detention & Observation Ward', value: 'Detention & Observation Ward' },
];

const admissionColumns = [
  { name: 'office_no', label: 'Office No.', field: 'office_no', align: 'center', sortable: true },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'age', label: 'Age', field: 'age', align: 'center', sortable: true },
  { name: 'male', label: 'M', field: 'male', align: 'center', sortable: true },
  { name: 'female', label: 'F', field: 'female', align: 'center', sortable: true },
  { name: 'official', label: 'Official', field: 'official', align: 'center', sortable: true },
  { name: 'non_official', label: 'Non-Official', field: 'non_official', align: 'center', sortable: true },
];

const dischargeColumns = [
  { name: 'office_no', label: 'Office No.', field: 'office_no', align: 'center', sortable: true },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'age', label: 'Age', field: 'age', align: 'center', sortable: true },
  { name: 'male', label: 'M', field: 'male', align: 'center', sortable: true },
  { name: 'female', label: 'F', field: 'female', align: 'center', sortable: true },
  { name: 'official', label: 'Official', field: 'official', align: 'center', sortable: true },
  { name: 'non_official', label: 'Non-Official', field: 'non_official', align: 'center', sortable: true },
];

const deathColumns = [
  { name: 'office_no', label: 'Office No.', field: 'office_no', align: 'center', sortable: true },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'age', label: 'Age', field: 'age', align: 'center', sortable: true },
  { name: 'male', label: 'M', field: 'male', align: 'center', sortable: true },
  { name: 'female', label: 'F', field: 'female', align: 'center', sortable: true },
  { name: 'official', label: 'Official', field: 'official', align: 'center', sortable: true },
  { name: 'non_official', label: 'Non-Official', field: 'non_official', align: 'center', sortable: true },
];

const admissionRows = computed(() => {
  if (!wardState.value) return [];
  // Combine new admissions and transfers
  const allAdmissions = [
    ...wardState.value.admissions.map(a => ({ ...a, is_transfer: false })),
    ...wardState.value.transfers_in.map(t => ({ ...t, is_transfer: true })),
  ];
  return allAdmissions;
});

const dischargeRows = computed(() => {
  if (!wardState.value) return [];
  return wardState.value.discharges || [];
});

const deathRows = computed(() => {
  if (!wardState.value) return [];
  return wardState.value.deaths || [];
});

const loadWardState = async () => {
  if (!selectedWard.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a ward',
    });
    return;
  }

  loading.value = true;
  try {
    const response = await consultationAPI.getDailyWardState(selectedWard.value, selectedDate.value);
    wardState.value = response.data;
  } catch (error) {
    console.error('Error loading ward state:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load ward state',
    });
    wardState.value = null;
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

onMounted(() => {
  // Auto-load if ward is pre-selected from query params
  if (route.query.ward) {
    selectedWard.value = route.query.ward;
    loadWardState();
  }
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

