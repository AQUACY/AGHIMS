<template>
  <q-page class="q-pa-md">
    <div class="text-h4 text-weight-bold glass-text q-mb-md">
      Inventory Debit Management
    </div>

    <!-- Filters -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-md-4">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
              label="Filter by Ward"
              clearable
              emit-value
              map-options
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="local_hospital" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4">
            <q-select
              v-model="releaseStatusFilter"
              :options="releaseStatusOptions"
              filled
              label="Release Status"
              clearable
              emit-value
              map-options
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="filter_list" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4">
            <q-btn
              flat
              icon="refresh"
              label="Refresh"
              color="primary"
              @click="loadInventoryDebits"
              :loading="loading"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Summary Cards -->
    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-md-4">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-7">Total Inventory Debits</div>
            <div class="text-h5 text-weight-bold glass-text">{{ inventoryDebits.length }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-7">Pending Release</div>
            <div class="text-h5 text-weight-bold text-warning">{{ pendingReleaseCount }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-caption text-grey-7">Released</div>
            <div class="text-h5 text-weight-bold text-positive">{{ releasedCount }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Inventory Debits Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            Inventory Debits ({{ filteredDebits.length }})
          </div>
          <q-space />
        </div>

        <q-table
          :rows="filteredDebits"
          :columns="columns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          :rows-per-page-options="[15, 25, 50, 100]"
          :pagination="{ rowsPerPage: 15 }"
        >
          <template v-slot:body-cell-patient="props">
            <q-td :props="props">
              <div>
                <div class="text-weight-medium">{{ props.row.patient_name || 'N/A' }}</div>
                <div class="text-caption text-grey-7">
                  Card: {{ props.row.patient_card_number || 'N/A' }}
                </div>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <q-badge color="primary" :label="props.value || 'N/A'" />
            </q-td>
          </template>

          <template v-slot:body-cell-admission_period="props">
            <q-td :props="props">
              <div v-if="props.row.admitted_at">
                <div class="text-caption">
                  {{ formatDate(props.row.admitted_at) }}
                </div>
                <div class="text-caption text-grey-7">
                  {{ formatTime(props.row.admitted_at) }}
                </div>
              </div>
              <span v-else class="text-grey-6">N/A</span>
            </q-td>
          </template>

          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                v-if="props.row.is_released"
                color="positive"
                label="Released"
              />
              <q-badge
                v-else
                color="warning"
                label="Pending"
              />
              <q-chip
                v-if="props.row.is_billed"
                color="info"
                text-color="white"
                size="sm"
                label="Billed"
                class="q-ml-xs"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-released_info="props">
            <q-td :props="props">
              <div v-if="props.row.is_released">
                <div class="text-caption">
                  By: {{ props.row.released_by_name || 'N/A' }}
                </div>
                <div class="text-caption text-grey-7" v-if="props.row.released_at">
                  {{ formatDateTime(props.row.released_at) }}
                </div>
              </div>
              <span v-else class="text-grey-6">-</span>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!props.row.is_released"
                flat
                dense
                icon="check_circle"
                color="positive"
                label="Release"
                @click="releaseDebit(props.row)"
                :loading="releasingId === props.row.id"
                :disable="releasingId !== null"
              >
                <q-tooltip>Release inventory for ward administration</q-tooltip>
              </q-btn>
              <q-icon
                v-else
                name="check_circle"
                color="positive"
                size="24px"
              >
                <q-tooltip>Released by {{ props.row.released_by_name }} on {{ formatDateTime(props.row.released_at) }}</q-tooltip>
              </q-icon>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();

const loading = ref(false);
const inventoryDebits = ref([]);
const selectedWard = ref(null);
const releaseStatusFilter = ref(null);
const releasingId = ref(null);

const wardOptions = ref([]);
const releaseStatusOptions = [
  { label: 'Pending Release', value: false },
  { label: 'Released', value: true }
];

const columns = [
  {
    name: 'patient',
    label: 'Patient',
    field: 'patient_name',
    align: 'left',
    sortable: true
  },
  {
    name: 'ward',
    label: 'Ward',
    field: 'ward',
    align: 'center',
    sortable: true
  },
  {
    name: 'admission_period',
    label: 'Admission Period',
    field: 'admitted_at',
    align: 'left',
    sortable: true
  },
  {
    name: 'product_name',
    label: 'Product',
    field: 'product_name',
    align: 'left',
    sortable: true
  },
  {
    name: 'product_code',
    label: 'Code',
    field: 'product_code',
    align: 'left',
    sortable: true
  },
  {
    name: 'quantity',
    label: 'Quantity',
    field: 'quantity',
    align: 'center',
    sortable: true
  },
  {
    name: 'total_price',
    label: 'Total Price',
    field: 'total_price',
    align: 'right',
    format: val => `GHS ${val?.toFixed(2) || '0.00'}`,
    sortable: true
  },
  {
    name: 'used_by',
    label: 'Used By',
    field: 'used_by_name',
    align: 'left',
    sortable: true
  },
  {
    name: 'used_at',
    label: 'Used At',
    field: 'used_at',
    align: 'left',
    format: val => val ? new Date(val).toLocaleString() : '',
    sortable: true
  },
  {
    name: 'status',
    label: 'Status',
    field: 'is_released',
    align: 'center',
    sortable: true
  },
  {
    name: 'released_info',
    label: 'Release Info',
    field: 'released_by_name',
    align: 'left',
    sortable: false
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center'
  }
];

const pendingReleaseCount = computed(() => {
  return inventoryDebits.value.filter(d => !d.is_released).length;
});

const releasedCount = computed(() => {
  return inventoryDebits.value.filter(d => d.is_released).length;
});

const filteredDebits = computed(() => {
  let filtered = inventoryDebits.value;
  
  if (selectedWard.value) {
    filtered = filtered.filter(d => d.ward === selectedWard.value);
  }
  
  if (releaseStatusFilter.value !== null) {
    filtered = filtered.filter(d => d.is_released === releaseStatusFilter.value);
  }
  
  return filtered;
});

const loadInventoryDebits = async () => {
  loading.value = true;
  try {
    const params = {};
    if (selectedWard.value) {
      params.ward = selectedWard.value;
    }
    if (releaseStatusFilter.value !== null) {
      params.is_released = releaseStatusFilter.value;
    }
    
    const response = await consultationAPI.getAllInventoryDebits(params);
    inventoryDebits.value = response.data || [];
    
    // Extract unique wards for filter dropdown
    const wards = new Set();
    inventoryDebits.value.forEach(debit => {
      if (debit.ward) {
        wards.add(debit.ward);
      }
    });
    wardOptions.value = Array.from(wards).sort().map(ward => ({
      label: ward,
      value: ward
    }));
  } catch (error) {
    console.error('Error loading inventory debits:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load inventory debits',
      position: 'top'
    });
    inventoryDebits.value = [];
  } finally {
    loading.value = false;
  }
};

const releaseDebit = async (debit) => {
  $q.dialog({
    title: 'Confirm Release',
    message: `Are you sure you want to release "${debit.product_name}" (Qty: ${debit.quantity}) for ${debit.patient_name || 'patient'} in ${debit.ward || 'ward'}?`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Release',
      color: 'positive',
      flat: false
    }
  }).onOk(async () => {
    releasingId.value = debit.id;
    try {
      await consultationAPI.releaseInventoryDebit(debit.id);
      $q.notify({
        type: 'positive',
        message: 'Inventory released successfully',
        position: 'top'
      });
      await loadInventoryDebits();
    } catch (error) {
      console.error('Error releasing inventory debit:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to release inventory debit',
        position: 'top'
      });
    } finally {
      releasingId.value = null;
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString();
};

const formatTime = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleTimeString();
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
};

onMounted(() => {
  loadInventoryDebits();
});
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

