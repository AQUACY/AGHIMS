<template>
  <q-page class="q-pa-md" style="background: #f5f5f5;">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back"
        @click="$router.back()"
        class="q-mr-md"
      />
      <div class="text-h5 text-weight-bold">Lab Result Report</div>
      <q-space />
      <q-btn
        flat
        icon="print"
        label="Print"
        color="primary"
        @click="printResult"
      />
    </div>

    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner color="primary" size="3em" />
      <div class="text-body1 q-mt-md">Loading lab result...</div>
    </div>

    <div v-else-if="error" class="text-center q-pa-xl">
      <q-icon name="error" size="3em" color="negative" />
      <div class="text-body1 q-mt-md text-negative">{{ error }}</div>
      <q-btn
        flat
        label="Go Back"
        color="primary"
        @click="$router.back()"
        class="q-mt-md"
      />
    </div>

    <div v-else-if="investigationResult && labResultTemplate" class="lab-result-container">
      <LabResultViewer
        :template-structure="labResultTemplate.template_structure"
        :template-data="templateData"
        :results-text="investigationResult.results_text"
        :patient-info="patientInfo"
        :procedure-name="investigation?.procedure_name || ''"
        :template-name="labResultTemplate.template_name"
        :result-date="investigationResult.created_at"
        :entered-by="investigationResult.entered_by_name"
        :entered-at="investigationResult.created_at"
      />
    </div>

    <div v-else-if="investigationResult" class="lab-result-container">
      <!-- Fallback for non-template results -->
      <q-card>
        <q-card-section>
          <div class="text-h5 q-mb-md">{{ investigation?.procedure_name || 'Lab Result' }}</div>
          <div v-if="patientInfo" class="q-mb-md">
            <div class="row q-gutter-md">
              <div class="col-12 col-md-3">
                <strong>Patient:</strong> {{ patientInfo.name }} {{ patientInfo.surname }}
              </div>
              <div class="col-12 col-md-3">
                <strong>Card Number:</strong> {{ patientInfo.card_number || 'N/A' }}
              </div>
              <div class="col-12 col-md-3">
                <strong>Age:</strong> {{ patientInfo.age || 'N/A' }}
              </div>
              <div class="col-12 col-md-3">
                <strong>Sex:</strong> {{ patientInfo.gender || 'N/A' }}
              </div>
            </div>
          </div>
          <q-separator class="q-my-md" />
          <div class="text-body1" style="white-space: pre-wrap;">
            {{ investigationResult.results_text || 'No results available.' }}
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { consultationAPI, labTemplatesAPI, patientsAPI, encountersAPI } from '../services/api';
import { useQuasar } from 'quasar';
import LabResultViewer from '../components/LabResultViewer.vue';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref(null);
const investigationResult = ref(null);
const labResultTemplate = ref(null);
const investigation = ref(null);
const patientInfo = ref(null);

const templateData = computed(() => {
  if (!investigationResult.value?.template_data) return null;
  
  if (typeof investigationResult.value.template_data === 'string') {
    try {
      return JSON.parse(investigationResult.value.template_data);
    } catch (e) {
      console.error('Failed to parse template_data:', e);
      return null;
    }
  }
  
  return investigationResult.value.template_data;
});

const loadLabResult = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const investigationId = parseInt(route.params.investigationId);
    
    if (!investigationId) {
      error.value = 'Invalid investigation ID';
      return;
    }
    
    // Load investigation details
    const encounterId = route.query.encounterId;
    if (encounterId) {
      const encounterResponse = await encountersAPI.get(encounterId);
      const investigations = encounterResponse.data.investigations || [];
      investigation.value = investigations.find(inv => inv.id === investigationId);
    }
    
    // Load lab result
    const resultResponse = await consultationAPI.getLabResult(investigationId);
    investigationResult.value = resultResponse.data;
    
    if (!investigationResult.value) {
      error.value = 'Lab result not found';
      return;
    }
    
    // Load template if template_id exists
    if (investigationResult.value.template_id) {
      try {
        const templateResponse = await labTemplatesAPI.get(investigationResult.value.template_id);
        labResultTemplate.value = templateResponse.data;
      } catch (templateError) {
        console.error('Failed to load template:', templateError);
        // Continue without template
      }
    }
    
    // Load patient info
    const patientId = route.query.patientId || investigationResult.value.patient_id;
    if (patientId) {
      try {
        const patientResponse = await patientsAPI.get(patientId);
        patientInfo.value = patientResponse.data;
      } catch (patientError) {
        console.error('Failed to load patient info:', patientError);
        // Continue without patient info
      }
    }
    
  } catch (err) {
    console.error('Failed to load lab result:', err);
    error.value = err.response?.data?.detail || 'Failed to load lab result';
  } finally {
    loading.value = false;
  }
};

const printResult = () => {
  window.print();
};

onMounted(() => {
  loadLabResult();
});
</script>

<style scoped>
.lab-result-container {
  max-width: 210mm; /* A4 width */
  margin: 0 auto;
  background: white;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

@media print {
  /* A4 Page setup */
  @page {
    size: A4;
    margin: 20mm 15mm;
  }
  
  html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
  }
  
  .lab-result-container {
    width: 180mm; /* 210mm - 30mm (left + right margins) */
    min-height: 257mm; /* 297mm - 40mm (top + bottom margins) */
    margin: 0 auto;
    padding: 0;
    box-shadow: none;
    background: white;
    position: relative;
  }
  
  .q-page {
    background: white;
    padding: 0;
    margin: 0;
    width: 210mm;
    height: 297mm;
  }
  
  /* Hide buttons when printing */
  .q-btn,
  button,
  .row.items-center,
  .no-print {
    display: none !important;
  }
}
</style>

