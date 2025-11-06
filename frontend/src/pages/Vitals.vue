<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Record Vitals</div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-gutter-md">
          <q-input
            v-model="selectedDate"
            filled
            type="date"
            label="Select Date"
            class="col-12 col-md-4"
            @update:model-value="loadEncounters"
          />
          <q-input
            v-model="cardSearch"
            filled
            label="Filter by Card Number"
            class="col-12 col-md-4"
            clearable
          />
          <q-btn
            icon="today"
            label="Today"
            @click="setToday"
            color="primary"
            class="col-12 col-md-2 glass-button"
          />
          <q-space />
          <q-badge color="primary" :label="`${encounters.length} encounters`" />
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Encounters for {{ formattedDate }}</div>
        
        <q-table
          v-if="encounters.length > 0"
          :rows="filteredEncounters"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
        >
          <template v-slot:body-cell-time="props">
            <q-td :props="props">
              {{ formatTime(props.value) }}
            </q-td>
          </template>
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-has_vitals="props">
            <q-td :props="props">
              <q-icon 
                v-if="props.value" 
                name="check_circle" 
                color="positive" 
                size="sm"
                title="Vitals Recorded"
              />
              <q-icon 
                v-else 
                name="radio_button_unchecked" 
                color="grey" 
                size="sm"
                title="No Vitals"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                size="sm"
                :color="props.row.has_vitals ? 'secondary' : 'primary'"
                :icon="props.row.has_vitals ? 'edit' : 'add_circle'"
                :label="props.row.has_vitals ? 'Edit Vitals' : 'Record Vitals'"
                @click="recordVitals(props.row)"
                class="q-mr-xs"
              />
            </q-td>
          </template>
        </q-table>

        <div v-else class="text-center q-pa-lg text-grey-6">
          <q-icon name="event_busy" size="64px" />
          <div class="text-h6 q-mt-md">No encounters found for this date</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Vitals Form Dialog -->
    <q-dialog v-model="showVitalsDialog" persistent>
      <q-card style="min-width: 700px; max-width: 900px">
      <q-card-section>
          <div class="text-h6">Record Vitals - Encounter #{{ selectedEncounter?.id }}</div>
          <div class="row q-gutter-md q-mt-md">
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Patient:</strong> {{ selectedEncounter?.patient_name || 'N/A' }}</div>
              <div class="text-body2"><strong>Card Number:</strong> {{ selectedEncounter?.patient_card_number || 'N/A' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Age:</strong> {{ selectedEncounter?.patient_age ? `${selectedEncounter.patient_age} years` : 'N/A' }}</div>
              <div class="text-body2"><strong>Sex:</strong> {{ selectedEncounter?.patient_gender === 'M' ? 'Male' : selectedEncounter?.patient_gender === 'F' ? 'Female' : selectedEncounter?.patient_gender || 'N/A' }}</div>
            </div>
          </div>
          <div class="row q-gutter-md q-mt-xs">
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Insurance Number:</strong> {{ selectedEncounter?.patient_insurance_id || 'N/A' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Address:</strong> {{ selectedEncounter?.patient_address || 'N/A' }}</div>
            </div>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
        <q-form @submit="onSubmit" class="q-gutter-md">
          <div class="row q-gutter-md">
              <q-input 
                v-model="vitalsForm.bp" 
                filled 
                label="Blood Pressure (e.g., 120/80)" 
                class="col-12 col-md-6" 
                hint="e.g., 120/80"
              />
              <q-input 
                v-model.number="vitalsForm.temperature" 
                filled 
                type="number" 
                label="Temperature (°C)" 
                class="col-12 col-md-6" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-input 
                v-model.number="vitalsForm.pulse" 
                filled 
                type="number" 
                label="Pulse (bpm)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.respiration" 
                filled 
                type="number" 
                label="Respiration (breaths/min)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.weight" 
                filled 
                type="number" 
                label="Weight (kg)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.height" 
                filled 
                type="number" 
                label="Height (cm)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-input 
                v-model.number="vitalsForm.bmi" 
                filled 
                type="number" 
                label="BMI" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.spo2" 
                filled 
                type="number" 
                label="SPO2 (%)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.rbs" 
                filled 
                type="number" 
                label="Random Blood Sugar (mmol/L)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.fbs" 
                filled 
                type="number" 
                label="Fasting Blood Sugar (mmol/L)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-select 
                v-model="vitalsForm.upt" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="UPT" 
                class="col-12 col-md-4" 
                clearable 
              />
              <q-select 
                v-model="vitalsForm.rdt_malaria" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="RDT for Malaria" 
                class="col-12 col-md-4" 
                clearable 
              />
              <q-select 
                v-model="vitalsForm.retro_rdt" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="Retro RDT" 
                class="col-12 col-md-4" 
                clearable 
              />
          </div>

          <q-input
            v-model="vitalsForm.remarks"
            filled
            label="Remarks"
            type="textarea"
            rows="3"
          />

            <div class="row justify-end q-gutter-sm q-mt-md">
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="closeVitalsDialog"
              />
            <q-btn
                label="Save Vitals"
              type="submit"
              color="primary"
              :loading="saving"
                icon="save"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { vitalsAPI, encountersAPI, patientsAPI } from '../services/api';
import { useQuasar } from 'quasar';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();

const selectedDate = ref('');
const encounters = ref([]);
const loading = ref(false);
const cardSearch = ref('');
const showVitalsDialog = ref(false);
const selectedEncounter = ref(null);
const saving = ref(false);

const columns = [
  { name: 'time', label: 'Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'patient_name', label: 'Patient Name', field: 'patient_name', align: 'left' },
  { name: 'card_number', label: 'Card Number', field: 'patient_card_number', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'has_vitals', label: 'Vitals', field: 'has_vitals', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const testOptions = [
  { label: 'Negative', value: 'negative' },
  { label: 'Positive', value: 'positive' }
];

const formattedDate = computed(() => {
  if (!selectedDate.value) return 'Select a date';
  const date = new Date(selectedDate.value);
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
});

const filteredEncounters = computed(() => {
  const needle = (cardSearch.value || '').toLowerCase().trim();
  if (!needle) return encounters.value;
  return encounters.value.filter(e => (e.patient_card_number || '').toLowerCase().includes(needle));
});

const setToday = () => {
  const today = new Date();
  selectedDate.value = today.toISOString().split('T')[0];
  loadEncounters();
};

const formatTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};

const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    in_consultation: 'blue',
    awaiting_services: 'purple',
    finalized: 'green',
  };
  return colors[status] || 'grey';
};

const loadEncounters = async () => {
  if (!selectedDate.value) {
    encounters.value = [];
    return;
  }

  loading.value = true;
  try {
    // Load encounters for the date using encounters API
    const response = await encountersAPI.getByDate(selectedDate.value);
    const encountersList = response.data || [];
    
    // Check vitals status for each encounter
    const encountersWithVitals = await Promise.all(
      encountersList.map(async (encounter) => {
        try {
          // Try to get vitals for this encounter
          const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
          return {
            ...encounter,
            has_vitals: true,
            vitals_id: vitalsResponse.data?.id || null,
          };
        } catch (error) {
          // If 404, vitals don't exist for this encounter
          return {
            ...encounter,
            has_vitals: false,
            vitals_id: null,
          };
        }
      })
    );
    
    encounters.value = encountersWithVitals;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    encounters.value = [];
  } finally {
    loading.value = false;
  }
};

const recordVitals = async (encounter) => {
  selectedEncounter.value = encounter;
  
  try {
    // Always fetch full patient details to ensure we have the latest data
    if (encounter.patient_card_number) {
      try {
        const patientResponse = await patientsAPI.getByCard(encounter.patient_card_number);
        let patients = [];
        if (Array.isArray(patientResponse.data)) {
          patients = patientResponse.data;
        } else if (patientResponse.data && typeof patientResponse.data === 'object' && !Array.isArray(patientResponse.data)) {
          patients = [patientResponse.data];
        }
        
        if (patients.length > 0) {
          const patient = patients[0];
          // Update encounter with full patient details
          selectedEncounter.value = {
            ...encounter,
            patient_name: patient.name + (patient.surname ? ' ' + patient.surname : ''),
            patient_card_number: patient.card_number,
            patient_age: patient.age,
            patient_gender: patient.gender,
            patient_insurance_id: patient.insurance_id,
            patient_address: patient.address,
          };
        }
      } catch (patientError) {
        console.warn('Failed to fetch patient details:', patientError);
        // Continue even if patient fetch fails - use data from encounter
      }
    }
    
    // Load existing vitals if available
    if (encounter.has_vitals) {
      const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
      const vitals = vitalsResponse.data;
      Object.assign(vitalsForm, {
        encounter_id: encounter.id,
        vitals_id: vitals.id,
        bp: vitals.bp || '',
        temperature: vitals.temperature || null,
        pulse: vitals.pulse || null,
        respiration: vitals.respiration || null,
        weight: vitals.weight || null,
        height: vitals.height || null,
        bmi: vitals.bmi || null,
        spo2: vitals.spo2 || null,
        rbs: vitals.rbs || null,
        fbs: vitals.fbs || null,
        upt: vitals.upt || null,
        rdt_malaria: vitals.rdt_malaria || null,
        retro_rdt: vitals.retro_rdt || null,
        remarks: vitals.remarks || '',
      });
    } else {
      // Reset form for new vitals
      Object.assign(vitalsForm, {
        encounter_id: encounter.id,
        vitals_id: null,
        bp: '',
        temperature: null,
        pulse: null,
        respiration: null,
        weight: null,
        height: null,
        bmi: null,
        spo2: null,
        rbs: null,
        fbs: null,
        upt: null,
        rdt_malaria: null,
        retro_rdt: null,
        remarks: '',
      });
    }
    
    showVitalsDialog.value = true;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load vitals',
    });
  }
};

const closeVitalsDialog = () => {
  showVitalsDialog.value = false;
  selectedEncounter.value = null;
};

const vitalsForm = reactive({
  encounter_id: null,
  vitals_id: null, // ID of existing vitals if updating
  bp: '',
  temperature: null,
  pulse: null,
  respiration: null,
  weight: null,
  height: null,
  bmi: null,
  spo2: null,
  rbs: null,
  fbs: null,
  upt: null,
  rdt_malaria: null,
  retro_rdt: null,
  remarks: '',
});

const onSubmit = async () => {
  if (!vitalsForm.encounter_id) {
    $q.notify({
      type: 'warning',
      message: 'Please select an encounter first',
    });
    return;
  }

  saving.value = true;
  try {
    // Prepare form data (exclude vitals_id from payload - backend handles create/update automatically)
    const { vitals_id, ...createData } = vitalsForm;
    
    // Backend create endpoint handles both create and update automatically
    await vitalsAPI.create(createData);
    
    $q.notify({ 
      type: 'positive', 
      message: vitals_id ? 'Vitals updated successfully' : 'Vitals recorded successfully',
      position: 'top'
    });
    
    closeVitalsDialog();
    await loadEncounters(); // Reload encounters to update vitals status
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save vitals',
      position: 'top'
    });
  } finally {
    saving.value = false;
  }
};

// Auto-load encounter from route query parameter
const autoLoadFromRoute = async () => {
  if (route.query.encounterId) {
    const encounterId = parseInt(route.query.encounterId);
    
    try {
      // Get encounter details
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      
      if (encounter) {
        // Set the date to the encounter's date
        const encounterDate = new Date(encounter.created_at);
        const dateStr = encounterDate.toISOString().split('T')[0];
        selectedDate.value = dateStr;
        
        // Load encounters for that date
        await loadEncounters();
        
        // Find the specific encounter in the loaded list
        const foundEncounter = encounters.value.find(e => e.id === encounterId);
        
        if (foundEncounter) {
          // Automatically open the vitals dialog for this encounter
          await recordVitals(foundEncounter);
        } else {
          $q.notify({
            type: 'warning',
            message: 'Encounter found but not in the encounters list for that date',
          });
        }
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
      // Still set today's date so the page is usable
      setToday();
    }
  } else {
    // No encounterId in route, set today's date normally
    setToday();
  }
};

// Watch for route query changes
watch(() => route.query.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

onMounted(() => {
  autoLoadFromRoute();
});
</script>
