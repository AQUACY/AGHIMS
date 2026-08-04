<template>
  <q-page class="hms-page dns-page">
    <HmsPageHeader
      title="Doctor / Nursing station"
      subtitle="Select a ward to manage admitted patients and pending transfers."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.push('/ipd')">Back to IPD</HmsButton>
      </template>
    </HmsPageHeader>

    <!-- Ward picker -->
    <div class="dns-toolbar">
      <div class="dns-toolbar-main">
        <label class="dns-field">
          <span class="dns-label">Ward</span>
          <q-select
            v-model="selectedWard"
            :options="wardOptions"
            dense
            outlined
            emit-value
            map-options
            placeholder="Select ward…"
            @update:model-value="onWardSelected"
            class="dns-select"
          />
        </label>
        <HmsButton
          :variant="wardLocked ? 'soft' : 'ghost'"
          size="sm"
          @click="toggleWardLock"
        >
          {{ wardLocked ? 'Unlock ward' : 'Lock ward' }}
        </HmsButton>
      </div>
      <div v-if="selectedWard" class="dns-toolbar-meta">
        <HmsBadge tone="accent">{{ selectedWard }}</HmsBadge>
        <span class="dns-count">{{ filteredPatients.length }} active</span>
        <span v-if="pendingTransfers.length" class="dns-count warn">{{ pendingTransfers.length }} transfer{{ pendingTransfers.length === 1 ? '' : 's' }}</span>
      </div>
    </div>

    <div v-if="!selectedWard" class="dns-empty-wrap">
      <HmsEmptyState
        title="Select a ward to begin"
        description="Choose a ward above to see admitted patients and pending transfer requests."
      />
    </div>

    <div v-else-if="loading" class="dns-loading">
      <q-spinner color="primary" size="2.5em" />
      <span>Loading ward patients…</span>
    </div>

    <template v-else>
      <!-- Pending transfers -->
      <section v-if="pendingTransfers.length > 0" class="dns-panel dns-transfers">
        <div class="dns-panel-head">
          <h2 class="hms-section-title">Pending transfers</h2>
          <HmsBadge tone="warning">{{ pendingTransfers.length }}</HmsBadge>
        </div>
        <div class="transfer-list">
          <div v-for="transfer in pendingTransfers" :key="transfer.id" class="transfer-row">
            <div class="transfer-avatar">{{ patientInitials(transfer.patient_name, transfer.patient_surname) }}</div>
            <div class="transfer-body">
              <div class="transfer-name">{{ transfer.patient_name }} {{ transfer.patient_surname }}</div>
              <div class="transfer-meta">
                <span class="mono">{{ transfer.patient_card_number }}</span>
                <span class="sep">·</span>
                <span>From {{ transfer.from_ward }}</span>
                <template v-if="transfer.transfer_reason">
                  <span class="sep">·</span>
                  <span>{{ transfer.transfer_reason }}</span>
                </template>
              </div>
              <div class="transfer-by">
                {{ transfer.transferred_by_name }} · {{ formatDateTime(transfer.transferred_at) }}
              </div>
            </div>
            <div class="transfer-actions">
              <HmsButton
                variant="primary"
                size="sm"
                :loading="acceptingTransferId === transfer.id"
                @click="acceptTransfer(transfer)"
              >
                Accept
              </HmsButton>
              <HmsButton
                variant="ghost"
                size="sm"
                :loading="rejectingTransferId === transfer.id"
                @click="rejectTransfer(transfer)"
              >
                Reject
              </HmsButton>
            </div>
          </div>
        </div>
      </section>

      <!-- Patients -->
      <section class="dns-panel">
        <div class="dns-panel-head dns-panel-head--row">
          <div>
            <h2 class="hms-section-title">Active patients</h2>
            <p class="dns-panel-sub">{{ selectedWard }} · {{ filteredPatients.length }} on ward</p>
          </div>
          <div class="dns-panel-tools">
            <input
              v-model="filter"
              type="search"
              class="dns-search"
              placeholder="Search by card number…"
            />
            <HmsButton variant="secondary" size="sm" @click="loadWardPatients">Refresh</HmsButton>
          </div>
        </div>

        <HmsEmptyState
          v-if="wardPatients.length === 0"
          title="No patients on this ward"
          :description="`No patients currently admitted to ${selectedWard}.`"
        />

        <HmsEmptyState
          v-else-if="filteredPatients.length === 0"
          title="No matching patients"
          description="Try a different card number filter."
        />

        <div v-else class="patient-grid">
          <motion.div
            v-for="patient in filteredPatients"
            :key="patient.id"
            class="patient-card"
            :initial="reduceMotion ? false : { opacity: 0, y: 8 }"
            :animate="{ opacity: 1, y: 0 }"
            :whileHover="reduceMotion ? undefined : { y: -3 }"
            :whilePress="reduceMotion ? undefined : { scale: 0.985 }"
            :transition="{ type: 'spring', stiffness: 380, damping: 28 }"
          >
            <div class="pc-top">
              <div class="pc-avatar">{{ patientInitials(patient.patient_name, patient.patient_surname) }}</div>
              <div class="pc-id">
                <div class="pc-name">
                  {{ patient.patient_name }} {{ patient.patient_surname }}
                  <span v-if="patient.patient_other_names">{{ patient.patient_other_names }}</span>
                </div>
                <div class="pc-meta">
                  <span class="mono">{{ patient.patient_card_number }}</span>
                  <span class="sep">·</span>
                  <span>{{ patient.patient_gender || '—' }}</span>
                  <template v-if="patient.patient_date_of_birth">
                    <span class="sep">·</span>
                    <span>{{ formatDate(patient.patient_date_of_birth) }}</span>
                  </template>
                </div>
              </div>
            </div>

            <div class="pc-badges">
              <HmsBadge tone="accent">{{ patient.ward }}</HmsBadge>
              <HmsBadge v-if="patient.bed_number" tone="info">Bed {{ patient.bed_number }}</HmsBadge>
              <HmsBadge tone="muted">{{ patient.encounter_service_type }}</HmsBadge>
            </div>

            <div class="pc-admit">
              Admitted {{ formatDateTime(patient.admitted_at) }}
              <template v-if="patient.admitted_by_name">
                · {{ patient.admitted_by_name }}
                <span v-if="patient.admitted_by_role">({{ patient.admitted_by_role }})</span>
              </template>
            </div>

            <div class="pc-actions">
              <HmsButton variant="ghost" size="sm" @click="viewPatient(patient.patient_card_number)">Profile</HmsButton>
              <HmsButton variant="ghost" size="sm" @click="viewEncounter(patient.encounter_id)">Encounter</HmsButton>
              <HmsButton variant="soft" size="sm" @click="openAdmissionManager(patient)">Manager</HmsButton>
              <HmsButton
                variant="danger"
                size="sm"
                :loading="dischargingId === patient.id"
                @click="dischargePatient(patient)"
              >
                Discharge
              </HmsButton>
            </div>
          </motion.div>
        </div>
      </section>
    </template>

    <!-- Accept Transfer Dialog -->
    <q-dialog v-model="showAcceptDialog" persistent>
      <q-card style="min-width: 400px;">
        <q-card-section>
          <div class="text-h6 glass-text">Accept Transfer</div>
        </q-card-section>

        <q-card-section>
          <div class="text-body2 text-secondary q-mb-md">
            Patient: <strong>{{ currentTransfer?.patient_name }} {{ currentTransfer?.patient_surname }}</strong>
            <br />
            From: <strong>{{ currentTransfer?.from_ward }}</strong>
            <br />
            To: <strong>{{ currentTransfer?.to_ward }}</strong>
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
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.bed_number }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-chip color="positive" text-color="white" size="sm">Available</q-chip>
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
            Patient: <strong>{{ currentTransfer?.patient_name }} {{ currentTransfer?.patient_surname }}</strong>
            <br />
            From: <strong>{{ currentTransfer?.from_ward }}</strong>
          </div>
          <q-input
            v-model="rejectionReason"
            filled
            type="textarea"
            label="Rejection Reason (Optional)"
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
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, wardsAPI } from '../services/api';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import HmsEmptyState from '../components/ui/HmsEmptyState.vue';

const $q = useQuasar();
const router = useRouter();

const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

const patientInitials = (name, surname) => {
  const a = (name || '').trim().charAt(0);
  const b = (surname || '').trim().charAt(0);
  return ((a + b) || '?').toUpperCase();
};

// Ward lock constants
const WARD_LOCK_KEY = 'doctor_nursing_station_ward_locked';
const WARD_STORAGE_KEY = 'doctor_nursing_station_selected_ward';

const loading = ref(false);
const wardPatients = ref([]);
const allWardPatients = ref([]); // Store all for getting unique wards
const pendingTransfers = ref([]);
const filter = ref('');
const selectedWard = ref(null);
const wardLocked = ref(false);
const dischargingId = ref(null);
const acceptingTransferId = ref(null);
const rejectingTransferId = ref(null);
const showAcceptDialog = ref(false);
const showRejectDialog = ref(false);
const currentTransfer = ref(null);
const availableBedsForTransfer = ref([]);
const selectedBedId = ref(null);
const rejectionReason = ref('');


// Dynamic ward options from API
const wardOptions = ref([]);

// Load wards from API
const loadWards = async () => {
  try {
    const response = await wardsAPI.getAll(true, 'ward'); // Get only active wards (department type = ward)
    const apiWards = (response.data || []).map(ward => ward.name);
    
    // Also include any wards found in patients (for backward compatibility)
    const patientWards = new Set();
    allWardPatients.value.forEach(patient => {
      if (patient.ward) {
        patientWards.add(patient.ward);
      }
    });
    
    // Merge API wards with patient wards
    const allWards = new Set([...apiWards, ...Array.from(patientWards)]);
    
    wardOptions.value = Array.from(allWards).sort().map(ward => ({
      label: ward,
      value: ward
    }));
  } catch (error) {
    console.error('Error loading wards:', error);
    // Fallback to extracting wards from patients only
    const wards = new Set();
    allWardPatients.value.forEach(patient => {
      if (patient.ward) {
        wards.add(patient.ward);
      }
    });
    wardOptions.value = Array.from(wards).sort().map(ward => ({
      label: ward,
      value: ward
    }));
  }
};

// Filter patients by search
const filteredPatients = computed(() => {
  if (!filter.value) {
    return wardPatients.value;
  }
  const searchTerm = filter.value.toLowerCase();
  return wardPatients.value.filter(patient => {
    const cardNumber = patient.patient_card_number?.toLowerCase() || '';
    const name = `${patient.patient_name} ${patient.patient_surname}`.toLowerCase();
    return cardNumber.includes(searchTerm) || name.includes(searchTerm);
  });
});

const loadWardPatients = async () => {
  if (!selectedWard.value) return;
  
  loading.value = true;
  try {
    // First load all to get ward options
    const allResponse = await consultationAPI.getWardAdmissions();
    let allData = [];
    if (Array.isArray(allResponse.data)) {
      allData = allResponse.data;
    } else if (allResponse.data && Array.isArray(allResponse.data.data)) {
      allData = allResponse.data.data;
    }
    allWardPatients.value = allData;
    
    // Then load filtered by ward
    const response = await consultationAPI.getWardAdmissions(selectedWard.value);
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    wardPatients.value = data;
    
    // Debug: Log bed numbers
    console.log('DEBUG DoctorNursingStation: Loaded ward patients:', data.map(p => ({
      id: p.id,
      name: `${p.patient_name} ${p.patient_surname}`,
      bed_id: p.bed_id,
      bed_number: p.bed_number,
      has_bed: !!p.bed_number
    })));
    
    // Load pending transfers for this ward
    await loadPendingTransfers();
    
    // Refresh wards to include any new wards found in patients
    await loadWards();
  } catch (error) {
    console.error('Error loading ward patients:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load ward patients',
    });
    wardPatients.value = [];
  } finally {
    loading.value = false;
  }
};

const loadPendingTransfers = async () => {
  if (!selectedWard.value) return;
  
  try {
    const response = await consultationAPI.getPendingTransfers(selectedWard.value);
    pendingTransfers.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading pending transfers:', error);
    pendingTransfers.value = [];
  }
};

const onWardSelected = () => {
  if (selectedWard.value) {
    // Save ward selection if locked
    if (wardLocked.value) {
      saveWardToStorage();
    }
    loadWardPatients();
  } else {
    wardPatients.value = [];
    pendingTransfers.value = [];
    // Clear saved ward if unlocked
    if (!wardLocked.value) {
      localStorage.removeItem(WARD_STORAGE_KEY);
    }
  }
};

const toggleWardLock = () => {
  wardLocked.value = !wardLocked.value;
  localStorage.setItem(WARD_LOCK_KEY, wardLocked.value.toString());
  
  if (wardLocked.value) {
    // Lock: Save current ward selection
    if (selectedWard.value) {
      saveWardToStorage();
    }
    $q.notify({
      type: 'positive',
      message: 'Ward selection locked',
      timeout: 2000,
    });
  } else {
    // Unlock: Clear saved ward
    localStorage.removeItem(WARD_STORAGE_KEY);
    $q.notify({
      type: 'info',
      message: 'Ward selection unlocked',
      timeout: 2000,
    });
  }
};

const saveWardToStorage = () => {
  if (selectedWard.value) {
    localStorage.setItem(WARD_STORAGE_KEY, selectedWard.value);
  }
};

const loadWardFromStorage = () => {
  const savedWard = localStorage.getItem(WARD_STORAGE_KEY);
  const isLocked = localStorage.getItem(WARD_LOCK_KEY) === 'true';
  
  wardLocked.value = isLocked;
  
  if (isLocked && savedWard) {
    selectedWard.value = savedWard;
    return true; // Indicate ward was loaded
  }
  return false; // No ward loaded
};

// Watch for ward changes when locked
watch(selectedWard, (newWard) => {
  if (wardLocked.value && newWard) {
    saveWardToStorage();
  }
});

const dischargePatient = async (patient) => {
  $q.dialog({
    title: 'Discharge Patient',
    message: `Are you sure you want to discharge ${patient.patient_name} ${patient.patient_surname} from ${patient.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    dischargingId.value = patient.id;
    try {
      await consultationAPI.dischargePatient(patient.id);
      $q.notify({
        type: 'positive',
        message: 'Patient discharged successfully',
      });
      // Reload ward patients
      await loadWardPatients();
    } catch (error) {
      console.error('Error discharging patient:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to discharge patient',
      });
    } finally {
      dischargingId.value = null;
    }
  });
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

const viewPatient = (cardNumber) => {
  router.push(`/patients/${cardNumber}`);
};

const viewEncounter = (encounterId) => {
  router.push(`/consultation/${encounterId}`);
};

const openAdmissionManager = (patient) => {
  router.push(`/ipd/admission-manager/${patient.id}?encounter_id=${patient.encounter_id}&card_number=${patient.patient_card_number}`);
};

const acceptTransfer = async (transfer) => {
  // Load available beds for the receiving ward
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
    showAcceptDialog.value = true;
  } catch (error) {
    console.error('Error loading beds:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load available beds',
    });
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
    await loadWardPatients(); // Reload to show the new patient
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

onMounted(async () => {
  // Load wards from API first
  await loadWards();
  
  // Load all ward patients to get ward options
  try {
    const response = await consultationAPI.getWardAdmissions();
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    allWardPatients.value = data;
    
    // Refresh wards to include any wards found in patients
    await loadWards();
    
    // Try to load saved ward if locked
    const wardLoaded = loadWardFromStorage();
    if (wardLoaded && selectedWard.value) {
      // Ward was loaded from storage, now load patients for that ward
      await loadWardPatients();
    }
  } catch (error) {
    console.error('Error loading ward options:', error);
  }
});
</script>


<style scoped>
.dns-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.85rem;
  margin-bottom: 0.95rem;
  padding: 0.95rem 1.1rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.dns-toolbar-main {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.65rem;
}
.dns-field { display: flex; flex-direction: column; gap: 0.3rem; min-width: min(280px, 100%); }
.dns-label {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}
.dns-select { min-width: 240px; }
.dns-toolbar-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
}
.dns-count {
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  font-weight: 600;
}
.dns-count.warn { color: #d97706; }
.dns-empty-wrap { margin-top: 0.5rem; }
.dns-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 1rem;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
}
.dns-panel {
  margin-bottom: 0.95rem;
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.dns-panel-head {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.85rem;
}
.dns-panel-head--row {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.dns-panel-sub {
  margin: 0.15rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.dns-panel-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.dns-search {
  min-width: min(220px, 100%);
  height: 2.05rem;
  padding: 0 0.75rem;
  border-radius: var(--hms-radius-md);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-primary);
  font: inherit;
  font-size: var(--hms-text-sm);
}
.dns-search:focus {
  outline: none;
  border-color: var(--hms-accent);
  box-shadow: 0 0 0 3px var(--hms-accent-muted);
}
.transfer-list { display: flex; flex-direction: column; gap: 0.55rem; }
.transfer-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.transfer-avatar, .pc-avatar {
  width: 2.5rem; height: 2.5rem;
  border-radius: 999px;
  display: grid; place-items: center;
  font-size: 0.78rem; font-weight: 700;
  color: var(--hms-accent);
  background: var(--hms-accent-muted);
  flex-shrink: 0;
}
.transfer-body { flex: 1; min-width: 180px; }
.transfer-name, .pc-name {
  font-weight: 700;
  color: var(--hms-text-primary);
  font-size: var(--hms-text-md);
}
.transfer-meta, .pc-meta, .transfer-by, .pc-admit {
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  margin-top: 0.12rem;
}
.transfer-by { color: var(--hms-text-muted); font-size: 0.75rem; }
.transfer-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.sep { margin: 0 0.25rem; opacity: 0.45; }
.mono { font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.92em; }
.patient-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}
.patient-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 0.95rem 1rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
  cursor: default;
}
.pc-top { display: flex; gap: 0.7rem; align-items: flex-start; }
.pc-id { min-width: 0; }
.pc-badges { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.pc-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  margin-top: auto;
  padding-top: 0.35rem;
  border-top: 1px solid var(--hms-border);
}
@media (max-width: 640px) {
  .dns-toolbar { padding: 0.85rem; }
  .pc-actions { grid-template-columns: 1fr; }
}
</style>
