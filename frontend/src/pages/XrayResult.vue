<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to X-ray"
        @click="$router.push('/xray')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">X-ray Result Entry</div>
    </div>

    <!-- Patient Information -->
    <q-card v-if="investigation && patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Patient Information</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1 text-weight-medium">{{ patient.name }} {{ patient.surname || '' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Card Number</div>
            <div class="text-body1 text-weight-medium">{{ patient.card_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">CCC Number</div>
            <div class="text-body1 text-weight-medium">{{ patient.ccc_number || encounter?.ccc_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance Status</div>
            <div class="text-body1 text-weight-medium">
              <q-badge :color="patient.insured ? 'positive' : 'grey'" :label="patient.insured ? 'Insured' : 'Not Insured'" />
            </div>
          </div>
        </div>
        <div class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Date of Birth</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.date_of_birth) }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Age</div>
            <div class="text-body1 text-weight-medium">{{ patient.age || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Sex</div>
            <div class="text-body1 text-weight-medium">{{ patient.gender || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Encounter Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDate(encounter?.created_at) || 'N/A' }}</div>
          </div>
        </div>
        <div v-if="patient.insured && patient.insurance_id" class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance ID</div>
            <div class="text-body1 text-weight-medium">{{ patient.insurance_id || 'N/A' }}</div>
          </div>
          <div v-if="patient.insurance_start_date" class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance Start Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.insurance_start_date) }}</div>
          </div>
          <div v-if="patient.insurance_end_date" class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance End Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.insurance_end_date) }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigation Details -->
    <q-card v-if="investigation" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Investigation Details</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-6">
            <div class="text-caption text-grey-7">Procedure Name</div>
            <div class="text-body1 text-weight-medium">{{ investigation.procedure_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-caption text-grey-7">G-DRG Code</div>
            <div class="text-body1 text-weight-medium">{{ investigation.gdrg_code || 'N/A' }}</div>
          </div>
        </div>
        <div v-if="investigation.notes" class="row q-mt-md">
          <div class="col-12">
            <div class="text-caption text-grey-7">Doctor's Notes</div>
            <div class="text-body2 q-pa-sm" style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px;">
              {{ investigation.notes }}
            </div>
          </div>
        </div>
        <div class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Confirmed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.confirmed_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Completed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.completed_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Entered By</div>
            <div class="text-body1 text-weight-medium">{{ xrayResult?.entered_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Updated By</div>
            <div class="text-body1 text-weight-medium">{{ xrayResult?.updated_by_name || 'N/A' }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- X-ray Result Form -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          {{ editingResult ? 'Edit X-ray Result' : 'Add X-ray Result' }}
        </div>
        <q-banner
          v-if="investigation?.status === 'completed' && !canEditResult"
          class="bg-warning text-dark q-mb-md"
          rounded
        >
          <template v-slot:avatar>
            <q-icon name="warning" color="dark" />
          </template>
          This investigation is completed. Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status if changes are needed.
        </q-banner>
        <q-form @submit="saveXrayResult" class="q-gutter-md">
          <q-input
            v-model="resultForm.results_text"
            filled
            type="textarea"
            rows="10"
            label="Results Text"
            hint="Enter x-ray results/findings"
            :rules="[(val) => !!val || 'Results text is required']"
          />
          <q-file
            v-model="resultForm.attachment"
            filled
            label="Upload PDF/Attachment"
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
            hint="Upload PDF, Word document, or image file"
            @update:model-value="onFileSelected"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
          <div v-if="resultForm.existingAttachment" class="text-caption text-grey-7 q-mt-sm">
            Current attachment: {{ resultForm.existingAttachment.split('/').pop() }}
            <q-btn
              flat
              dense
              size="sm"
              icon="download"
              label="Download"
              @click="downloadExistingAttachment"
              class="q-ml-sm"
            />
          </div>
          <div class="row q-gutter-md q-mt-md">
            <q-btn
              label="Cancel"
              flat
              @click="$router.push('/xray')"
              class="col"
            />
            <q-btn
              label="Save"
              type="submit"
              color="primary"
              class="col"
              :loading="savingResult"
              :disable="!canEditResult"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, encountersAPI, patientsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const investigation = ref(null);
const patient = ref(null);
const encounter = ref(null);
const xrayResult = ref(null);
const loading = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);

// Check if user can edit result (Admin and Xray Head can edit completed investigations)
const canEditResult = computed(() => {
  if (!investigation.value) return true;
  // If investigation is completed, only Admin and Xray Head can edit
  if (investigation.value.status === 'completed') {
    return authStore.userRole === 'Admin' || authStore.userRole === 'Xray Head';
  }
  // For non-completed investigations, all Xray staff can edit
  return true;
});

const resultForm = ref({
  investigation_id: null,
  results_text: '',
  attachment: null,
  existingAttachment: null,
});

const loadInvestigation = async () => {
  const investigationId = route.params.investigationId;
  if (!investigationId) {
    $q.notify({
      type: 'negative',
      message: 'Investigation ID is required',
    });
    router.push('/xray');
    return;
  }

  loading.value = true;
  try {
    // Load investigation details - try OPD first, then IPD
    let invResponse;
    try {
      invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
      investigation.value = invResponse.data;
    } catch (opdError) {
      // If OPD fails with 404, try IPD
      if (opdError.response?.status === 404) {
        try {
          invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
          investigation.value = invResponse.data;
        } catch (ipdError) {
          $q.notify({
            type: 'negative',
            message: 'Investigation not found',
          });
          router.push('/xray');
          return;
        }
      } else {
        throw opdError;
      }
    }
    
    if (!investigation.value) {
      $q.notify({
        type: 'negative',
        message: 'Investigation not found',
      });
      router.push('/xray');
      return;
    }

    // Load encounter details (only for OPD investigations)
    if (investigation.value.encounter_id && investigation.value.source !== 'inpatient') {
      try {
        const encounterResponse = await encountersAPI.get(investigation.value.encounter_id);
        encounter.value = encounterResponse.data;
      } catch (error) {
        console.error('Failed to load encounter:', error);
      }
    } else if (investigation.value.source === 'inpatient' && investigation.value.encounter_id) {
      // For IPD, we can still load the encounter if needed
      try {
        const encounterResponse = await encountersAPI.get(investigation.value.encounter_id);
        encounter.value = encounterResponse.data;
      } catch (error) {
        console.error('Failed to load encounter:', error);
      }
    }
    
    // Load patient details using card number from investigation
    if (investigation.value.patient_card_number) {
      try {
        const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
        const patients = patientResponse.data || [];
        if (patients.length > 0) {
          // getByCard returns a list, get the first match
          patient.value = patients[0];
        } else {
          throw new Error('Patient not found');
        }
      } catch (error) {
        console.error('Failed to load patient:', error);
        // Fallback: use patient info from investigation response
        if (investigation.value.patient_name) {
          const nameParts = investigation.value.patient_name.split(' ');
          patient.value = {
            card_number: investigation.value.patient_card_number,
            name: nameParts[0] || 'N/A',
            surname: nameParts.slice(1).join(' ') || '',
            ccc_number: encounter.value?.ccc_number || null,
            date_of_birth: null,
            age: null,
            gender: null,
            insured: false,
            insurance_id: null,
          };
        }
      }
    }

    // Check if result already exists
    try {
      const resultResponse = await consultationAPI.getXrayResult(investigation.value.id);
      xrayResult.value = resultResponse.data;
      const existingResult = resultResponse.data;
      if (existingResult) {
        editingResult.value = true;
        resultForm.value = {
          investigation_id: investigation.value.id,
          results_text: existingResult.results_text || '',
          attachment: null,
          existingAttachment: existingResult.attachment_path || null,
        };
      } else {
        resultForm.value = {
          investigation_id: investigation.value.id,
          results_text: '',
          attachment: null,
          existingAttachment: null,
        };
      }
    } catch (error) {
      // No result exists yet
      resultForm.value = {
        investigation_id: investigation.value.id,
        results_text: '',
        attachment: null,
        existingAttachment: null,
      };
    }
  } catch (error) {
    console.error('Failed to load investigation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigation details',
    });
    router.push('/xray');
  } finally {
    loading.value = false;
  }
};

const onFileSelected = (file) => {
  // File is automatically set in resultForm.attachment
};

const saveXrayResult = async () => {
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

    await consultationAPI.createXrayResult(formData);
    $q.notify({
      type: 'positive',
      message: 'X-ray result saved successfully',
    });
    router.push('/xray');
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save x-ray result',
    });
  } finally {
    savingResult.value = false;
  }
};

const downloadExistingAttachment = async () => {
  if (!resultForm.value.existingAttachment || !resultForm.value.investigation_id) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to download',
    });
    return;
  }

  try {
    const response = await consultationAPI.downloadXrayResultAttachment(resultForm.value.investigation_id);
    
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = resultForm.value.existingAttachment.split('/').pop() || 'xray_result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
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

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatDateOnly = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
};

onMounted(() => {
  loadInvestigation();
});
</script>

