<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Lab Services</div>

    <!-- Patient Search -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Search Patient</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="cardNumber"
            filled
            label="Patient Card Number"
            class="col-12 col-md-8"
            @keyup.enter="searchPatient"
            :disable="loadingPatient"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchPatient"
            class="col-12 col-md-4 glass-button"
            :loading="loadingPatient"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Patient Info & Encounter Selection -->
    <q-card v-if="patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div>
            <div class="text-h6 glass-text">{{ patient.name }} {{ patient.surname || '' }}</div>
            <div class="text-grey-7">Card: {{ patient.card_number }}</div>
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Clear"
            @click="clearSearch"
          />
        </div>

        <!-- Encounter Selection -->
        <div v-if="activeEncounters.length > 0" class="q-mt-md">
          <div class="text-subtitle1 q-mb-sm">Select Encounter:</div>
          <q-select
            v-model="selectedEncounterId"
            :options="activeEncounters"
            option-value="id"
            option-label="label"
            filled
            label="Encounter"
            emit-value
            map-options
            @update:model-value="loadInvestigations"
          />
        </div>
        <div v-else class="text-grey-7 q-mt-md">
          No active encounters found for this patient
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigations Table -->
    <q-card v-if="selectedEncounterId" class="q-mb-md">
          <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6">Lab Investigations</div>
          <q-space />
          <q-badge v-if="isFinalized" color="orange" label="Encounter Finalized - Read Only" />
        </div>
        <q-table
          v-if="investigations.length > 0"
          :rows="investigations"
          :columns="investigationColumns"
          row-key="id"
          flat
          :loading="loadingInvestigations"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="props.row.status !== 'confirmed' && props.row.status !== 'completed'"
                size="sm"
                color="primary"
                label="Confirm"
                @click="confirmInvestigation(props.row)"
                :loading="confirmingId === props.row.id"
                :disable="confirmingId !== null || isFinalized"
              />
              <q-badge
                v-else
                color="positive"
                label="Confirmed"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else-if="!loadingInvestigations" class="text-center text-grey-7 q-pa-md">
          No lab investigations found for this encounter
        </div>
      </q-card-section>
    </q-card>

    <!-- Lab Results Table -->
    <q-card v-if="selectedEncounterId && confirmedInvestigations.length > 0" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Lab Results</div>
        <q-table
          :rows="labResults"
          :columns="labResultColumns"
          row-key="investigation_id"
          flat
          :loading="loadingResults"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                size="sm"
                color="primary"
                :label="props.row.id ? 'Edit' : 'Add Results'"
                @click="openResultDialog(props.row)"
                :disable="isFinalized"
              />
              <q-btn
                v-if="props.row.attachment_path"
                size="sm"
                color="secondary"
                icon="download"
                flat
                @click="downloadAttachment(props.row)"
                class="q-ml-xs"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Lab Result Dialog -->
    <q-dialog v-model="showResultDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">
            {{ editingResult ? 'Edit Lab Result' : 'Add Lab Result' }}
          </div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            {{ selectedInvestigation.procedure_name || 'Lab Investigation' }} ({{ selectedInvestigation.gdrg_code }})
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveLabResult" class="q-gutter-md">
            <q-input
              v-model="resultForm.results_text"
              filled
              type="textarea"
              rows="6"
              label="Results Text"
              hint="Enter lab results from analyzer"
            />
            <q-file
              v-model="resultForm.attachment"
              filled
              label="Upload PDF/Attachment"
              accept=".pdf,.jpg,.jpeg,.png"
              hint="Upload PDF or image file from analyzer"
              @update:model-value="onFileSelected"
            >
              <template v-slot:prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>
            <div v-if="resultForm.existingAttachment" class="text-caption text-grey-7">
              Current attachment: {{ resultForm.existingAttachment.split('/').pop() }}
            </div>
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Save"
                type="submit"
                color="primary"
                class="col"
                :loading="savingResult"
                :disable="isFinalized"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, patientsAPI, encountersAPI } from '../services/api';

const $q = useQuasar();
const route = useRoute();
const cardNumber = ref('');
const loadingPatient = ref(false);
const patient = ref(null);
const activeEncounters = ref([]);
const selectedEncounterId = ref(null);
const currentEncounter = ref(null);
const investigations = ref([]);
const loadingInvestigations = ref(false);
const confirmingId = ref(null);
const labResults = ref([]);
const loadingResults = ref(false);
const showResultDialog = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);
const selectedInvestigation = ref(null);
const resultForm = ref({
  investigation_id: null,
  results_text: '',
  attachment: null,
  existingAttachment: null,
});

const investigationColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const labResultColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'has_result', label: 'Has Results', field: 'has_result', align: 'center' },
  { name: 'has_attachment', label: 'Has Attachment', field: 'has_attachment', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const getStatusColor = (status) => {
  const colors = {
    requested: 'orange',
    confirmed: 'blue',
    completed: 'green',
  };
  return colors[status] || 'grey';
};

const confirmedInvestigations = computed(() => {
  return investigations.value.filter(inv => inv.status === 'confirmed' || inv.status === 'completed');
});

const isFinalized = computed(() => {
  return currentEncounter.value?.status === 'finalized';
});

const searchPatient = async () => {
  if (!cardNumber.value || !cardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  loadingPatient.value = true;
  try {
    const patientResponse = await patientsAPI.getByCard(cardNumber.value.trim());
    
    // getByCard returns a list of patients
    let patients = [];
    if (Array.isArray(patientResponse.data)) {
      patients = patientResponse.data;
    } else if (patientResponse.data && typeof patientResponse.data === 'object' && !Array.isArray(patientResponse.data)) {
      patients = [patientResponse.data];
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      return;
    }
    
    // Use the first patient (or exact match if available)
    patient.value = patients[0];

    const encountersResponse = await encountersAPI.getPatientEncounters(patient.value.id);
    activeEncounters.value = encountersResponse.data
      .filter(e => !e.archived)
      .map(e => ({
        id: e.id,
        label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
        value: e.id,
      }));

    if (activeEncounters.value.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No active encounters found for this patient',
      });
    } else if (activeEncounters.value.length === 1) {
      selectedEncounterId.value = activeEncounters.value[0].id;
      await loadInvestigations();
    }
  } catch (error) {
    patient.value = null;
    activeEncounters.value = [];
    selectedEncounterId.value = null;
    investigations.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Patient not found',
    });
  } finally {
    loadingPatient.value = false;
  }
};

const loadInvestigations = async () => {
  if (!selectedEncounterId.value || !patient.value) return;

  loadingInvestigations.value = true;
  try {
    // Load encounter details to check status
    const encounterResponse = await encountersAPI.get(selectedEncounterId.value);
    currentEncounter.value = encounterResponse.data;
    
    // Load investigations (filter by lab type)
    const response = await consultationAPI.getInvestigationsByPatientCard(
      patient.value.card_number,
      selectedEncounterId.value,
      'lab'
    );
    investigations.value = response.data || [];

    // Load lab results for confirmed investigations (after investigations are loaded)
    await loadLabResults();
  } catch (error) {
    investigations.value = [];
    labResults.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigations',
    });
  } finally {
    loadingInvestigations.value = false;
  }
};

const loadLabResults = async () => {
  if (!selectedEncounterId.value || confirmedInvestigations.value.length === 0) {
    labResults.value = [];
    return;
  }

  loadingResults.value = true;
  try {
    // Load lab results for confirmed investigations
    labResults.value = await Promise.all(
      confirmedInvestigations.value.map(async (inv) => {
        try {
          const resultResponse = await consultationAPI.getLabResult(inv.id);
          const result = resultResponse.data || null;
          
          return {
            investigation_id: inv.id,
            procedure_name: inv.procedure_name,
            gdrg_code: inv.gdrg_code,
            has_result: result ? 'Yes' : 'No',
            has_attachment: result?.attachment_path ? 'Yes' : 'No',
            ...result,
          };
        } catch (error) {
          return {
            investigation_id: inv.id,
            procedure_name: inv.procedure_name,
            gdrg_code: inv.gdrg_code,
            has_result: 'No',
            has_attachment: 'No',
          };
        }
      })
    );
  } catch (error) {
    labResults.value = [];
    console.error('Failed to load lab results:', error);
  } finally {
    loadingResults.value = false;
  }
};

const confirmInvestigation = async (investigation) => {
  $q.dialog({
    title: 'Confirm Investigation',
    message: `Confirm ${investigation.procedure_name || investigation.gdrg_code}?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    confirmingId.value = investigation.id;
    try {
      await consultationAPI.confirmInvestigation(investigation.id);
      $q.notify({
        type: 'positive',
        message: 'Investigation confirmed',
      });
      await loadInvestigations();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to confirm investigation',
      });
    } finally {
      confirmingId.value = null;
    }
  });
};

const openResultDialog = (result) => {
  selectedInvestigation.value = investigations.value.find(inv => inv.id === result.investigation_id);
  editingResult.value = !!result.id;
  resultForm.value = {
    investigation_id: result.investigation_id,
    results_text: result.results_text || '',
    attachment: null,
    existingAttachment: result.attachment_path || null,
  };
  showResultDialog.value = true;
};

const onFileSelected = (file) => {
  // File is automatically set in resultForm.attachment
};

const saveLabResult = async () => {
  if (!resultForm.value.investigation_id) return;

  savingResult.value = true;
  try {
    const formData = new FormData();
    formData.append('investigation_id', resultForm.value.investigation_id);
    if (resultForm.value.results_text) {
      formData.append('results_text', resultForm.value.results_text);
    }
    if (resultForm.value.attachment) {
      formData.append('attachment', resultForm.value.attachment);
    }

    await consultationAPI.createLabResult(formData);
    $q.notify({
      type: 'positive',
      message: 'Lab result saved successfully',
    });
    showResultDialog.value = false;
    // Reload investigations and results
    await loadInvestigations();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save lab result',
    });
  } finally {
    savingResult.value = false;
  }
};

const downloadAttachment = async (result) => {
  if (!result.attachment_path || !result.investigation_id) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to download',
    });
    return;
  }

  try {
    const response = await consultationAPI.downloadLabResultAttachment(result.investigation_id);
    
    // Axios with responseType: 'blob' returns data as Blob directly
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    // Get filename from Content-Disposition header or use attachment path
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = result.attachment_path.split('/').pop() || 'lab_result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);
    
    $q.notify({
      type: 'positive',
      message: 'File downloaded successfully',
    });
  } catch (error) {
    console.error('Download error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download attachment',
    });
  }
};

const clearSearch = () => {
  cardNumber.value = '';
  patient.value = null;
  activeEncounters.value = [];
  selectedEncounterId.value = null;
  currentEncounter.value = null;
  investigations.value = [];
  labResults.value = [];
};

// Auto-load from route query parameter
const autoLoadFromRoute = async () => {
  if (route.query.encounterId) {
    const encounterId = parseInt(route.query.encounterId);
    selectedEncounterId.value = encounterId;
    
    try {
      // Get encounter details to get patient info
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      currentEncounter.value = encounter;
      
      if (encounter && encounter.patient_id) {
        // Get patient info
        const patientResponse = await patientsAPI.get(encounter.patient_id);
        patient.value = patientResponse.data;
        cardNumber.value = patient.value.card_number;
        
        // Load all encounters for this patient
        const encountersResponse = await encountersAPI.getPatientEncounters(encounter.patient_id);
        const allEncounters = encountersResponse.data.filter(e => !e.archived);
        activeEncounters.value = allEncounters.map(e => ({
          id: e.id,
          label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
          value: e.id,
        }));
        
        // Load investigations for this encounter
        await loadInvestigations();
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
    }
  }
};

// Watch for route query changes
watch(() => route.query.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

// Auto-load on mount
onMounted(() => {
  autoLoadFromRoute();
});
</script>
