<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h4 text-weight-bold glass-text">
        Blood Transfusion Requests - Lab Management
      </div>
      <q-space />
      <q-btn
        v-if="authStore.userRole === 'Admin' || authStore.userRole === 'Lab Head'"
        color="primary"
        icon="add"
        label="Add Processing Fee Service"
        @click="openAddServiceDialog"
        class="q-mr-md"
      />
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

          <template v-slot:body-cell-blood_type="props">
            <q-td :props="props" class="text-center">
              <q-badge
                v-if="props.value"
                color="red"
                text-color="white"
                :label="props.value"
                class="text-weight-bold"
                style="font-size: 16px; padding: 8px 16px; min-width: 50px;"
              />
              <q-badge
                v-else
                color="orange"
                text-color="white"
                label="Not Set"
                class="text-caption"
                style="padding: 6px 12px;"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  v-if="props.row.status === 'pending'"
                  flat
                  dense
                  icon="edit"
                  color="primary"
                  label="Edit"
                  size="sm"
                  @click="editRequest(props.row)"
                  :loading="processingId === props.row.id"
                />
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

    <!-- Add Processing Fee Dialog -->
    <q-dialog v-model="showAddServiceDialog">
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6">Add Processing Fee to Bill</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            Select a blood transfusion request to add the processing fee to the encounter/IPD clinical review bill
          </div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addProcessingFee" class="q-gutter-md">
            <div class="text-subtitle2 q-mb-sm">Select Blood Transfusion Request:</div>
            <q-select
              v-model="selectedRequestId"
              filled
              :options="requestsForProcessingFee"
              option-label="label"
              option-value="value"
              label="Blood Transfusion Request *"
              :rules="[(val) => !!val || 'Please select a blood transfusion request']"
              emit-value
              map-options
              hint="Select the request to add processing fee to its encounter/IPD bill"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption>
                      {{ scope.opt.details }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No blood transfusion requests available. Processing fee can only be added for existing requests.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-banner v-if="selectedRequestInfo" class="bg-blue-1 q-mt-md">
              <template v-slot:avatar>
                <q-icon name="info" color="primary" />
              </template>
              <div class="text-body2">
                <strong>Request Details:</strong><br>
                Patient: {{ selectedRequestInfo.patient_name }}<br>
                Transfusion Type: {{ selectedRequestInfo.transfusion_type_name }}<br>
                Blood Type: {{ selectedRequestInfo.blood_type || 'Not specified' }}<br>
                Quantity: {{ selectedRequestInfo.quantity }}<br>
                Ward: {{ selectedRequestInfo.ward }}<br>
                Status: {{ selectedRequestInfo.status.toUpperCase() }}
              </div>
            </q-banner>
            
            <q-select
              v-if="selectedRequestId"
              v-model="selectedService"
              filled
              :options="filteredServiceOptions"
              option-label="service_name"
              :option-value="(item) => item"
              label="Select Processing Fee Service *"
              :loading="loadingServices"
              :rules="[(val) => !!val || 'Please select a processing fee service']"
              use-input
              input-debounce="300"
              @filter="filterServices"
              clearable
              hint="Search for services in Transfusion Medicine Unit"
              emit-value
              map-options
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                    <q-item-label caption>G-DRG: {{ scope.opt.g_drg_code }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No services found. Try a different search term.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-banner class="bg-amber-1 q-mt-md">
              <template v-slot:avatar>
                <q-icon name="warning" color="amber" />
              </template>
              <div class="text-body2">
                The processing fee will be added as a bill item to the encounter/IPD clinical review that led to this blood request. 
                Select the appropriate processing fee service from the price list.
              </div>
            </q-banner>
            
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Add Processing Fee to Bill"
                type="submit"
                color="primary"
                class="col"
                :loading="addingService"
                :disable="!selectedRequestId || !selectedService"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

const $q = useQuasar();

const loading = ref(false);
const requests = ref([]);
const statusFilter = ref(null);
const wardFilter = ref('');
const searchTerm = ref('');
const processingId = ref(null);

// Add Processing Fee Dialog
const showAddServiceDialog = ref(false);
const addingService = ref(false);
const selectedRequestId = ref(null);
const selectedService = ref(null);
const loadingServices = ref(false);
const allServiceOptions = ref([]);
const filteredServiceOptions = ref([]);

// Edit Request Dialog
const showEditDialog = ref(false);
const updating = ref(false);
const editingRequest = ref(null);
const transfusionTypes = ref([]);
const editForm = ref({
  transfusion_type_id: null,
  blood_type: null,
  quantity: 1.0,
  request_reason: '',
});

const bloodTypeOptions = [
  { label: 'A+', value: 'A+' },
  { label: 'A-', value: 'A-' },
  { label: 'B+', value: 'B+' },
  { label: 'B-', value: 'B-' },
  { label: 'AB+', value: 'AB+' },
  { label: 'AB-', value: 'AB-' },
  { label: 'O+', value: 'O+' },
  { label: 'O-', value: 'O-' },
];

const transfusionTypeOptions = computed(() => {
  return transfusionTypes.value
    .filter(type => type.is_active)
    .map(type => ({
      label: type.type_name,
      value: type.id,
      price: type.unit_price,
      unit_type: type.unit_type,
    }));
});

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
    label: 'Transfusion Type',
    align: 'left',
    field: 'transfusion_type_name',
    sortable: true,
  },
  {
    name: 'blood_type',
    label: 'Blood Type',
    align: 'center',
    field: 'blood_type',
    sortable: true,
    headerStyle: 'font-weight: bold; background-color: rgba(244, 67, 54, 0.1);',
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

// Requests available for adding processing fee (all requests)
const requestsForProcessingFee = computed(() => {
  return requests.value.map(req => ({
    label: `${req.patient_name} (${req.transfusion_type_name} - ${req.quantity} units)`,
    value: req.id,
    details: `Card: ${req.patient_card_number || 'N/A'} | Ward: ${req.ward || 'N/A'} | Status: ${req.status.toUpperCase()} | Requested: ${formatDateTime(req.requested_at)}`
  }));
});

// Selected request info for display
const selectedRequestInfo = computed(() => {
  if (!selectedRequestId.value) return null;
  return requests.value.find(req => req.id === selectedRequestId.value);
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

const loadTransfusionTypes = async () => {
  try {
    const response = await consultationAPI.getBloodTransfusionTypes(true);
    transfusionTypes.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading transfusion types:', error);
  }
};

const editRequest = (request) => {
  editingRequest.value = request;
  editForm.value = {
    transfusion_type_id: request.transfusion_type_id,
    blood_type: request.blood_type,
    quantity: request.quantity,
    request_reason: request.request_reason || '',
  };
  showEditDialog.value = true;
  // Load transfusion types if not already loaded
  if (transfusionTypes.value.length === 0) {
    loadTransfusionTypes();
  }
};

const updateRequest = async () => {
  if (!editForm.value.transfusion_type_id || !editForm.value.blood_type || !editForm.value.quantity) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all required fields',
    });
    return;
  }

  if (!editingRequest.value) {
    return;
  }

  updating.value = true;
  try {
    const updateData = {
      transfusion_type_id: editForm.value.transfusion_type_id,
      blood_type: editForm.value.blood_type,
      quantity: editForm.value.quantity,
      request_reason: editForm.value.request_reason || null,
    };
    
    await consultationAPI.updateBloodTransfusionRequest(editingRequest.value.id, updateData);
    
    $q.notify({
      type: 'positive',
      message: 'Blood transfusion request updated successfully',
    });
    
    showEditDialog.value = false;
    editingRequest.value = null;
    await loadRequests();
  } catch (error) {
    console.error('Error updating request:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update blood request',
    });
  } finally {
    updating.value = false;
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

const openAddServiceDialog = async () => {
  selectedRequestId.value = null;
  selectedService.value = null;
  showAddServiceDialog.value = true;
  // Load services when dialog opens
  await loadServices();
};

// Load services for Transfusion Medicine Unit
const loadServices = async () => {
  loadingServices.value = true;
  try {
    const serviceTypeKeywords = ['Transfusion Medicine Unit', 'Transfusion Medicine', 'Transfusion', 'Blood Transfusion'];
    let services = [];
    
    // Try direct service type queries
    for (const serviceType of serviceTypeKeywords) {
      try {
        const response = await priceListAPI.getProceduresByServiceType(serviceType);
        if (response.data && Array.isArray(response.data) && response.data.length > 0) {
          services = services.concat(response.data);
        }
      } catch (e) {
        // Continue if this service type doesn't exist
      }
    }
    
    // Remove duplicates
    const seen = new Set();
    services = services.filter(service => {
      const uniqueKey = `${service.g_drg_code || 'no_code'}_${service.service_name || 'no_name'}`;
      if (seen.has(uniqueKey)) return false;
      seen.add(uniqueKey);
      return true;
    });
    
    allServiceOptions.value = services;
    filteredServiceOptions.value = services;
    
    if (services.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No services found for Transfusion Medicine Unit. Please ensure services are added to the price list.',
        timeout: 5000,
      });
    }
  } catch (error) {
    console.error('Failed to load services:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load services',
    });
  } finally {
    loadingServices.value = false;
  }
};

// Filter services for the dropdown
const filterServices = (val, update) => {
  if (val === '') {
    update(() => {
      filteredServiceOptions.value = allServiceOptions.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    filteredServiceOptions.value = allServiceOptions.value.filter(
      (service) =>
        (service.service_name && service.service_name.toLowerCase().includes(needle)) ||
        (service.g_drg_code && service.g_drg_code.toLowerCase().includes(needle))
    );
  });
};

// Watch for request selection to reset service selection
watch(selectedRequestId, (newVal) => {
  if (newVal) {
    selectedService.value = null;
  }
});

const addProcessingFee = async () => {
  if (!selectedRequestId.value) {
    $q.notify({
      type: 'negative',
      message: 'Please select a blood transfusion request',
    });
    return;
  }
  
  if (!selectedService.value) {
    $q.notify({
      type: 'negative',
      message: 'Please select a processing fee service',
    });
    return;
  }
  
  addingService.value = true;
  try {
    const serviceData = {
      g_drg_code: selectedService.value.g_drg_code,
      service_name: selectedService.value.service_name,
    };
    
    const response = await consultationAPI.addProcessingFeeToBloodRequest(selectedRequestId.value, serviceData);
    
    $q.notify({
      type: 'positive',
      message: response.data?.message || 'Processing fee added to bill successfully',
      caption: `Bill: ${response.data?.bill_number || 'N/A'} | Amount: GHS ${(response.data?.total_price || 0).toFixed(2)}`,
      timeout: 5000,
    });
    
    showAddServiceDialog.value = false;
    selectedRequestId.value = null;
    selectedService.value = null;
    
    // Reload requests to refresh data
    await loadRequests();
  } catch (error) {
    console.error('Error adding processing fee:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add processing fee to bill',
      timeout: 5000,
    });
  } finally {
    addingService.value = false;
  }
};

onMounted(() => {
  loadRequests();
  loadTransfusionTypes();
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

