<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back"
        @click="$router.back()"
        class="q-mr-md"
      />
      <div>
        <div class="text-h4 text-weight-bold glass-text">
          Blood Transfusion Request
        </div>
        <div v-if="patientInfo?.card_number" class="text-subtitle1 text-grey-4 q-mt-xs">
          Card Number: <span class="text-weight-bold">{{ patientInfo.card_number }}</span>
        </div>
      </div>
    </div>

    <!-- Patient Info Card -->
    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-sm">
          <q-icon name="person" color="primary" class="q-mr-sm" />
          Patient Information
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1 text-weight-bold">{{ patientInfo.patient_name }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Card Number</div>
            <div class="text-body1 text-weight-bold text-primary">{{ patientInfo.card_number }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Ward</div>
            <div class="text-body1 text-weight-bold">{{ patientInfo.ward }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Blood Requests</div>
            <div class="text-body1 text-weight-bold text-positive">{{ bloodRequests.length }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Request Blood Form -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="bloodtype" color="red" class="q-mr-sm" />
          Request Blood Transfusion
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="requestForm.transfusion_type_id"
              :options="transfusionTypeOptions"
              filled
              label="Blood Type *"
              hint="Select type of blood transfusion"
              :rules="[val => !!val || 'Blood type is required']"
              emit-value
              map-options
              option-label="label"
              option-value="value"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption>
                      Price: GHS {{ scope.opt.price?.toFixed(2) || '0.00' }} / {{ scope.opt.unit_type }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model.number="requestForm.quantity"
              filled
              type="number"
              step="0.1"
              min="0.1"
              label="Quantity *"
              hint="Number of units requested"
              :rules="[
                val => !!val || 'Quantity is required',
                val => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
          </div>
          <div class="col-12">
            <q-input
              v-model="requestForm.request_reason"
              filled
              type="textarea"
              label="Request Reason (optional)"
              hint="Reason for blood transfusion request"
              rows="3"
            />
          </div>
          <div class="col-12 flex items-end q-gutter-sm">
            <q-btn
              flat
              icon="send"
              label="Submit Request"
              color="red"
              @click="submitRequest"
              :loading="submitting"
              :disable="!requestForm.transfusion_type_id || !requestForm.quantity"
            />
            <q-btn
              flat
              icon="refresh"
              label="Clear"
              color="grey"
              @click="clearForm"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Blood Requests History -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            Blood Requests History ({{ bloodRequests.length }})
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Refresh"
            color="primary"
            @click="loadBloodRequests"
            :loading="loading"
          />
        </div>
        <q-table
          :rows="bloodRequests"
          :columns="columns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          :rows-per-page-options="[10, 20, 50]"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
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
                  icon="cancel"
                  color="negative"
                  label="Cancel"
                  size="sm"
                  @click="cancelRequest(props.row)"
                  :loading="processingId === props.row.id"
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
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);

const patientInfo = ref(null);
const bloodRequests = ref([]);
const loading = ref(false);
const submitting = ref(false);
const processingId = ref(null);
const transfusionTypes = ref([]);

const requestForm = ref({
  transfusion_type_id: null,
  quantity: 1.0,
  request_reason: '',
});

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

const columns = [
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
    name: 'requested_at',
    label: 'Requested At',
    align: 'left',
    field: 'requested_at',
    format: (val) => formatDateTime(val),
    sortable: true,
  },
  {
    name: 'request_reason',
    label: 'Reason',
    align: 'left',
    field: 'request_reason',
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

const getStatusColor = (status) => {
  const colors = {
    pending: 'orange',
    accepted: 'blue',
    fulfilled: 'positive',
    returned: 'info',
    cancelled: 'negative',
  };
  return colors[status] || 'grey';
};

const loadPatientInfo = async () => {
  try {
    const response = await consultationAPI.getWardAdmission(wardAdmissionId.value);
    const admission = response.data;
    
    if (admission) {
      patientInfo.value = {
        patient_name: `${admission.patient_name || ''} ${admission.patient_surname || ''} ${admission.patient_other_names || ''}`.trim(),
        card_number: admission.patient_card_number,
        ward: admission.ward,
      };
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
  }
};

const loadTransfusionTypes = async () => {
  try {
    const response = await consultationAPI.getBloodTransfusionTypes(true);
    transfusionTypes.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading transfusion types:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load blood transfusion types',
    });
  }
};

const loadBloodRequests = async () => {
  if (!encounterId.value) return;
  
  loading.value = true;
  try {
    // Get all requests for this ward admission
    const response = await consultationAPI.getBloodTransfusionRequests();
    const allRequests = Array.isArray(response.data) ? response.data : [];
    bloodRequests.value = allRequests.filter(req => req.ward_admission_id === wardAdmissionId.value);
  } catch (error) {
    console.error('Error loading blood requests:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load blood requests',
    });
  } finally {
    loading.value = false;
  }
};

const submitRequest = async () => {
  if (!requestForm.value.transfusion_type_id || !requestForm.value.quantity) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all required fields',
    });
    return;
  }

  if (!encounterId.value) {
    $q.notify({
      type: 'negative',
      message: 'Encounter ID is missing',
    });
    return;
  }

  submitting.value = true;
  try {
    await consultationAPI.createBloodTransfusionRequest({
      ward_admission_id: wardAdmissionId.value,
      encounter_id: encounterId.value,
      transfusion_type_id: requestForm.value.transfusion_type_id,
      quantity: requestForm.value.quantity,
      request_reason: requestForm.value.request_reason || null,
    });
    
    $q.notify({
      type: 'positive',
      message: 'Blood transfusion request submitted successfully',
    });
    
    clearForm();
    await loadBloodRequests();
  } catch (error) {
    console.error('Error submitting request:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to submit blood request',
    });
  } finally {
    submitting.value = false;
  }
};

const clearForm = () => {
  requestForm.value = {
    transfusion_type_id: null,
    quantity: 1.0,
    request_reason: '',
  };
};

const cancelRequest = async (request) => {
  $q.dialog({
    title: 'Cancel Blood Request',
    message: `Cancel blood request for ${request.transfusion_type_name}?`,
    prompt: {
      model: '',
      type: 'text',
      label: 'Cancellation reason (optional)',
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    processingId.value = request.id;
    try {
      await consultationAPI.cancelBloodTransfusionRequest(request.id, reason || null);
      $q.notify({
        type: 'positive',
        message: 'Blood request cancelled successfully',
      });
      await loadBloodRequests();
    } catch (error) {
      console.error('Error cancelling request:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to cancel blood request',
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

onMounted(async () => {
  await loadPatientInfo();
  await loadTransfusionTypes();
  await loadBloodRequests();
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

