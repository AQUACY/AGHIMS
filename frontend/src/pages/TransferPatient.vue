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
        Transfer Patient
      </div>
    </div>

    <!-- Patient Search Section -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="search" color="primary" class="q-mr-sm" />
          Search Patient to Transfer
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-input
              v-model="searchCardNumber"
              filled
              label="Search by Card Number"
              hint="Enter patient's card number"
              @keyup.enter="searchPatientByCard"
              :loading="searchingPatient"
            >
              <template v-slot:append>
                <q-btn
                  v-if="searchCardNumber"
                  flat
                  dense
                  icon="clear"
                  @click="searchCardNumber = ''"
                />
                <q-btn
                  flat
                  dense
                  icon="search"
                  color="primary"
                  @click="searchPatientByCard"
                  :loading="searchingPatient"
                />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="searchPatientName"
              filled
              label="Search by Name"
              hint="Enter patient's full name"
              @keyup.enter="searchPatientByName"
              :loading="searchingPatient"
            >
              <template v-slot:append>
                <q-btn
                  v-if="searchPatientName"
                  flat
                  dense
                  icon="clear"
                  @click="searchPatientName = ''"
                />
                <q-btn
                  flat
                  dense
                  icon="search"
                  color="primary"
                  @click="searchPatientByName"
                  :loading="searchingPatient"
                />
              </template>
            </q-input>
          </div>
        </div>

        <div v-if="searchResults.length > 0" class="q-mt-md">
          <div class="text-subtitle1 text-secondary q-mb-sm">Search Results:</div>
          <q-list bordered separator class="rounded-borders">
            <q-item
              v-for="patient in searchResults"
              :key="patient.id"
              clickable
              v-ripple
              @click="selectPatient(patient)"
              :active="selectedPatient?.id === patient.id"
              active-class="bg-blue-1 text-primary"
            >
              <q-item-section avatar>
                <q-avatar icon="person" color="primary" text-color="white" />
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  {{ patient.name }} {{ patient.surname }}
                  <span v-if="patient.other_names">({{ patient.other_names }})</span>
                </q-item-label>
                <q-item-label caption>
                  Card: {{ patient.card_number }} | Gender: {{ patient.gender }} | DOB: {{ formatDate(patient.date_of_birth) }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="check_circle" color="positive" v-if="selectedPatient?.id === patient.id" />
              </q-item-section>
            </q-item>
          </q-list>
        </div>
        <div v-else-if="!searchingPatient && (searchCardNumber || searchPatientName)" class="q-mt-md text-center text-secondary">
          No patients found.
        </div>
      </q-card-section>
    </q-card>

    <!-- Pending Transfer Warning -->
    <q-card v-if="selectedPatient && currentAdmission && hasPendingTransfer && transferType === 'ward'" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center">
          <q-icon name="warning" color="warning" size="32px" class="q-mr-md" />
          <div class="col">
            <div class="text-h6 text-weight-bold glass-text q-mb-xs">
              Pending Transfer Exists
            </div>
            <div class="text-body2 text-secondary">
              This patient already has a pending transfer request:
              <strong>From {{ pendingTransferInfo?.from_ward }} to {{ pendingTransferInfo?.to_ward }}</strong>
              <br />
              Requested at: {{ formatDateTime(pendingTransferInfo?.transferred_at) }}
              <br />
              <span v-if="pendingTransferInfo?.transfer_reason">
                Reason: {{ pendingTransferInfo.transfer_reason }}
              </span>
            </div>
            <div class="text-body2 text-warning q-mt-sm">
              <strong>Please wait for this transfer to be accepted or rejected before creating another transfer.</strong>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Transfer Form -->
    <q-card v-if="selectedPatient && currentAdmission" class="glass-card" flat bordered>
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6 glass-text">
          Transfer Patient - {{ selectedPatient?.name }} {{ selectedPatient?.surname }}
        </div>
        <q-space />
      </q-card-section>

      <q-card-section>
        <!-- Current Admission Info -->
        <q-card flat bordered class="q-pa-md q-mb-md bg-blue-1">
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Current Admission Details:</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-body2 text-secondary">Current Ward</div>
              <div class="text-body1 glass-text">
                <strong>{{ currentAdmission.ward }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6" v-if="currentAdmission.bed_number">
              <div class="text-body2 text-secondary">Current Bed</div>
              <div class="text-body1 glass-text">
                <strong>{{ currentAdmission.bed_number }}</strong>
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2 text-secondary">Admitted At</div>
              <div class="text-body1 glass-text">
                <strong>{{ formatDateTime(currentAdmission.admitted_at) }}</strong>
              </div>
            </div>
          </div>
        </q-card>

        <!-- Transfer Type Selection -->
        <div class="q-mb-md">
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Transfer Type:</div>
          <q-radio
            v-model="transferType"
            val="ward"
            label="Transfer to Another Ward"
            color="primary"
            class="q-mr-md"
          />
          <q-radio
            v-model="transferType"
            val="bed"
            label="Transfer to Another Bed (Same Ward)"
            color="primary"
          />
        </div>

        <q-separator class="q-mb-md" />

        <!-- Transfer Form Fields -->
        <div class="row q-col-gutter-md">
          <!-- Ward Transfer -->
          <template v-if="transferType === 'ward'">
            <div class="col-12 col-md-6">
              <q-select
                v-model="transferForm.to_ward"
                :options="wardOptions"
                filled
                label="Transfer To Ward *"
                :rules="[val => !!val || 'Ward is required']"
                emit-value
                map-options
                @update:model-value="onWardSelected"
                :disable="transferForm.to_ward === currentAdmission.ward"
              >
                <template v-slot:prepend>
                  <q-icon name="local_hospital" />
                </template>
              </q-select>
              <div v-if="transferForm.to_ward === currentAdmission.ward" class="text-caption text-warning q-mt-xs">
                Cannot transfer to the same ward
              </div>
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="transferForm.bed_id"
                :options="availableBeds"
                option-label="bed_number"
                option-value="id"
                filled
                label="Select Bed *"
                :loading="loadingBeds"
                :rules="[val => !!val || 'Please select a bed']"
                emit-value
                map-options
                :disable="!transferForm.to_ward || transferForm.to_ward === currentAdmission.ward"
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
            </div>
          </template>

          <!-- Bed Transfer (Same Ward) -->
          <template v-if="transferType === 'bed'">
            <div class="col-12 col-md-6">
              <q-select
                v-model="transferForm.bed_id"
                :options="availableBedsSameWard"
                option-label="bed_number"
                option-value="id"
                filled
                label="Select New Bed *"
                :loading="loadingBeds"
                :rules="[val => !!val || 'Please select a bed']"
                emit-value
                map-options
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
                      No available beds found in this ward
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </div>
          </template>

          <!-- Transfer Reason -->
          <div class="col-12">
            <q-input
              v-model="transferForm.transfer_reason"
              filled
              type="textarea"
              label="Transfer Reason"
              hint="Optional: Reason for transfer"
              rows="3"
            />
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Cancel" color="primary" @click="resetForm" />
        <q-btn
          flat
          label="Transfer Patient"
          color="positive"
          @click="submitTransfer"
          :loading="transferring"
          :disable="!isFormValid || (transferType === 'ward' && hasPendingTransfer)"
        />
      </q-card-actions>
    </q-card>

    <!-- No Active Admission Message -->
    <q-card v-if="selectedPatient && !currentAdmission" class="glass-card" flat bordered>
      <q-card-section class="text-center">
        <q-icon name="info" size="48px" color="warning" class="q-mb-sm" />
        <div class="text-subtitle1 glass-text">
          Patient is not currently admitted to any ward
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { patientsAPI, consultationAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();

const searchCardNumber = ref('');
const searchPatientName = ref('');
const searchingPatient = ref(false);
const searchResults = ref([]);
const selectedPatient = ref(null);
const currentAdmission = ref(null);
const transferType = ref('ward');
const transferring = ref(false);
const loadingBeds = ref(false);
const availableBeds = ref([]);
const availableBedsSameWard = ref([]);

const transferForm = ref({
  ward_admission_id: null,
  from_ward: null,
  to_ward: null,
  bed_id: null,
  transfer_reason: '',
});

const wardOptions = [
  { label: 'Accident & Emergency Ward', value: 'Accident & Emergency Ward' },
  { label: 'Maternity Ward', value: 'Maternity Ward' },
  { label: 'Female Ward', value: 'Female Ward' },
  { label: 'Male Ward', value: 'Male Ward' },
  { label: 'Kids Ward', value: 'Kids Ward' },
  { label: 'Nicu', value: 'Nicu' },
  { label: 'Detention & Observation Ward', value: 'Detention & Observation Ward' },
];

const searchPatientByCard = async () => {
  if (!searchCardNumber.value.trim()) {
    $q.notify({ type: 'warning', message: 'Please enter a card number' });
    return;
  }
  searchingPatient.value = true;
  try {
    const response = await patientsAPI.getByCard(searchCardNumber.value.trim());
    searchResults.value = Array.isArray(response.data) ? response.data : [];
    if (searchResults.value.length === 0) {
      $q.notify({ type: 'info', message: 'No patient found with that card number' });
    }
  } catch (error) {
    console.error('Error searching patient by card:', error);
    $q.notify({ type: 'negative', message: 'Failed to search patient' });
  } finally {
    searchingPatient.value = false;
  }
};

const searchPatientByName = async () => {
  if (!searchPatientName.value.trim()) {
    $q.notify({ type: 'warning', message: 'Please enter a patient name' });
    return;
  }
  searchingPatient.value = true;
  try {
    const response = await patientsAPI.searchByName(searchPatientName.value.trim());
    searchResults.value = Array.isArray(response.data) ? response.data : [];
    if (searchResults.value.length === 0) {
      $q.notify({ type: 'info', message: 'No patient found with that name' });
    }
  } catch (error) {
    console.error('Error searching patient by name:', error);
    $q.notify({ type: 'negative', message: 'Failed to search patient' });
  } finally {
    searchingPatient.value = false;
  }
};

const selectPatient = async (patient) => {
  selectedPatient.value = patient;
  // Load current admission
  try {
    const response = await consultationAPI.getWardAdmissions(null, false);
    const admissions = Array.isArray(response.data) ? response.data : [];
    const admission = admissions.find(a => a.patient_card_number === patient.card_number);
    
    if (admission) {
      currentAdmission.value = admission;
      transferForm.value.ward_admission_id = admission.id;
      transferForm.value.from_ward = admission.ward;
      
      // Check for pending transfers
      await checkPendingTransfer(admission.id);
      
      // Load beds for same ward if bed transfer
      if (transferType.value === 'bed') {
        await loadBedsForWard(admission.ward);
      }
    } else {
      currentAdmission.value = null;
      transferForm.value.ward_admission_id = null;
      transferForm.value.from_ward = null;
      hasPendingTransfer.value = false;
      pendingTransferInfo.value = null;
    }
  } catch (error) {
    console.error('Error loading admission:', error);
    $q.notify({ type: 'negative', message: 'Failed to load patient admission' });
  }
};

const checkPendingTransfer = async (wardAdmissionId) => {
  try {
    const response = await consultationAPI.getPendingTransfers();
    const allPending = Array.isArray(response.data) ? response.data : [];
    const pending = allPending.find(t => t.ward_admission_id === wardAdmissionId);
    
    if (pending) {
      hasPendingTransfer.value = true;
      pendingTransferInfo.value = pending;
    } else {
      hasPendingTransfer.value = false;
      pendingTransferInfo.value = null;
    }
  } catch (error) {
    console.error('Error checking pending transfer:', error);
    hasPendingTransfer.value = false;
    pendingTransferInfo.value = null;
  }
};

const onWardSelected = async (ward) => {
  if (ward && ward !== currentAdmission.value?.ward) {
    await loadBedsForWard(ward);
  } else {
    availableBeds.value = [];
    transferForm.value.bed_id = null;
  }
};

const loadBedsForWard = async (ward) => {
  if (!ward) return;
  loadingBeds.value = true;
  try {
    const response = await consultationAPI.getBeds(ward, true);
    const beds = Array.isArray(response.data) ? response.data : [];
    
    if (transferType.value === 'ward') {
      availableBeds.value = beds;
    } else {
      // For bed transfer, exclude current bed
      const currentBedId = currentAdmission.value?.bed_id;
      availableBedsSameWard.value = beds.filter(bed => bed.id !== currentBedId);
    }
  } catch (error) {
    console.error('Error loading beds:', error);
    $q.notify({ type: 'negative', message: 'Failed to load beds' });
  } finally {
    loadingBeds.value = false;
  }
};

const isFormValid = computed(() => {
  if (!selectedPatient.value || !currentAdmission.value) return false;
  
  if (transferType.value === 'ward') {
    return !!(
      transferForm.value.to_ward &&
      transferForm.value.to_ward !== currentAdmission.value.ward &&
      transferForm.value.bed_id
    );
  } else {
    return !!transferForm.value.bed_id;
  }
});

const submitTransfer = async () => {
  if (!isFormValid.value) {
    $q.notify({
      type: 'negative',
      message: 'Please complete all required fields',
    });
    return;
  }

  // Check for pending transfer before submitting
  if (transferType.value === 'ward' && hasPendingTransfer.value) {
    $q.notify({
      type: 'warning',
      message: 'This patient already has a pending transfer request. Please wait for it to be accepted or rejected.',
      timeout: 5000,
    });
    return;
  }

  transferring.value = true;
  try {
    const payload = {
      ward_admission_id: transferForm.value.ward_admission_id,
      from_ward: transferForm.value.from_ward,
      to_ward: transferType.value === 'ward' ? transferForm.value.to_ward : currentAdmission.value.ward,
      bed_id: transferForm.value.bed_id,
      transfer_reason: transferForm.value.transfer_reason || null,
    };
    
    const response = await consultationAPI.transferPatient(payload);
    $q.notify({
      type: 'positive',
      message: response.message || 'Patient transferred successfully',
    });
    resetForm();
    router.push('/ipd/transfer-acceptance');
  } catch (error) {
    console.error('Error transferring patient:', error);
    const errorMessage = error.response?.data?.detail || 'Failed to transfer patient';
    
    // Check if error is about pending transfer
    if (errorMessage.includes('pending transfer')) {
      hasPendingTransfer.value = true;
      await checkPendingTransfer(transferForm.value.ward_admission_id);
    }
    
    $q.notify({
      type: 'negative',
      message: errorMessage,
      timeout: 5000,
    });
  } finally {
    transferring.value = false;
  }
};

const resetForm = () => {
  selectedPatient.value = null;
  currentAdmission.value = null;
  searchResults.value = [];
  searchCardNumber.value = '';
  searchPatientName.value = '';
  transferType.value = 'ward';
  transferForm.value = {
    ward_admission_id: null,
    from_ward: null,
    to_ward: null,
    bed_id: null,
    transfer_reason: '',
  };
  availableBeds.value = [];
  availableBedsSameWard.value = [];
  hasPendingTransfer.value = false;
  pendingTransferInfo.value = null;
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

// Watch transfer type
watch(transferType, () => {
  if (transferType.value === 'bed' && currentAdmission.value) {
    loadBedsForWard(currentAdmission.value.ward);
    transferForm.value.to_ward = currentAdmission.value.ward;
  } else if (transferType.value === 'ward') {
    transferForm.value.to_ward = null;
    transferForm.value.bed_id = null;
    availableBeds.value = [];
    // Re-check pending transfer when switching to ward transfer
    if (currentAdmission.value) {
      checkPendingTransfer(currentAdmission.value.id);
    }
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

