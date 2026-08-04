<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Inventory debits"
      subtitle="Review inpatient and companion inventory debits, filter by ward or status, and release items for ward administration."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/inventory-mode')">Back</HmsButton>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadInventoryDebits">
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Ward, release status, dates, user, and item</div>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-md-3">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
              dense
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
          <div class="col-12 col-md-3">
            <q-select
              v-model="releaseStatusFilter"
              :options="releaseStatusOptions"
              filled
              dense
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
          <div class="col-12 col-md-3">
            <q-input
              v-model="startDate"
              filled
              dense
              label="Start Date"
              type="date"
              clearable
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="event" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-3">
            <q-input
              v-model="endDate"
              filled
              dense
              label="End Date"
              type="date"
              clearable
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="event" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-3">
            <q-input
              v-model="userNameFilter"
              filled
              dense
              label="Filter by Full Name"
              clearable
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="person" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-3">
            <q-input
              v-model="itemFilter"
              filled
              dense
              label="Filter by Item (Code/Name)"
              clearable
              @update:model-value="loadInventoryDebits"
            >
              <template v-slot:prepend>
                <q-icon name="inventory" />
              </template>
            </q-input>
          </div>
        </div>
      </div>
    </section>

    <div class="claim-kpi-grid">
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Total inventory debits</div>
        </div>
        <div class="claim-kpi__value">{{ inventoryDebits.length }}</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Pending release</div>
        </div>
        <div class="claim-kpi__value text-warning">{{ pendingReleaseCount }}</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Released</div>
        </div>
        <div class="claim-kpi__value text-positive">{{ releasedCount }}</div>
      </div>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Inventory debits</div>
          <div class="panel-sub">{{ filteredDebits.length }} matching row(s)</div>
        </div>
      </div>
      <div class="panel-body table-wrap">
        <q-table
          class="diag-table"
          :rows="filteredDebits"
          :columns="columns"
          :row-key="debitRowKey"
          :loading="loading"
          flat
          dense
          :rows-per-page-options="[15, 25, 50, 100]"
          :pagination="{ rowsPerPage: 15 }"
        >
          <template v-slot:body-cell-patient="props">
            <q-td :props="props">
              <div>
                <q-badge
                  v-if="props.row.debit_source === 'companion'"
                  color="secondary"
                  label="Companion"
                  class="q-mb-xs"
                />
                <div class="text-weight-medium">{{ props.row.patient_name || 'N/A' }}</div>
                <div class="text-caption text-grey-7">
                  Card: {{ props.row.patient_card_number || 'N/A' }}
                </div>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <div>
                <q-badge color="primary" :label="props.row.requesting_ward || props.value || 'N/A'" />
                <div v-if="props.row.requesting_ward && props.value && props.row.requesting_ward !== props.value" class="text-caption text-grey-7 q-mt-xs">
                  (Current: {{ props.value }})
                </div>
              </div>
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
      </div>
    </section>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI, wardsAPI } from '../services/api';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

const $q = useQuasar();

const loading = ref(false);
const inventoryDebits = ref([]);
const selectedWard = ref(null);
const releaseStatusFilter = ref(null);
const startDate = ref(null);
const endDate = ref(null);
const userNameFilter = ref(null);
const itemFilter = ref(null);
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
    label: 'Requesting Ward',
    field: 'requesting_ward',
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

function debitRowKey(row) {
  return row.row_key || `inpatient-${row.id}`;
}

const filteredDebits = computed(() => {
  let filtered = inventoryDebits.value;

  if (selectedWard.value) {
    filtered = filtered.filter(
      (d) => (d.requesting_ward || d.ward) === selectedWard.value
    );
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
    if (startDate.value) {
      params.start_date = startDate.value;
    }
    if (endDate.value) {
      params.end_date = endDate.value;
    }
    if (userNameFilter.value) {
      params.used_by_name = userNameFilter.value;
    }
    if (itemFilter.value) {
      // Filter by product name (backend will handle partial matching)
      params.product_name = itemFilter.value;
    }
    
    const response = await consultationAPI.getAllInventoryDebits(params);
    inventoryDebits.value = response.data || [];
    
    // Load wards from API first, then merge with any additional wards from debits
    try {
      const wardsResponse = await wardsAPI.getAll(true, 'ward'); // Get only active wards (department type = ward)
      const apiWards = (wardsResponse.data || []).map(ward => ward.name);
      const wards = new Set(apiWards);
      
      // Add any wards found in debits that might not be in the API (for backward compatibility)
      inventoryDebits.value.forEach(debit => {
        const ward = debit.requesting_ward || debit.ward;
        if (ward) {
          wards.add(ward);
        }
      });
      
      wardOptions.value = Array.from(wards).sort().map(ward => ({
        label: ward,
        value: ward
      }));
    } catch (error) {
      console.error('Error loading wards:', error);
      // Fallback to extracting wards from debits only
      const wards = new Set();
      inventoryDebits.value.forEach(debit => {
        const ward = debit.requesting_ward || debit.ward;
        if (ward) {
          wards.add(ward);
        }
      });
      wardOptions.value = Array.from(wards).sort().map(ward => ({
        label: ward,
        value: ward
      }));
    }
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
      await consultationAPI.releaseInventoryDebit(debit.id, {
        source: debit.debit_source || 'inpatient',
      });
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
.stat-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
</style>
