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
        Admission & Discharge Registers
      </div>
    </div>

    <!-- Filters -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4 col-lg-3">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
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
          <div class="col-12 col-md-4 col-lg-3">
            <q-select
              v-model="statusFilter"
              :options="statusOptions"
              filled
              label="Filter by Status"
              emit-value
              map-options
              @update:model-value="onStatusFilterChange"
            >
              <template v-slot:prepend>
                <q-icon name="filter_list" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4 col-lg-6">
            <q-input
              v-model="searchTerm"
              filled
              label="Search by Card Number or Name"
              @update:model-value="onSearchChange"
            >
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
              <template v-slot:append>
                <q-btn
                  v-if="searchTerm"
                  flat
                  dense
                  icon="clear"
                  @click="searchTerm = ''; onSearchChange()"
                />
              </template>
            </q-input>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Tabs for Admissions and Discharges -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <q-tabs v-model="activeTab" class="text-primary" align="left">
          <q-tab name="admissions" label="Admissions" icon="person_add" />
          <q-tab name="discharges" label="Discharges" icon="exit_to_app" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="activeTab" animated>
          <!-- Admissions Tab -->
          <q-tab-panel name="admissions">
            <div class="text-h6 glass-text q-mb-md">
              Admission Register ({{ filteredAdmissions.length }})
            </div>
            <q-table
              :rows="filteredAdmissions"
              :columns="admissionColumns"
              row-key="id"
              flat
              :loading="loading"
              :filter="searchTerm"
              @request="onRequest"
              :pagination="pagination"
              class="glass-table"
            >
              <template v-slot:body-cell-patient="props">
                <q-td :props="props">
                  <div class="text-weight-bold glass-text">
                    {{ props.row.patient_name }} {{ props.row.patient_surname }}
                    <span v-if="props.row.patient_other_names">{{ props.row.patient_other_names }}</span>
                  </div>
                  <div class="text-caption text-secondary">
                    {{ props.row.patient_card_number }}
                  </div>
                </q-td>
              </template>

              <template v-slot:body-cell-ward="props">
                <q-td :props="props">
                  <q-badge color="primary" :label="props.value" />
                </q-td>
              </template>

              <template v-slot:body-cell-admitted_at="props">
                <q-td :props="props">
                  {{ formatDateTime(props.value) }}
                </q-td>
              </template>

              <template v-slot:body-cell-admitted_by="props">
                <q-td :props="props">
                  <div v-if="props.row.admitted_by_name">
                    {{ props.row.admitted_by_name }}
                    <span v-if="props.row.admitted_by_role" class="text-caption text-secondary">
                      ({{ props.row.admitted_by_role }})
                    </span>
                  </div>
                  <span v-else class="text-secondary">N/A</span>
                </q-td>
              </template>

              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    flat
                    dense
                    icon="visibility"
                    label="View"
                    color="primary"
                    size="sm"
                    @click="viewAdmission(props.row)"
                  />
                </q-td>
              </template>
            </q-table>
          </q-tab-panel>

          <!-- Discharges Tab -->
          <q-tab-panel name="discharges">
            <div class="text-h6 glass-text q-mb-md">
              Discharge Register ({{ filteredDischarges.length }})
            </div>
            <q-table
              :rows="filteredDischarges"
              :columns="dischargeColumns"
              row-key="id"
              flat
              :loading="loading"
              :filter="searchTerm"
              @request="onRequest"
              :pagination="pagination"
              class="glass-table"
            >
              <template v-slot:body-cell-patient="props">
                <q-td :props="props">
                  <div class="text-weight-bold glass-text">
                    {{ props.row.patient_name }} {{ props.row.patient_surname }}
                    <span v-if="props.row.patient_other_names">{{ props.row.patient_other_names }}</span>
                  </div>
                  <div class="text-caption text-secondary">
                    {{ props.row.patient_card_number }}
                  </div>
                </q-td>
              </template>

              <template v-slot:body-cell-ward="props">
                <q-td :props="props">
                  <q-badge color="primary" :label="props.value" />
                </q-td>
              </template>

              <template v-slot:body-cell-admitted_at="props">
                <q-td :props="props">
                  {{ formatDateTime(props.value) }}
                </q-td>
              </template>

              <template v-slot:body-cell-discharged_at="props">
                <q-td :props="props">
                  {{ formatDateTime(props.value) }}
                </q-td>
              </template>

              <template v-slot:body-cell-discharged_by="props">
                <q-td :props="props">
                  <div v-if="props.row.discharged_by_name">
                    {{ props.row.discharged_by_name }}
                    <span v-if="props.row.discharged_by_role" class="text-caption text-secondary">
                      ({{ props.row.discharged_by_role }})
                    </span>
                  </div>
                  <span v-else class="text-secondary">N/A</span>
                </q-td>
              </template>

              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    flat
                    dense
                    icon="visibility"
                    label="View"
                    color="primary"
                    size="sm"
                    @click="viewDischarge(props.row)"
                  />
                </q-td>
              </template>
            </q-table>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
    </q-card>

    <!-- View Admission/Discharge Dialog -->
    <q-dialog v-model="showViewDialog" persistent>
      <q-card style="min-width: 600px; max-width: 800px;">
        <q-card-section>
          <div class="text-h6 glass-text">
            {{ viewingRecord?.patient_name }} {{ viewingRecord?.patient_surname }}
          </div>
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-body2 text-secondary">Card Number</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>{{ viewingRecord?.patient_card_number }}</strong>
              </div>
              <div class="text-body2 text-secondary">Ward</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>{{ viewingRecord?.ward }}</strong>
              </div>
              <div class="text-body2 text-secondary">Admitted At</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>{{ formatDateTime(viewingRecord?.admitted_at) }}</strong>
              </div>
              <div class="text-body2 text-secondary">Admitted By</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>
                  {{ viewingRecord?.admitted_by_name || 'N/A' }}
                  <span v-if="viewingRecord?.admitted_by_role"> ({{ viewingRecord.admitted_by_role }})</span>
                </strong>
              </div>
            </div>
            <div class="col-12 col-md-6" v-if="viewingRecord?.discharged_at">
              <div class="text-body2 text-secondary">Discharged At</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>{{ formatDateTime(viewingRecord.discharged_at) }}</strong>
              </div>
              <div class="text-body2 text-secondary">Discharged By</div>
              <div class="text-body1 glass-text q-mb-md">
                <strong>
                  {{ viewingRecord.discharged_by_name || 'N/A' }}
                  <span v-if="viewingRecord.discharged_by_role"> ({{ viewingRecord.discharged_by_role }})</span>
                </strong>
              </div>
            </div>
            <div class="col-12" v-if="viewingRecord?.admission_notes">
              <div class="text-body2 text-secondary">Admission Notes</div>
              <div class="text-body1 glass-text q-mb-md" style="white-space: pre-wrap;">
                {{ viewingRecord.admission_notes }}
              </div>
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" @click="showViewDialog = false" />
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
const activeTab = ref('admissions');
const allRecords = ref([]);
const selectedWard = ref(null);
const statusFilter = ref('all');
const searchTerm = ref('');
const showViewDialog = ref(false);
const viewingRecord = ref(null);

const statusOptions = [
  { label: 'All', value: 'all' },
  { label: 'Active (Admitted)', value: 'active' },
  { label: 'Discharged', value: 'discharged' },
];

const wardOptions = computed(() => {
  const wards = new Set();
  allRecords.value.forEach(record => {
    if (record.ward) {
      wards.add(record.ward);
    }
  });
  return Array.from(wards).sort().map(ward => ({
    label: ward,
    value: ward
  }));
});

const filteredAdmissions = computed(() => {
  let filtered = [...allRecords.value];
  
  // Filter by ward
  if (selectedWard.value) {
    filtered = filtered.filter(record => record.ward === selectedWard.value);
  }
  
  // Filter by status
  if (statusFilter.value === 'active') {
    filtered = filtered.filter(record => !record.discharged_at);
  } else if (statusFilter.value === 'discharged') {
    filtered = filtered.filter(record => record.discharged_at);
  }
  
  // Filter by search
  if (searchTerm.value) {
    const term = searchTerm.value.toLowerCase();
    filtered = filtered.filter(record => {
      const cardNumber = record.patient_card_number?.toLowerCase() || '';
      const name = `${record.patient_name || ''} ${record.patient_surname || ''}`.toLowerCase();
      return cardNumber.includes(term) || name.includes(term);
    });
  }
  
  // Sort by admitted_at descending
  return filtered.sort((a, b) => {
    const dateA = new Date(a.admitted_at);
    const dateB = new Date(b.admitted_at);
    return dateB - dateA;
  });
});

const filteredDischarges = computed(() => {
  // Only show discharged records
  return filteredAdmissions.value.filter(record => record.discharged_at);
});

const admissionColumns = [
  {
    name: 'patient',
    required: true,
    label: 'Patient',
    align: 'left',
    field: 'patient',
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
    name: 'admitted_at',
    label: 'Admitted At',
    align: 'center',
    field: 'admitted_at',
    sortable: true,
  },
  {
    name: 'admitted_by',
    label: 'Admitted By',
    align: 'center',
    field: 'admitted_by',
    sortable: false,
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center',
    field: 'actions',
    sortable: false,
  },
];

const dischargeColumns = [
  {
    name: 'patient',
    required: true,
    label: 'Patient',
    align: 'left',
    field: 'patient',
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
    name: 'admitted_at',
    label: 'Admitted At',
    align: 'center',
    field: 'admitted_at',
    sortable: true,
  },
  {
    name: 'discharged_at',
    label: 'Discharged At',
    align: 'center',
    field: 'discharged_at',
    sortable: true,
  },
  {
    name: 'discharged_by',
    label: 'Discharged By',
    align: 'center',
    field: 'discharged_by',
    sortable: false,
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center',
    field: 'actions',
    sortable: false,
  },
];

const pagination = ref({
  sortBy: 'admitted_at',
  descending: true,
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0,
});

const loadRecords = async () => {
  loading.value = true;
  try {
    // Load all records including discharged
    const response = await consultationAPI.getWardAdmissions(null, true);
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    allRecords.value = data;
    pagination.value.rowsNumber = filteredAdmissions.value.length;
  } catch (error) {
    console.error('Error loading records:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load records',
    });
    allRecords.value = [];
  } finally {
    loading.value = false;
  }
};

const onWardFilterChange = () => {
  pagination.value.rowsNumber = filteredAdmissions.value.length;
  pagination.value.page = 1;
};

const onStatusFilterChange = () => {
  pagination.value.rowsNumber = filteredAdmissions.value.length;
  pagination.value.page = 1;
};

const onSearchChange = () => {
  pagination.value.rowsNumber = filteredAdmissions.value.length;
  pagination.value.page = 1;
};

const viewAdmission = (record) => {
  viewingRecord.value = record;
  showViewDialog.value = true;
};

const viewDischarge = (record) => {
  viewingRecord.value = record;
  showViewDialog.value = true;
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

const onRequest = (props) => {
  const { page, rowsPerPage, sortBy, descending } = props.pagination;
  pagination.value.page = page;
  pagination.value.rowsPerPage = rowsPerPage;
  pagination.value.sortBy = sortBy;
  pagination.value.descending = descending;
};

onMounted(() => {
  loadRecords();
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

