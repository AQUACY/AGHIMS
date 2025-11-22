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
          <!-- Sample ID Field - Always at the top, always enabled -->
          <div class="row q-gutter-md q-mb-md">
            <div class="col-12 col-md-8">
              <q-input
                v-model="templateData.sample_no"
                filled
                label="Sample ID"
                hint="Pre-generated sample ID for analyzer mapping (e.g., 251100001)"
                :disable="generatingSampleId"
              >
                <template v-slot:prepend>
                  <q-icon name="qr_code" />
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-4 flex flex-center">
              <q-btn
                label="Generate Sample ID"
                color="primary"
                icon="refresh"
                :loading="generatingSampleId"
                @click="generateAndSaveSampleId"
                class="full-width"
              />
            </div>
          </div>
          
          <!-- Template-based form -->
          <div v-if="usingTemplate && template">
            <div class="text-subtitle2 q-mb-md text-grey-7">
              Using template: {{ template.template_name }} ({{ template.procedure_name }})
            </div>
            
            <!-- Template fields grouped by group -->
            <template v-for="group in getTemplateGroups()" :key="group">
              <div v-if="group" class="text-subtitle1 q-mt-md q-mb-sm glass-text">{{ group }}</div>
              <div class="row q-gutter-md">
                <template v-for="field in getTemplateFieldsByGroup(group)" :key="field.name">
                  <div class="col-12 col-md-6">
                    <q-input
                      v-model.number="templateData.field_values[field.name]"
                      filled
                      :label="field.label"
                      :hint="`${field.unit || ''} ${getReferenceRange(field)}`"
                      :type="field.type === 'numeric' ? 'number' : 'text'"
                      step="0.01"
                      :disable="!canEnterResults"
                    >
                      <template v-slot:append v-if="isOutOfRange(field, templateData.field_values[field.name])">
                        <q-icon name="warning" color="negative" />
                      </template>
                    </q-input>
                  </div>
                </template>
              </div>
            </template>

            <!-- Message fields -->
            <div v-if="template.template_structure.message_fields && template.template_structure.message_fields.length > 0" class="q-mt-md">
              <div class="text-subtitle1 q-mb-sm glass-text">Messages</div>
              <template v-for="msgField in template.template_structure.message_fields" :key="msgField.name">
                <q-input
                  v-model="templateData.messages[msgField.name]"
                  filled
                  :type="msgField.type === 'textarea' ? 'textarea' : 'text'"
                  :rows="msgField.type === 'textarea' ? 3 : 1"
                  :label="msgField.label || msgField.name"
                  class="q-mb-md"
                />
              </template>
            </div>

            <!-- Payment Warning -->
            <q-banner
              v-if="!canEnterResults"
              class="bg-negative text-white q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="payment" />
              </template>
              <strong>Payment Required</strong>
              <div class="text-caption q-mt-xs">
                This investigation must be paid for before results can be entered. Please process payment at the billing desk.
              </div>
            </q-banner>
            
            <!-- Additional fields -->
            <div class="row q-gutter-md q-mt-md">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="templateData.validated_by"
                  filled
                  label="Validated By"
                  hint="Name of person validating the results"
                  :disable="!canEnterResults"
                />
              </div>
            </div>
          </div>

          <!-- Default form (no template) -->
          <div v-else>
            <q-input
              v-model="resultForm.results_text"
              filled
              type="textarea"
              rows="10"
              label="Results Text"
              hint="Enter lab results from analyzer"
              :rules="[(val) => !!val || 'Results text is required']"
            />
          </div>

          <!-- File upload (available for both template and non-template) -->
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
              :disable="!canEditResult || !canEnterResults"
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
import { consultationAPI, encountersAPI, patientsAPI, billingAPI, labTemplatesAPI } from '../services/api';
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
const template = ref(null);
const templateData = ref({ field_values: {}, messages: {}, validated_by: '', sample_no: '' });
const usingTemplate = ref(false);
const generatingSampleId = ref(false);
const encounterBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});
const bills = ref([]);
const isInvestigationPaid = ref(false);
const canEnterResults = computed(() => {
  // For IPD investigations, allow without payment check
  if (investigation.value?.source === 'inpatient' || investigation.value?.prescription_type === 'inpatient') {
    return true;
  }
  // For OPD, must be paid
  return isInvestigationPaid.value;
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
    } else if (source === 'opd') {
      // Explicitly OPD - try OPD first
      try {
        invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = false;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (opdError) {
        // If OPD fails with 404 or patient mismatch, try IPD as fallback
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
    } else {
      // Source not specified: Try IPD first, then OPD (to handle IPD investigations correctly)
      // This ensures IPD investigations are found even if source parameter is missing
      let found = false;
      
      // Try IPD first
      try {
        invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = true;
        found = true;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (ipdError) {
        // IPD not found or mismatch - try OPD
        if (ipdError.response?.status === 404 || ipdError.message === 'Patient mismatch') {
          try {
            invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = false;
            found = true;
            
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
          // Other error from IPD call - rethrow
          throw ipdError;
        }
      }
      
      if (!found) {
        $q.notify({
          type: 'negative',
          message: 'Investigation not found',
        });
        router.push('/lab');
        return;
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
        
        // Check if investigation is paid
        checkInvestigationPayment();
        
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

    // Check for template for this investigation's G-DRG code
    try {
      const templateResponse = await consultationAPI.getLabResultTemplateForInvestigation(investigation.value.id);
      if (templateResponse.data) {
        template.value = templateResponse.data;
        usingTemplate.value = true;
      }
    } catch (error) {
      console.log('No template found for investigation:', investigation.value.id);
      template.value = null;
      usingTemplate.value = false;
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
        
        // If template data exists, use it
        if (existingResult.template_data) {
          templateData.value = { ...existingResult.template_data };
          usingTemplate.value = true;
          // Log sample_no status for debugging
          if (templateData.value.sample_no && templateData.value.sample_no.trim() !== '') {
            console.log('Sample ID loaded from database:', templateData.value.sample_no);
          } else {
            console.warn('Sample ID is empty in loaded template_data. Investigation ID:', investigation.value.id);
          }
        } else {
          // No template data, but check if sample_no was pre-generated
          // Try to load it from a minimal lab_result record
          if (existingResult.sample_no) {
            templateData.value = {
              field_values: {},
              messages: {},
              validated_by: '',
              sample_no: existingResult.sample_no
            };
          }
        }
        
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
        // Check if sample ID was pre-generated when investigation was confirmed
        // Try to load existing lab_result with just sample_no
        try {
          const checkResult = await consultationAPI.getLabResult(investigation.value.id);
          if (checkResult.data && checkResult.data.template_data && checkResult.data.template_data.sample_no) {
            // Sample ID was pre-generated, use it
            templateData.value = {
              field_values: {},
              messages: {},
              validated_by: '',
              sample_no: checkResult.data.template_data.sample_no
            };
          } else {
            // No pre-generated sample ID, generate one
            generateSampleId();
            templateData.value = { field_values: {}, messages: {}, validated_by: '', sample_no: templateData.value.sample_no || '' };
          }
        } catch (err) {
          // No result exists, generate sample ID
          generateSampleId();
          templateData.value = { field_values: {}, messages: {}, validated_by: '', sample_no: templateData.value.sample_no || '' };
        }
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
      // Check if sample ID was pre-generated when investigation was confirmed
      // The backend creates a minimal lab_result record with sample_no when investigation is confirmed
      try {
        const checkResult = await consultationAPI.getLabResult(investigation.value.id);
        if (checkResult.data && checkResult.data.template_data && checkResult.data.template_data.sample_no) {
          // Sample ID was pre-generated, use it
          templateData.value = {
            field_values: {},
            messages: {},
            validated_by: '',
            sample_no: checkResult.data.template_data.sample_no
          };
        } else {
          // No pre-generated sample ID, generate one
          generateSampleId();
          templateData.value = { field_values: {}, messages: {}, validated_by: '', sample_no: templateData.value.sample_no || '' };
        }
      } catch (err) {
        // No result exists, generate sample ID
        generateSampleId();
        templateData.value = { field_values: {}, messages: {}, validated_by: '', sample_no: templateData.value.sample_no || '' };
      }
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
  
  // Check payment before saving
  if (!canEnterResults.value) {
    $q.notify({
      type: 'negative',
      message: 'Payment required. This investigation must be paid for before results can be entered.',
      position: 'top',
    });
    return;
  }

  savingResult.value = true;
  try {
    const formData = new FormData();
    formData.append('investigation_id', resultForm.value.investigation_id);
    
    // If using template, send template data
    if (usingTemplate.value && template.value) {
      formData.append('template_id', template.value.id);
      // Ensure sample_no is included - send the current value from templateData
      const dataToSend = { ...templateData.value };
      console.log('Saving lab result with template_data:', dataToSend);
      console.log('Sample ID being sent:', dataToSend.sample_no);
      // Always send the sample_no - backend will use it if provided
      formData.append('template_data', JSON.stringify(dataToSend));
    } else {
      // Otherwise, send results_text
      if (resultForm.value.results_text) {
        formData.append('results_text', resultForm.value.results_text);
      }
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
    const errorMessage = error.response?.data?.detail || 'Failed to save lab result';
    $q.notify({
      type: 'negative',
      message: errorMessage,
      position: 'top',
    });
    
    // If payment error, refresh payment status
    if (error.response?.status === 402) {
      checkInvestigationPayment();
    }
  } finally {
    savingResult.value = false;
  }
};

const getTemplateGroups = () => {
  if (!template.value || !template.value.template_structure.fields) return [];
  const groups = [...new Set(template.value.template_structure.fields.map(f => f.group || 'Other'))];
  return groups;
};

const getTemplateFieldsByGroup = (group) => {
  if (!template.value || !template.value.template_structure.fields) return [];
  return template.value.template_structure.fields
    .filter(f => (f.group || 'Other') === group)
    .sort((a, b) => (a.order || 0) - (b.order || 0));
};

const getReferenceRange = (field) => {
  if (field.reference_min !== null && field.reference_max !== null) {
    return `(Ref: ${field.reference_min} - ${field.reference_max})`;
  }
  return '';
};

const isOutOfRange = (field, value) => {
  if (value === null || value === undefined || value === '') return false;
  const numValue = parseFloat(value);
  if (isNaN(numValue)) return false;
  if (field.reference_min !== null && numValue < field.reference_min) return true;
  if (field.reference_max !== null && numValue > field.reference_max) return true;
  return false;
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

const loadEncounterBills = async (encounterId) => {
  try {
    const response = await billingAPI.getBillsByEncounter(encounterId);
    bills.value = response.data || [];
    
    // Calculate total amounts
    let totalAmount = 0;
    let paidAmount = 0;
    
    for (const bill of bills.value) {
      totalAmount += bill.total_amount || 0;
      paidAmount += bill.paid_amount || 0;
    }
    
    encounterBillInfo.value = {
      totalAmount,
      paidAmount,
      remainingBalance: totalAmount - paidAmount
    };
  } catch (error) {
    console.error('Failed to load bills:', error);
    bills.value = [];
    encounterBillInfo.value = {
      totalAmount: null,
      paidAmount: null,
      remainingBalance: null
    };
  }
};

const checkInvestigationPayment = () => {
  if (!investigation.value || !bills.value.length) {
    // For IPD, allow without payment check
    if (investigation.value?.source === 'inpatient' || investigation.value?.prescription_type === 'inpatient') {
      isInvestigationPaid.value = true;
      return;
    }
    isInvestigationPaid.value = false;
    return;
  }
  
  // For IPD investigations, allow without payment requirement
  if (investigation.value.source === 'inpatient' || investigation.value.prescription_type === 'inpatient') {
    isInvestigationPaid.value = true;
    return;
  }
  
  // Find bill item for this investigation
  for (const bill of bills.value) {
    for (const billItem of bill.bill_items || []) {
      const matchesCode = billItem.item_code === investigation.value.gdrg_code;
      const investigationName = investigation.value.procedure_name || '';
      const investigationCode = investigation.value.gdrg_code || '';
      const matchesName = billItem.item_name && (
        billItem.item_name.includes(investigationName) ||
        billItem.item_name.includes(investigationCode) ||
        billItem.item_name.includes(`Investigation: ${investigationName}`) ||
        billItem.item_name.includes(`Investigation: ${investigationCode}`)
      );
      
      if (matchesCode || matchesName) {
        const totalPrice = billItem.total_price || 0;
        const remainingBalance = billItem.remaining_balance !== undefined && billItem.remaining_balance !== null
          ? billItem.remaining_balance 
          : (totalPrice - (billItem.amount_paid || 0));
        const isPaid = billItem.is_paid !== undefined 
          ? billItem.is_paid 
          : (remainingBalance <= 0.01);
        
        isInvestigationPaid.value = totalPrice === 0 || isPaid;
        return;
      }
    }
  }
  
  // If no bill item found, assume not paid (unless it's free)
  isInvestigationPaid.value = false;
};

const generateAndSaveSampleId = async () => {
  if (!investigation.value) return;
  
  generatingSampleId.value = true;
  try {
    // Call backend API to generate sequential sample ID
    // Format: YYMMNNNNN (e.g., 251100001 = November 2025, sample 00001)
    // Pass source and investigation_id to ensure correct table is checked
    const source = investigation.value?.source || investigation.value?.prescription_type === 'inpatient' ? 'inpatient' : 'opd';
    const response = await labTemplatesAPI.generateSampleId(source, investigation.value.id);
    if (response.data && response.data.sample_id) {
      const sampleId = response.data.sample_id;
      templateData.value.sample_no = sampleId;
      
      // Save the sample ID automatically (no payment check required)
      try {
        const saveResponse = await consultationAPI.saveSampleId(investigation.value.id, sampleId);
        console.log('Save sample ID response:', saveResponse.data);
        // Reload the saved data to ensure we have the latest from database
        if (saveResponse.data && saveResponse.data.template_data) {
          const savedSampleNo = saveResponse.data.template_data.sample_no;
          if (savedSampleNo && savedSampleNo.trim() !== '') {
            templateData.value.sample_no = savedSampleNo;
            console.log('Sample ID saved successfully:', savedSampleNo);
          } else {
            console.error('Sample ID was not in response:', saveResponse.data);
            throw new Error('Sample ID was not saved correctly');
          }
        } else {
          console.error('Invalid response from save sample ID:', saveResponse);
          throw new Error('Invalid response from server');
        }
        $q.notify({
          type: 'positive',
          message: `Sample ID ${sampleId} generated and saved successfully`,
          position: 'top',
          timeout: 3000,
        });
      } catch (saveError) {
        console.error('Failed to save sample ID:', saveError);
        console.error('Error details:', saveError.response?.data);
        $q.notify({
          type: 'negative',
          message: saveError.response?.data?.detail || 'Sample ID generated but could not be saved. Please try again.',
          position: 'top',
          timeout: 5000,
        });
        // Don't clear the sample ID from the form - let user try to save again
      }
    } else {
      throw new Error('Invalid response from server');
    }
  } catch (error) {
    console.error('Failed to generate sample ID:', error);
    // Fallback: generate client-side (may not be unique, but better than nothing)
    const now = new Date();
    const year = now.getFullYear() % 100; // Last 2 digits (e.g., 25 for 2025)
    const month = now.getMonth() + 1; // 1-12
    // Use timestamp-based fallback (not guaranteed unique)
    const timestamp = Date.now();
    const fallbackNum = (timestamp % 100000).toString().padStart(5, '0');
    const sampleId = `${year.toString().padStart(2, '0')}${month.toString().padStart(2, '0')}${fallbackNum}`;
    templateData.value.sample_no = sampleId;
    
    // Try to save the fallback sample ID
    try {
      await consultationAPI.saveSampleId(investigation.value.id, sampleId);
    } catch (saveError) {
      console.error('Failed to save fallback sample ID:', saveError);
    }
    
    $q.notify({
      type: 'warning',
      message: 'Could not generate sequential sample ID. Using fallback. Please verify uniqueness.',
      position: 'top',
    });
  } finally {
    generatingSampleId.value = false;
  }
};

const generateSampleId = async () => {
  // Legacy function - now just calls generateAndSaveSampleId
  await generateAndSaveSampleId();
};

onMounted(() => {
  loadInvestigation();
});
</script>

