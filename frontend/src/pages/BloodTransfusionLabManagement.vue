<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h4 text-weight-bold glass-text">
        Blood Transfusion Requests - Lab Management
      </div>
      <q-space />
      <q-btn
        flat
        icon="refresh"
        label="Refresh"
        color="primary"
        @click="loadRequests"
        :loading="loading"
      />
    </div>

    <!-- Filters -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-select
              v-model="statusFilter"
              :options="statusOptions"
              filled
              label="Filter by Status"
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model="wardFilter"
              filled
              label="Filter by Ward"
              clearable
            />
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model="searchTerm"
              filled
              label="Search by Patient Card Number"
              clearable
            >
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Requests Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          Blood Requests ({{ filteredRequests.length }})
        </div>
        <q-table
          :rows="filteredRequests"
          :columns="columns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          :pagination="{ rowsPerPage: 20 }"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value.toUpperCase()"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-total_price="props">
            <q-td :props="props">
              <span class="text-weight-bold">GHS {{ props.value?.toFixed(2) || '0.00' }}</span>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  v-if="props.row.status === 'pending'"
                  flat
                  dense
                  icon="check_circle"
                  color="positive"
                  label="Accept"
                  size="sm"
                  @click="acceptRequest(props.row)"
                  :loading="processingId === props.row.id"
                />
                <q-btn
                  v-if="props.row.status === 'accepted'"
                  flat
                  dense
                  icon="done_all"
                  color="blue"
                  label="Fulfill"
                  size="sm"
                  @click="fulfillRequest(props.row)"
                  :loading="processingId === props.row.id"
                />
                <q-btn
                  v-if="(props.row.status === 'accepted' || props.row.status === 'fulfilled') && authStore.userRole === 'Admin'"
                  flat
                  dense
                  icon="undo"
                  color="info"
                  label="Return"
                  size="sm"
                  @click="returnRequest(props.row)"
                  :loading="processingId === props.row.id"
                />
                <q-btn
                  v-if="authStore.userRole === 'Admin' && (props.row.status === 'pending' || props.row.status === 'cancelled')"
                  flat
                  dense
                  icon="delete"
                  color="negative"
                  label="Delete"
                  size="sm"
                  @click="deleteRequest(props.row)"
                  :loading="processingId === props.row.id"
                />
                <q-chip
                  v-if="props.row.status === 'fulfilled' && authStore.userRole !== 'Admin'"
                  color="positive"
                  text-color="white"
                  icon="check_circle"
                  label="Fulfilled"
                />
                <q-chip
                  v-if="props.row.status === 'cancelled'"
                  color="grey"
                  text-color="white"
                  icon="cancel"
                  label="Cancelled"
                />
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

const $q = useQuasar();

const loading = ref(false);
const requests = ref([]);
const statusFilter = ref(null);
const wardFilter = ref('');
const searchTerm = ref('');
const processingId = ref(null);

const statusOptions = [
  { label: 'All', value: null },
  { label: 'Pending', value: 'pending' },
  { label: 'Accepted', value: 'accepted' },
  { label: 'Fulfilled', value: 'fulfilled' },
  { label: 'Returned', value: 'returned' },
  { label: 'Cancelled', value: 'cancelled' },
];

const columns = [
  {
    name: 'patient_name',
    label: 'Patient',
    align: 'left',
    field: 'patient_name',
    sortable: true,
  },
  {
    name: 'patient_card_number',
    label: 'Card Number',
    align: 'left',
    field: 'patient_card_number',
    sortable: true,
  },
  {
    name: 'ward',
    label: 'Ward',
    align: 'center',
    field: 'ward',
    sortable: true,
  },
  {
    name: 'transfusion_type_name',
    label: 'Blood Type',
    align: 'left',
    field: 'transfusion_type_name',
    sortable: true,
  },
  {
    name: 'quantity',
    label: 'Quantity',
    align: 'center',
    field: 'quantity',
    sortable: true,
  },
  {
    name: 'status',
    label: 'Status',
    align: 'center',
    field: 'status',
    sortable: true,
  },
  {
    name: 'total_price',
    label: 'Total Price',
    align: 'right',
    field: 'total_price',
    sortable: true,
  },
  {
    name: 'requested_by_name',
    label: 'Requested By',
    align: 'left',
    field: 'requested_by_name',
    sortable: false,
  },
  {
    name: 'requested_at',
    label: 'Requested At',
    align: 'left',
    field: 'requested_at',
    format: (val) => formatDateTime(val),
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

const filteredRequests = computed(() => {
  let filtered = [...requests.value];
  
  if (statusFilter.value) {
    filtered = filtered.filter(req => req.status === statusFilter.value);
  }
  
  if (wardFilter.value) {
    const ward = wardFilter.value.toLowerCase();
    filtered = filtered.filter(req => req.ward?.toLowerCase().includes(ward));
  }
  
  if (searchTerm.value) {
    const term = searchTerm.value.toLowerCase();
    filtered = filtered.filter(req => 
      req.patient_card_number?.toLowerCase().includes(term) ||
      req.patient_name?.toLowerCase().includes(term)
    );
  }
  
  return filtered;
});

const getStatusColor = (status) => {
  const colors = {
    pending: 'orange',
    accepted: 'blue',
    fulfilled: 'positive',
    returned: 'info',
    cancelled: 'grey',
  };
  return colors[status] || 'grey';
};

const loadRequests = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getBloodTransfusionRequests();
    requests.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading requests:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load blood transfusion requests',
    });
  } finally {
    loading.value = false;
  }
};

const acceptRequest = async (request) => {
  $q.dialog({
    title: 'Accept Blood Request',
    message: `Accept blood request for ${request.patient_name}? This will create a bill item.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    processingId.value = request.id;
    try {
      await consultationAPI.acceptBloodTransfusionRequest(request.id);
      $q.notify({
        type: 'positive',
        message: 'Blood request accepted successfully. Bill item created.',
      });
      await loadRequests();
    } catch (error) {
      console.error('Error accepting request:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to accept blood request',
      });
    } finally {
      processingId.value = null;
    }
  });
};

const fulfillRequest = async (request) => {
  $q.dialog({
    title: 'Fulfill Blood Request',
    message: `Mark blood request as fulfilled for ${request.patient_name}?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    processingId.value = request.id;
    try {
      await consultationAPI.fulfillBloodTransfusionRequest(request.id);
      $q.notify({
        type: 'positive',
        message: 'Blood request marked as fulfilled',
      });
      await loadRequests();
    } catch (error) {
      console.error('Error fulfilling request:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to fulfill blood request',
      });
    } finally {
      processingId.value = null;
    }
  });
};

const returnRequest = async (request) => {
  $q.dialog({
    title: 'Return Blood',
    message: `Return blood for ${request.patient_name}? This will create a credit bill item and reduce the total bill amount. The request will be set back to pending status so it can be accepted again if needed.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    processingId.value = request.id;
    try {
      await consultationAPI.returnBloodTransfusionRequest(request.id);
      $q.notify({
        type: 'positive',
        message: 'Blood returned successfully. Bill has been credited. Request is now pending and can be accepted again.',
      });
      await loadRequests();
    } catch (error) {
      console.error('Error returning blood:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to return blood',
      });
    } finally {
      processingId.value = null;
    }
  });
};

const deleteRequest = async (request) => {
  $q.dialog({
    title: 'Delete Blood Request',
    message: `Permanently delete blood request for ${request.patient_name}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    processingId.value = request.id;
    try {
      await consultationAPI.deleteBloodTransfusionRequest(request.id);
      $q.notify({
        type: 'positive',
        message: 'Blood request deleted successfully',
      });
      await loadRequests();
    } catch (error) {
      console.error('Error deleting request:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete blood request',
      });
    } finally {
      processingId.value = null;
    }
  });
};

const formatDateTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

onMounted(() => {
  loadRequests();
});
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-table {
  background: transparent;
}
</style>

