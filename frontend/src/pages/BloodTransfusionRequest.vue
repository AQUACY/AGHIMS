<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Blood transfusion request"
      subtitle="Request and track blood products for this admission."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="patientInfo" class="ipd-patient-hero">
      <div class="ipd-hero-main">
        <div class="ipd-hero-avatar">{{ btrPatientInitials(patientInfo) }}</div>
        <div>
          <h1 class="ipd-hero-name">{{ patientInfo.patient_name }}</h1>
          <div class="ipd-hero-meta">
            <span class="mono">{{ patientInfo.card_number }}</span>
            <span class="sep">·</span>
            <span>{{ patientInfo.ward || '—' }}</span>
            <span class="sep">·</span>
            <span>{{ bloodRequests.length }} blood requests</span>
            <template v-if="bloodRequests.length > 0 && bloodRequests[0].blood_type">
              <span class="sep">·</span>
              <span>Last type {{ bloodRequests[0].blood_type }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Request Blood Form -->
    <section class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Request Blood Transfusion</h2>
      </div>
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6">
          <q-select
            v-model="requestForm.transfusion_type_id"
            :options="transfusionTypeOptions"
            filled
            label="Transfusion Type *"
            hint="Select type of blood transfusion (e.g., Packed Cells, Whole Blood)"
            :rules="[val => !!val || 'Transfusion type is required']"
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
          <q-select
            v-model="requestForm.blood_type"
            :options="bloodTypeOptions"
            filled
            label="Patient Blood Type *"
            hint="Select patient's blood type (from sample test)"
            :rules="[val => !!val || 'Blood type is required']"
            emit-value
            map-options
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label class="text-weight-bold">{{ scope.opt.label }}</q-item-label>
                  <q-item-label caption v-if="scope.opt.description">
                    {{ scope.opt.description }}
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
          <HmsButton
            variant="danger"
            :loading="submitting"
            :disabled="!requestForm.transfusion_type_id || !requestForm.blood_type || !requestForm.quantity"
            @click="submitRequest"
          >
            Submit Request
          </HmsButton>
          <HmsButton variant="secondary" @click="clearForm">
            Clear
          </HmsButton>
        </div>
      </div>
    </section>

    <!-- Blood Requests History -->
    <section class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Blood Requests History ({{ bloodRequests.length }})</h2>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadBloodRequests">
          Refresh
        </HmsButton>
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
    </section>

    <!-- Edit Request Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Blood Transfusion Request</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="updateRequest" class="q-gutter-md">
            <q-select
              v-model="editForm.transfusion_type_id"
              :options="transfusionTypeOptions"
              filled
              label="Transfusion Type *"
              hint="Select type of blood transfusion (e.g., Packed Cells, Whole Blood)"
              :rules="[val => !!val || 'Transfusion type is required']"
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
            <q-select
              v-model="editForm.blood_type"
              :options="bloodTypeOptions"
              filled
              label="Patient Blood Type *"
              hint="Select patient's blood type (from sample test)"
              :rules="[val => !!val || 'Blood type is required']"
              emit-value
              map-options
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label class="text-weight-bold">{{ scope.opt.label }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model.number="editForm.quantity"
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
            <q-input
              v-model="editForm.request_reason"
              filled
              type="textarea"
              label="Request Reason (optional)"
              hint="Reason for blood transfusion request"
              rows="3"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Update Request"
                type="submit"
                color="primary"
                class="col"
                :loading="updating"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { consultationAPI } from '../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);

const patientInfo = ref(null);

const btrPatientInitials = (info) => {
  if (!info?.patient_name) return '?';
  const parts = String(info.patient_name).trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};
const bloodRequests = ref([]);
const loading = ref(false);
const submitting = ref(false);
const updating = ref(false);
const processingId = ref(null);
const transfusionTypes = ref([]);
const showEditDialog = ref(false);
const editingRequest = ref(null);

const requestForm = ref({
  transfusion_type_id: null,
  blood_type: null,
  quantity: 1.0,
  request_reason: '',
});

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

const columns = [
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
  if (!requestForm.value.transfusion_type_id || !requestForm.value.blood_type || !requestForm.value.quantity) {
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
      blood_type: requestForm.value.blood_type,
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
    blood_type: null,
    quantity: 1.0,
    request_reason: '',
  };
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
    await loadBloodRequests();
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
.am-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  margin-bottom: 0.95rem;
}
.am-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.85rem;
}

.ipd-patient-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  margin-bottom: 0.95rem;
  padding: 1rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  position: sticky;
  top: 0.55rem;
  z-index: 6;
}
.ipd-hero-main { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.ipd-hero-avatar {
  width: 3rem; height: 3rem; border-radius: 999px;
  display: grid; place-items: center;
  font-weight: 700; font-size: 0.85rem;
  color: var(--hms-accent); background: var(--hms-accent-muted);
  flex-shrink: 0;
}
.ipd-hero-name {
  margin: 0;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  font-weight: 750;
  color: var(--hms-text-primary);
  letter-spacing: -0.02em;
}
.ipd-hero-meta {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.15rem;
}
.ipd-hero-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.ipd-hero-meta .mono,
.mono { font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.ipd-hero-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.balance-pill {
  display: inline-flex; flex-direction: column; align-items: flex-end;
  padding: 0.35rem 0.7rem; border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border); background: var(--hms-surface);
  cursor: pointer; font: inherit;
}
.balance-pill .balance-label {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--hms-text-muted);
}
.balance-pill .balance-value { font-weight: 700; font-variant-numeric: tabular-nums; }
.balance-pill.due .balance-value { color: var(--hms-critical); }
.balance-pill.ok .balance-value { color: var(--hms-success); }
.balance-pill.neutral .balance-value { color: var(--hms-text-secondary); }
@media (max-width: 720px) {
  .ipd-patient-hero { position: static; }
}
:deep(.glass-card) {
  border-radius: var(--hms-radius-xl) !important;
  border: 1px solid var(--hms-border) !important;
  box-shadow: var(--hms-shadow-md) !important;
  background: var(--hms-panel-bg) !important;
}
:deep(.text-h6.glass-text),
:deep(.glass-text.text-h6) {
  font-size: var(--hms-text-lg) !important;
  font-weight: 700 !important;
  color: var(--hms-text-primary) !important;
}


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

