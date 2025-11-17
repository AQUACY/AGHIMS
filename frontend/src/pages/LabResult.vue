<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Lab"
        @click="$router.push('/lab')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">Lab Result Entry</div>
    </div>

    <!-- Patient Information -->
    <q-card v-if="investigation && patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Patient Information</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1 text-weight-medium">{{ patient.name }} {{ patient.surname || '' }}<span v-if="patient.other_names"> {{ patient.other_names }}</span></div>
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
        <div v-if="encounterBillInfo.totalAmount !== null" class="row q-gutter-md q-mt-md">
          <div class="col-12">
            <div class="text-body2" :class="encounterBillInfo.remainingBalance > 0 ? 'text-negative text-weight-bold' : 'text-secondary'">
              <q-icon name="receipt" size="14px" class="q-mr-xs" />
              <strong>Total Bills:</strong> GHC {{ encounterBillInfo.totalAmount.toFixed(2) }} 
              <span v-if="encounterBillInfo.remainingBalance > 0" class="text-negative">
                | Outstanding: GHC {{ encounterBillInfo.remainingBalance.toFixed(2) }}
              </span>
              <span v-else>
                | Outstanding: GHC 0.00
              </span>
            </div>
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
          <div v-if="investigation.confirmed_by_name" class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Confirmed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.confirmed_by_name || 'N/A' }}</div>
          </div>
          <div v-if="investigation.completed_by_name" class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Completed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.completed_by_name || 'N/A' }}</div>
          </div>
          <div v-if="labResult?.entered_by_name" class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Entered By</div>
            <div class="text-body1 text-weight-medium">{{ labResult.entered_by_name || 'N/A' }}</div>
          </div>
          <div v-if="labResult?.updated_by_name" class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Updated By</div>
            <div class="text-body1 text-weight-medium">{{ labResult.updated_by_name || 'N/A' }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Lab Result Form -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          {{ editingResult ? 'Edit Lab Result' : 'Add Lab Result' }}
        </div>
        <q-banner
          v-if="investigation?.status === 'completed' && !canEditResult"
          class="bg-warning text-dark q-mb-md"
          rounded
        >
          <template v-slot:avatar>
            <q-icon name="warning" color="dark" />
          </template>
          This investigation is completed. Only Admin and Lab Head can edit completed investigations. Please contact Lab Head to revert the status if changes are needed.
        </q-banner>
        <q-form @submit="saveLabResult" class="q-gutter-md">
          <q-input
            v-model="resultForm.results_text"
            filled
            type="textarea"
            rows="10"
            label="Results Text"
            hint="Enter lab results from analyzer"
            :rules="[(val) => !!val || 'Results text is required']"
          />
          <q-file
            v-model="resultForm.attachment"
            filled
            label="Upload PDF/Attachment"
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
            hint="Upload PDF, Word document, or image file from analyzer"
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
              @click="$router.push('/lab')"
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
import { consultationAPI, encountersAPI, patientsAPI, billingAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const investigation = ref(null);
const patient = ref(null);
const encounter = ref(null);
const labResult = ref(null);
const loading = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);
const encounterBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});

// Check if user can edit result (Admin and Lab Head can edit completed investigations)
const canEditResult = computed(() => {
  if (!investigation.value) return true;
  // If investigation is completed, only Admin and Lab Head can edit
  if (investigation.value.status === 'completed') {
    return authStore.userRole === 'Admin' || authStore.userRole === 'Lab Head';
  }
  // For non-completed investigations, all Lab staff can edit
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
  const source = route.query.source; // 'opd' or 'inpatient' from query param
  const expectedCardNumber = route.query.card_number; // Expected patient card number
  
  if (!investigationId) {
    $q.notify({
      type: 'negative',
      message: 'Investigation ID is required',
    });
    router.push('/lab');
    return;
  }

  loading.value = true;
  try {
    let invResponse;
    let isInpatient = false;
    
    // If source is specified in query params, use it to determine which API to call first
    if (source === 'inpatient') {
      // Try IPD first if source indicates inpatient
      try {
        invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = true;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (ipdError) {
        if (ipdError.message === 'Patient mismatch' || (expectedCardNumber && ipdError.response?.status !== 404)) {
          // Patient doesn't match or other error - try OPD
          try {
            invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = false;
            
            // Verify patient card number matches
            if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
              throw new Error('Investigation not found for this patient');
            }
          } catch (opdError) {
            $q.notify({
              type: 'negative',
              message: 'Investigation not found or patient mismatch',
            });
            router.push('/lab');
            return;
          }
        } else {
          throw ipdError;
        }
      }
    } else {
      // Default: Try OPD first (most common case)
      try {
        invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = false;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (opdError) {
        // If OPD fails with 404 or patient mismatch, try IPD
        if (opdError.response?.status === 404 || opdError.message === 'Patient mismatch') {
          try {
            invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = true;
            
            // Verify patient card number matches
            if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
              throw new Error('Investigation not found for this patient');
            }
          } catch (ipdError) {
            $q.notify({
              type: 'negative',
              message: 'Investigation not found or patient mismatch',
            });
            router.push('/lab');
            return;
          }
        } else {
          throw opdError;
        }
      }
    }
    
    // Store investigation source for reference
    investigation.value.source = isInpatient ? 'inpatient' : 'opd';
    
    if (!investigation.value) {
      $q.notify({
        type: 'negative',
        message: 'Investigation not found',
      });
      router.push('/lab');
      return;
    }

    // Load encounter details first (for both OPD and IPD)
    if (investigation.value.encounter_id) {
      try {
        const encounterResponse = await encountersAPI.get(investigation.value.encounter_id);
        encounter.value = encounterResponse.data;
        
        // Load bills for this encounter
        await loadEncounterBills(encounter.value.id);
        
        // Verify encounter matches investigation's patient_card_number if available
        if (investigation.value.patient_card_number && encounter.value.patient_card_number) {
          if (investigation.value.patient_card_number !== encounter.value.patient_card_number) {
            console.warn(`Mismatch: Investigation patient card (${investigation.value.patient_card_number}) != Encounter patient card (${encounter.value.patient_card_number})`);
            $q.notify({
              type: 'warning',
              message: 'Warning: Patient information mismatch detected. Please verify the investigation belongs to this patient.',
            });
          }
        }
        
        // Load patient from encounter to ensure correct patient
        if (encounter.value && encounter.value.patient_id) {
          try {
            const patientResponse = await patientsAPI.get(encounter.value.patient_id);
            patient.value = patientResponse.data;
            
            // Double-check: verify patient card number matches investigation
            if (investigation.value.patient_card_number && patient.value.card_number) {
              if (investigation.value.patient_card_number !== patient.value.card_number) {
                console.error(`CRITICAL: Patient card mismatch! Investigation: ${investigation.value.patient_card_number}, Patient: ${patient.value.card_number}`);
                $q.notify({
                  type: 'negative',
                  message: `Error: Patient mismatch detected. Investigation is for ${investigation.value.patient_card_number} but encounter is for ${patient.value.card_number}`,
                });
              }
            }
          } catch (error) {
            console.error('Failed to load patient by ID:', error);
            // Fallback: try loading by card number from investigation
            if (investigation.value.patient_card_number) {
              try {
                const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
                const patients = patientResponse.data || [];
                if (patients.length > 0) {
                  // For IPD, prefer the patient that matches the encounter's patient_id if available
                  let correctPatient = patients[0];
                  if (encounter.value && encounter.value.patient_id) {
                    const matchingPatient = patients.find(p => p.id === encounter.value.patient_id);
                    if (matchingPatient) {
                      correctPatient = matchingPatient;
                    } else {
                      console.warn(`Patient from card lookup doesn't match encounter patient_id. Using first match.`);
                    }
                  }
                  patient.value = correctPatient;
                } else {
                  throw new Error('Patient not found');
                }
              } catch (cardError) {
                console.error('Failed to load patient by card:', cardError);
                // Final fallback: use patient info from investigation response
                if (investigation.value.patient_name) {
                  const nameParts = investigation.value.patient_name.split(' ');
                  patient.value = {
                    id: encounter.value?.patient_id || null,
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
          }
        }
      } catch (error) {
        console.error('Failed to load encounter:', error);
        // Fallback: try loading patient by card number from investigation
        if (investigation.value.patient_card_number) {
          try {
            const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
            const patients = patientResponse.data || [];
            if (patients.length > 0) {
              // For IPD investigations, we need to be more careful
              // If we have encounter_id but failed to load encounter, try to match by investigation's patient info
              patient.value = patients[0];
              console.warn('Loaded patient by card number as fallback - verify this is correct');
            }
          } catch (cardError) {
            console.error('Failed to load patient:', cardError);
          }
        }
      }
    } else {
      // No encounter_id - fallback to card number lookup
      if (investigation.value.patient_card_number) {
        try {
          const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
          const patients = patientResponse.data || [];
          if (patients.length > 0) {
            patient.value = patients[0];
          }
        } catch (error) {
          console.error('Failed to load patient:', error);
        }
      }
    }

    // Check if result already exists
    // IMPORTANT: Only load result if investigation is loaded correctly
    // The backend will check IPD first to prevent ID collisions
    try {
      const resultResponse = await consultationAPI.getLabResult(investigation.value.id);
      const existingResult = resultResponse.data;
      
      // Verify the result belongs to this investigation
      // (Backend should handle this, but double-check on frontend)
      if (existingResult && existingResult.investigation_id === investigation.value.id) {
        labResult.value = existingResult;
        editingResult.value = true;
        resultForm.value = {
          investigation_id: investigation.value.id,
          results_text: existingResult.results_text || '',
          attachment: null,
          existingAttachment: existingResult.attachment_path || null,
        };
      } else {
        // No result exists or mismatch - start fresh
        labResult.value = null;
        editingResult.value = false;
        resultForm.value = {
          investigation_id: investigation.value.id,
          results_text: '',
          attachment: null,
          existingAttachment: null,
        };
      }
    } catch (error) {
      // No result exists yet or error loading
      console.log('No lab result found for investigation:', investigation.value.id, 'Source:', investigation.value?.source || 'unknown', error);
      labResult.value = null;
      editingResult.value = false;
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
    router.push('/lab');
  } finally {
    loading.value = false;
  }
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
    router.push('/lab');
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save lab result',
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
    const response = await consultationAPI.downloadLabResultAttachment(resultForm.value.investigation_id);
    
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = resultForm.value.existingAttachment.split('/').pop() || 'lab_result.pdf';
    
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

