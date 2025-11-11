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
        Transfer Acceptance
      </div>
    </div>

    <!-- Ward Filter -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              filled
              label="Filter by Receiving Ward"
              clearable
              emit-value
              map-options
              @update:model-value="loadPendingTransfers"
            >
              <template v-slot:prepend>
                <q-icon name="local_hospital" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4 flex items-end">
            <q-btn
              flat
              icon="refresh"
              label="Refresh"
              color="primary"
              @click="loadPendingTransfers"
              :loading="loading"
            />
          </div>
          <div class="col-12 col-md-4 flex items-end">
            <q-badge color="warning" :label="`${pendingTransfers.length} Pending`" class="text-h6 q-pa-sm" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading pending transfers...</div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="!loading && pendingTransfers.length === 0" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="check_circle" size="64px" color="positive" class="q-mb-sm" />
        <div class="text-subtitle1 glass-text">No pending transfers</div>
        <div class="text-body2 text-secondary q-mt-sm">
          All transfer requests have been processed
        </div>
      </q-card-section>
    </q-card>

    <!-- Pending Transfers List -->
    <div v-else class="row q-col-gutter-md">
      <div
        v-for="transfer in pendingTransfers"
        :key="transfer.id"
        class="col-12 col-md-6 col-lg-4"
      >
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="row items-start q-mb-md">
              <q-avatar size="56px" color="warning" text-color="white" class="q-mr-md">
                <q-icon name="swap_horiz" size="32px" />
              </q-avatar>
              <div class="col">
                <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                  {{ transfer.patient_name }} {{ transfer.patient_surname }}
                </div>
                <div class="text-caption text-secondary q-mb-xs">
                  <q-icon name="credit_card" size="14px" class="q-mr-xs" />
                  Card: {{ transfer.patient_card_number }}
                </div>
                <div class="text-caption text-secondary">
                  <q-icon name="person" size="14px" class="q-mr-xs" />
                  {{ transfer.patient_gender }}
                </div>
              </div>
            </div>

            <q-separator class="q-mb-md" />

            <div class="row q-col-gutter-xs q-mb-md">
              <div class="col-12">
                <q-badge color="info" :label="`From: ${transfer.from_ward}`" class="q-mr-sm" />
                <q-badge color="primary" :label="`To: ${transfer.to_ward}`" />
              </div>
            </div>

            <div class="text-body2 text-secondary q-mb-md">
              <div class="q-mb-xs">
                <q-icon name="schedule" size="14px" class="q-mr-xs" />
                Requested: {{ formatDateTime(transfer.transferred_at) }}
              </div>
              <div v-if="transfer.transferred_by_name" class="q-mb-xs">
                <q-icon name="person" size="14px" class="q-mr-xs" />
                By: <strong>{{ transfer.transferred_by_name }}</strong>
              </div>
              <div v-if="transfer.transfer_reason" class="q-mt-sm">
                <q-icon name="info" size="14px" class="q-mr-xs" />
                <strong>Reason:</strong> {{ transfer.transfer_reason }}
              </div>
            </div>

            <q-separator class="q-mb-md" />

            <div class="row q-gutter-xs">
              <q-btn
                flat
                dense
                icon="check"
                label="Accept"
                color="positive"
                size="sm"
                @click="acceptTransfer(transfer)"
                :loading="acceptingTransferId === transfer.id"
                class="col"
              />
              <q-btn
                flat
                dense
                icon="close"
                label="Reject"
                color="negative"
                size="sm"
                @click="rejectTransfer(transfer)"
                :loading="rejectingTransferId === transfer.id"
                class="col"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Accept Transfer Dialog -->
    <q-dialog v-model="showAcceptDialog" persistent>
      <q-card style="min-width: 400px;">
        <q-card-section>
          <div class="text-h6 glass-text">Accept Transfer</div>
        </q-card-section>

        <q-card-section>
          <div class="text-body2 text-secondary q-mb-md">
            <div class="q-mb-sm">
              <strong>Patient:</strong> {{ currentTransfer?.patient_name }} {{ currentTransfer?.patient_surname }}
            </div>
            <div class="q-mb-sm">
              <strong>Card Number:</strong> {{ currentTransfer?.patient_card_number }}
            </div>
            <div class="q-mb-sm">
              <strong>From:</strong> {{ currentTransfer?.from_ward }}
            </div>
            <div class="q-mb-sm">
              <strong>To:</strong> {{ currentTransfer?.to_ward }}
            </div>
            <div v-if="currentTransfer?.transfer_reason" class="q-mt-md">
              <strong>Transfer Reason:</strong> {{ currentTransfer.transfer_reason }}
            </div>
          </div>
          <q-select
            v-model="selectedBedId"
            :options="availableBedsForTransfer"
            option-label="bed_number"
            option-value="id"
            filled
            label="Select Bed *"
            :rules="[val => !!val || 'Please select a bed']"
            emit-value
            map-options
            :loading="loadingBeds"
          >
            <template v-slot:prepend>
              <q-icon name="hotel" />
            </template>
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.bed_number }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.ward }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-chip color="positive" text-color="white" size="sm">Available</q-chip>
                </q-item-section>
              </q-item>
            </template>
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No available beds found for this ward
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showAcceptDialog = false" />
          <q-btn
            flat
            label="Accept Transfer"
            color="positive"
            @click="confirmAcceptTransfer"
            :loading="acceptingTransferId === currentTransfer?.id"
            :disable="!selectedBedId"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reject Transfer Dialog -->
    <q-dialog v-model="showRejectDialog" persistent>
      <q-card style="min-width: 400px;">
        <q-card-section>
          <div class="text-h6 glass-text">Reject Transfer</div>
        </q-card-section>

        <q-card-section>
          <div class="text-body2 text-secondary q-mb-md">
            <div class="q-mb-sm">
              <strong>Patient:</strong> {{ currentTransfer?.patient_name }} {{ currentTransfer?.patient_surname }}
            </div>
            <div class="q-mb-sm">
              <strong>Card Number:</strong> {{ currentTransfer?.patient_card_number }}
            </div>
            <div class="q-mb-sm">
              <strong>From:</strong> {{ currentTransfer?.from_ward }}
            </div>
            <div class="q-mb-sm">
              <strong>To:</strong> {{ currentTransfer?.to_ward }}
            </div>
            <div v-if="currentTransfer?.transfer_reason" class="q-mt-md">
              <strong>Transfer Reason:</strong> {{ currentTransfer.transfer_reason }}
            </div>
          </div>
          <q-input
            v-model="rejectionReason"
            filled
            type="textarea"
            label="Rejection Reason (Optional)"
            hint="Provide a reason for rejecting this transfer"
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showRejectDialog = false" />
          <q-btn
            flat
            label="Reject Transfer"
            color="negative"
            @click="confirmRejectTransfer"
            :loading="rejectingTransferId === currentTransfer?.id"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();

const loading = ref(false);
const loadingBeds = ref(false);
const selectedWard = ref(null);
const pendingTransfers = ref([]);
const acceptingTransferId = ref(null);
const rejectingTransferId = ref(null);
const showAcceptDialog = ref(false);
const showRejectDialog = ref(false);
const currentTransfer = ref(null);
const availableBedsForTransfer = ref([]);
const selectedBedId = ref(null);
const rejectionReason = ref('');

const wardOptions = [
  { label: 'Accident & Emergency Ward', value: 'Accident & Emergency Ward' },
  { label: 'Maternity Ward', value: 'Maternity Ward' },
  { label: 'Female Ward', value: 'Female Ward' },
  { label: 'Male Ward', value: 'Male Ward' },
  { label: 'Kids Ward', value: 'Kids Ward' },
  { label: 'Nicu', value: 'Nicu' },
  { label: 'Detention & Observation Ward', value: 'Detention & Observation Ward' },
];

const loadPendingTransfers = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getPendingTransfers(selectedWard.value);
    pendingTransfers.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading pending transfers:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load pending transfers',
    });
    pendingTransfers.value = [];
  } finally {
    loading.value = false;
  }
};

const acceptTransfer = async (transfer) => {
  // Load available beds for the receiving ward
  loadingBeds.value = true;
  try {
    const bedsResponse = await consultationAPI.getBeds(transfer.to_ward, true);
    availableBedsForTransfer.value = Array.isArray(bedsResponse.data) ? bedsResponse.data : [];
    
    if (availableBedsForTransfer.value.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No available beds in this ward',
      });
      return;
    }
    
    currentTransfer.value = transfer;
    selectedBedId.value = null;
    showAcceptDialog.value = true;
  } catch (error) {
    console.error('Error loading beds:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load available beds',
    });
  } finally {
    loadingBeds.value = false;
  }
};

const confirmAcceptTransfer = async () => {
  if (!selectedBedId.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a bed',
    });
    return;
  }
  
  acceptingTransferId.value = currentTransfer.value.id;
  try {
    await consultationAPI.acceptTransfer(currentTransfer.value.id, selectedBedId.value);
    $q.notify({
      type: 'positive',
      message: 'Transfer accepted successfully',
    });
    showAcceptDialog.value = false;
    selectedBedId.value = null;
    currentTransfer.value = null;
    await loadPendingTransfers(); // Reload pending transfers
  } catch (error) {
    console.error('Error accepting transfer:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to accept transfer',
    });
  } finally {
    acceptingTransferId.value = null;
  }
};

const rejectTransfer = (transfer) => {
  currentTransfer.value = transfer;
  rejectionReason.value = '';
  showRejectDialog.value = true;
};

const confirmRejectTransfer = async () => {
  rejectingTransferId.value = currentTransfer.value.id;
  try {
    await consultationAPI.rejectTransfer(currentTransfer.value.id, rejectionReason.value);
    $q.notify({
      type: 'info',
      message: 'Transfer rejected',
    });
    showRejectDialog.value = false;
    rejectionReason.value = '';
    currentTransfer.value = null;
    await loadPendingTransfers(); // Reload pending transfers
  } catch (error) {
    console.error('Error rejecting transfer:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to reject transfer',
    });
  } finally {
    rejectingTransferId.value = null;
  }
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

onMounted(() => {
  loadPendingTransfers();
});
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

.body--dark .glass-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>

